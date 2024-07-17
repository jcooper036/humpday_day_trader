from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.models import Order
from prefect import flow, task
from prefect_slack import SlackCredentials
from prefect_slack.messages import send_chat_message

from flows.alpaca_client import AccountType, get_client
import flows.const as const
from flows.trader import get_market_price


@task
def post_to_slack(order: Order, market_price: float, slack_channel: const.SlackChannel):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": ":moneybag: Postion sold",
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
                "text": f"qty: {order.qty}\nprice: {market_price}\ntotal value: {round((float(order.qty) * market_price), 2)}\n:chart_with_upwards_trend:",
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
def sell_position(account_type: AccountType, ticker):
    trading_client = get_client(account_type=account_type)
    postions = trading_client.get_all_positions()
    pos = [p for p in postions if p.symbol == ticker][0]

    market_order_data = MarketOrderRequest(
        symbol=ticker,
        qty=pos.qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    market_order = trading_client.submit_order(order_data=market_order_data)
    return market_order


@flow(log_prints=True)
def reporter(
    account_type: AccountType = AccountType.PAPER,
    slack_channel: const.SlackChannel = const.CHANNELS["test"],
):
    # get the symbol
    with open(const.CURRENT_STOCK_FILE, "r") as f:
        ticker = f.readlines()[0]
    print(ticker)

    sell_order = sell_position(account_type=account_type, ticker=ticker)
    market_price = get_market_price(ticker=ticker)
    post_to_slack(
        order=sell_order, market_price=market_price, slack_channel=slack_channel
    )

    # read the stock name for the file
    # read the parquet information, make sure the two match
    # send request to the alpaca API to confirm that the postion has been exited
    # if not, then send the sell request immediatly
    # write the stock information to the parquet
    # generate a report on the performance, adding to the prospectors report
    # send to slack


if __name__ == "__main__":
    reporter()
