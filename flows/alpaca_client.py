import enum

from alpaca.trading.client import TradingClient

import flows.env as env
from flows.const import AccountType


def get_client(account_type):
    if account_type == AccountType.PAPER:
        trading_client = TradingClient(
            api_key=env.ALPACA_PAPER_API_KEY,
            secret_key=env.ALPACA_PAPER_API_SECRET,
            paper=True,
        )
    if account_type == AccountType.LIVE:
        trading_client = TradingClient(
            api_key=env.ALPACA_LIVE_API_KEY,
            secret_key=env.ALPACA_LIVE_API_SECRET,
            paper=False,
        )
    return trading_client
