import enum

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from prefect import flow

from flows.alpaca_client import AccountType, get_client
import flows.const as const
import flows.env as env


@flow(log_prints=True)
def reporter(account_type: AccountType = AccountType.PAPER, slack_channel=const.CHANNELS['']):
    # get the symbol
    with open(const.CURRENT_STOCK_FILE, "r") as f:
        ticker = f.readlines()[0]
    print(ticker)
    
    # sell the postion
    trading_client = get_client(account_type=account_type)
    postions = trading_client.get_all_positions()
    pos = [p for p in postions if p["symbol"] == ticker][0]

    market_order_data = MarketOrderRequest(
        symbol=ticker,
        qty=pos["qty"],
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    market_order = trading_client.submit_order(order_data=market_order_data)
    
    # read the stock name for the file
    # read the parquet information, make sure the two match
    # send request to the alpaca API to confirm that the postion has been exited
    # if not, then send the sell request immediatly
    # write the stock information to the parquet
    # generate a report on the performance, adding to the prospectors report
    # send to slack
