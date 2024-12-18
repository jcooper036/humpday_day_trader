from datetime import timedelta
from decimal import Decimal
import time
from typing import Optional

from alpaca.trading.requests import (
    MarketOrderRequest,
    StopLossRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce
from prefect import flow, task
from pydantic import BaseModel

from flows.alpaca_client import (
    get_client,
    get_historical_trades,
    get_latest_trade,
)
from flows.const import AccountType, SlackChannelName
from flows.etf_trading.etf_specs import etf_options


class Position(BaseModel):
    symbol: str
    market_value: Decimal
    qty: Decimal
    current_price: Decimal
    proportion_portfolio_value: float
    cost_basis: Decimal | None = None
    ratio_change: Optional[float] = None
    new: bool = False


class Portfolio(BaseModel):
    cash_on_hand: int
    positions: list[Position]


@task(retries=3, retry_delay_seconds=5)
def get_curent_portfolio(
    cash_to_set_aside: int,
    etfs: list[str] = etf_options,
    account_type: AccountType = AccountType.PAPER,
) -> Portfolio:
    client = get_client(account_type)
    account = client.get_account()
    cash_on_hand = int(float(account.cash))  # round down to nearest whole
    usable_cash = cash_on_hand - min(cash_to_set_aside, cash_on_hand)
    positions = client.get_all_positions()
    positions = [p for p in positions if p.symbol in etfs]
    new_positions = []
    for etf in etfs:
        if etf not in [p.symbol for p in positions]:
            data = get_latest_trade(
                symbols=[etf],
                account_type=account_type,
            )
            price = data["trades"][etf]["p"]
            new_positions.append(
                Position(
                    new=True,
                    symbol=etf,
                    qty=0,
                    market_value=0.0,
                    proportion_portfolio_value=0.0,
                    current_price=price,
                )
            )

    total_position_market_value = (
        sum([Decimal(p.market_value) for p in positions]) + usable_cash
    )
    # current proportions
    value_proportions = {
        p.symbol: float(Decimal(p.market_value) / total_position_market_value)
        for p in positions
    }
    positions = [
        Position(
            symbol=p.symbol,
            market_value=Decimal(p.market_value),
            qty=Decimal(p.qty),
            cost_basis=Decimal(p.cost_basis),
            proportion_portfolio_value=value_proportions[p.symbol],
            current_price=Decimal(p.current_price),
        )
        for p in positions
    ]
    positions = positions + new_positions
    return Portfolio(cash_on_hand=usable_cash, positions=positions)


def measure_performance(
    portfolio: Portfolio,
    time_frame: timedelta = timedelta(days=30),
    account_type: AccountType = AccountType.PAPER,
):
    symbols = [p.symbol for p in portfolio.positions]
    data = get_historical_trades(
        symbols=symbols,
        time_frame=time_frame,
        account_type=account_type,
    )
    old_price = {s: data[s]["p"] for s in symbols}
    for p in portfolio.positions:
        p.ratio_change = float(p.current_price) / old_price[p.symbol]
    return portfolio


@task
def compute_rebalance_target(portfolo: Portfolio) -> dict:
    min_ratio_per_position = (1 / len(portfolo.positions)) - (
        0.7 / len(portfolo.positions)
    )
    max_ratio_per_position = (1 / len(portfolo.positions)) + (
        0.7 / len(portfolo.positions)
    )
    change_sum = sum([p.ratio_change for p in portfolo.positions])
    performance_proportional_change = {
        p.symbol: (p.ratio_change / change_sum) for p in portfolo.positions
    }
    adj_performance_proportional_change = {}
    for k, v in performance_proportional_change.items():
        if v > (1 / len(portfolo.positions)):
            adj_performance_proportional_change[k] = min(v, max_ratio_per_position)
        else:
            adj_performance_proportional_change[k] = max(v, min_ratio_per_position)

    # finally adjust everything such that the sum is 1. It might be more because
    # of non-offsetting upwards / downwards adjustments, but it should never be
    # that far off
    total_adj = sum(adj_performance_proportional_change.values())
    if total_adj > 1 or total_adj < 0.99:  # poor-mans .isclose w/o using numpy :)
        for k, v in adj_performance_proportional_change:
            adj_performance_proportional_change[k] = v / total_adj

    return adj_performance_proportional_change


@task
def create_rebalance_sell_orders(
    portfolo: Portfolio, rebalance_targets: dict
) -> list[MarketOrderRequest]:

    orders = []
    # for any assets that are too much of the portfolio, turn the correct proportion into cash
    for position in portfolo.positions:
        if rebalance_targets[position.symbol] < position.proportion_portfolio_value:
            # x / a = y / b
            n_left_shares = (
                rebalance_targets[position.symbol]
                * float(position.qty)
                / position.proportion_portfolio_value
            )
            n_sell_shares = round(float(position.qty) - n_left_shares, 2)
            portfolo.cash_on_hand += n_sell_shares * position.current_price
            orders.append(
                MarketOrderRequest(
                    symbol=position.symbol,
                    qty=n_sell_shares,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                )
            )
    return orders


@task(retries=3, retry_delay_seconds=5)
def update_portfolio_cash(
    portfolo: Portfolio,
    cash_to_set_aside: int,
    account_type: AccountType = AccountType.PAPER,
):
    client = get_client(account_type)
    account = client.get_account()
    cash_on_hand = int(float(account.cash))  # round down to nearest whole
    portfolo.cash_on_hand = cash_on_hand - cash_to_set_aside
    return portfolo


@task
def create_rebalance_buy_orders(portfolo: Portfolio, rebalance_targets: dict):
    orders = []
    buy_targets = {}
    for position in portfolo.positions:
        if rebalance_targets[position.symbol] > position.proportion_portfolio_value:
            buy_targets[position.symbol] = rebalance_targets[position.symbol]
    buy_target_total = sum(buy_targets.values())

    # this is basically the amount of money to invest in each ticker
    buy_allocation: dict[str, int] = {
        k: int(portfolo.cash_on_hand * (v / buy_target_total))
        for k, v in buy_targets.items()
    }
    print(f"{portfolo.cash_on_hand=}")
    for symbol, money_to_spend in buy_allocation.items():
        print(f"{symbol=}, {money_to_spend=}")
        current_price = [
            p.current_price for p in portfolo.positions if p.symbol == symbol
        ][0]
        buy_qty = int(
            money_to_spend / current_price
        )  # many of these aren't fractionable
        if buy_qty > 0:
            orders.append(
                MarketOrderRequest(
                    symbol=symbol,
                    qty=buy_qty,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    stop_loss=StopLossRequest(stop_price=float(current_price) * 0.85),
                )
            )
    return orders


@task(retries=3, retry_delay_seconds=5)
def process_orders(
    order_datas: list[MarketOrderRequest],
    account_type: AccountType = AccountType.PAPER,
):
    client = get_client(account_type=account_type)
    orders = []
    for order_data in order_datas:
        r = client.submit_order(order_data=order_data)
        orders.append(r)
    return orders


@task(retries=3, retry_delay_seconds=5)
def wait_for_orders_to_complete(
    symbol: list[str],
    account_type: AccountType,
    max_retries: int = 60,
):
    client = get_client(account_type=account_type)
    request_params = GetOrdersRequest(
        symbols=[symbol],
    )
    # orders will exist if they are not closed yet
    orders = client.get_orders(request_params)
    total_tries = 0
    # for the first few tries we'll try quickly
    # after that, slow down the retries, because it's probably going
    # to be a while
    retry_timing = [10, 10, 20, 60, 300]  # seconds
    while (len(orders) > 0) and (total_tries < max_retries):
        orders = client.get_orders(request_params)
        if len(retry_timing) > total_tries:
            wait_time = retry_timing[total_tries]
        else:
            wait_time = 3600  # default is 1 hour
        print(f"Waiting for {symbol} order to clear: check in {wait_time} seconds")
        time.sleep(wait_time)
        total_tries += 1
    if total_tries == max_retries:
        raise ValueError(f"order for {symbol} was not proccesed in {max_retries} tries")


@flow(
    log_prints=True,
    name="etf_balancing",
)
def etf_balancing(
    cash_to_set_aside: int,
    etfs: list[str] | None = etf_options,
    account_type: AccountType = AccountType.PAPER,
    sell_balancing=False,
    slack_channel_name: SlackChannelName = SlackChannelName.BOT_TEST,
):
    portfolio = get_curent_portfolio(
        cash_to_set_aside=cash_to_set_aside,
        etfs=etfs,
        account_type=account_type,
    )
    print(f"{portfolio.model_dump_json()=}")
    portfolio = measure_performance(portfolio)
    print(f"{portfolio.model_dump_json()=}")
    rebalance_targets = compute_rebalance_target(portfolio)
    print(f"{rebalance_targets=}")

    # selling orders block
    if sell_balancing:
        sell_orders = create_rebalance_sell_orders(portfolio, rebalance_targets)
        print(f"{sell_orders=}")
        sell_order_reciepts = process_orders(
            orders=sell_orders,
            account_type=account_type,
        )
        print(f"{sell_order_reciepts=}")
        wait_for_orders_to_complete(sell_order_reciepts)

    # spending cash on buy rebalancing
    portfolio = update_portfolio_cash(
        portfolo=portfolio,
        account_type=account_type,
        cash_to_set_aside=cash_to_set_aside,
    )
    buy_orders = create_rebalance_buy_orders(portfolio, rebalance_targets)
    print(f"{buy_orders=}")
    buy_order_reciepts = process_orders(buy_orders)
    print(f"{buy_order_reciepts=}")

    # don't need to wrap in ummapped because they are
    # not iterable arguments
    wait_for_orders_to_complete.map(
        symbol=etfs,
        account_type=account_type,
        max_retries=60,
    )

    # commence buying and selling
    # compare 3 month and 1 month window to the SNP and Nasdaq
    # post report to slack


if __name__ == "__main__":
    etf_balancing(cash_to_set_aside=10000)
