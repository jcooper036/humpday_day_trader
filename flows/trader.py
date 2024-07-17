from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.models import Order
import finnhub
from prefect import flow, task
from prefect_slack import SlackCredentials
from prefect_slack.messages import send_chat_message

import flows.const as const
import flows.env as env
from flows.alpaca_client import get_client, AccountType


@task
def post_to_slack(order: Order, market_price: float, slack_channel: const.SlackChannel):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": ":four_leaf_clover: :crossed_fingers: Trade submitted",
            },
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{order.symbol}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"qty: {order.qty}\nprice: {market_price}\nposition value: {round((float(order.qty) * market_price), 2)}",
            },
        },
    ]
    slack_credentials = SlackCredentials.load("slackbot-cred")
    send_chat_message(
        slack_credentials=slack_credentials,
        slack_blocks=blocks,
        channel=slack_channel.name,
    )


@task
def submit_buy_order(
    ticker: str, market_price: float, account_type: AccountType
) -> Order:
    dollar_value = 1000
    qty = round((dollar_value / market_price), 2)

    trading_client = get_client(account_type)
    market_order_data = MarketOrderRequest(
        symbol=ticker,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )
    market_order = trading_client.submit_order(order_data=market_order_data)
    return market_order


@task
def get_market_price(ticker: str) -> float:
    finnhub_client = finnhub.Client(api_key=env.FINNHUB_API_KEY)
    quote = finnhub_client.quote(symbol=ticker)
    return quote["c"]


@flow(log_prints=True)
def trader(
    account_type: AccountType = AccountType.PAPER,
    slack_channel: const.SlackChannel = const.CHANNELS["test"],
):

    # get the current ticker
    with open(const.CURRENT_STOCK_FILE, "r") as f:
        ticker = f.readlines()[0]
    print(ticker)
    market_price = get_market_price(ticker=ticker)
    order = submit_buy_order(
        ticker=ticker,
        market_price=market_price,
        account_type=account_type,
    )
    post_to_slack(order=order, market_price=market_price, slack_channel=slack_channel)

    # write the postition information to a parquet
    # send a request to the alpaca API to sell the stock 30 mintues later
    # send a report to a slack channel


if __name__ == "__main__":
    trader()
