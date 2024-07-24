from datetime import datetime, timedelta

from alpaca.trading.client import TradingClient
import requests

import flows.env as env
from flows.const import AccountType


ALPACA_ACCOUNT_CREDS = {
    AccountType.LIVE: {
        "api_key": env.ALPACA_LIVE_API_KEY,
        "api_secret": env.ALPACA_LIVE_API_SECRET,
    },
    AccountType.PAPER: {
        "api_key": env.ALPACA_PAPER_API_KEY,
        "api_secret": env.ALPACA_PAPER_API_SECRET,
    },
}


def get_client(account_type):
    is_paper = account_type is AccountType.PAPER
    trading_client = TradingClient(
        api_key=ALPACA_ACCOUNT_CREDS[account_type]["api_key"],
        secret_key=ALPACA_ACCOUNT_CREDS[account_type]["api_secret"],
        paper=is_paper,
    )
    return trading_client


def get_historical_trades(
    symbols: list[str],
    time_frame: timedelta,
    account_type: AccountType = AccountType.PAPER,
) -> dict:
    def _call(
        symbols,
        account_type,
        next_page_token=None,
        max_end_time="9:40:00",
    ):
        page_token = ""
        if next_page_token is not None:
            page_token = f"page_token={next_page_token}&"
        symbols_str = ",".join(symbols)
        asof = (datetime.now().date() - time_frame).strftime("%Y-%m-%d")
        start = f"{asof}T09:30:00-03:00".replace(":", "%3A")
        end = f"{asof}T{max_end_time}-03:00".replace(":", "%3A")
        url = f"https://data.alpaca.markets/v2/stocks/trades?symbols={symbols_str}&limit=1000&start={start}&end={end}&feed=sip&{page_token}sort=asc"
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": ALPACA_ACCOUNT_CREDS[account_type]["api_key"],
            "APCA-API-SECRET-KEY": ALPACA_ACCOUNT_CREDS[account_type]["api_secret"],
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    trade_data = {}
    data = _call(symbols, account_type, next_page_token=None)
    # only take the first entry for each symbol
    for symbol in symbols:
        if symbol in data["trades"]:
            trade_data[symbol] = data["trades"][symbol][0]
    cnt = 0
    symbols_missing = True
    max_end_time = "10:00:00"
    search_symbols = [x for x in symbols]
    while symbols_missing and cnt < 100 and max_end_time != "23:00:00":
        search_symbols = [x for x in symbols if x not in trade_data]
        if data["next_page_token"] is None:
            max_end_time = str(int(max_end_time.split(":")[0]) + 1) + ":00:00"
        if len(search_symbols) == 1:
            max_end_time = "22:00:00"
        data = _call(
            search_symbols,
            account_type,
            next_page_token=data["next_page_token"],
            max_end_time=max_end_time,
        )
        # only take the first entry the first time we come across a symbol
        for symbol in search_symbols:
            if symbol in data["trades"]:
                trade_data[symbol] = data["trades"][symbol][0]
        if all(x in trade_data for x in symbols):
            symbols_missing = False
        cnt += 1

    return trade_data


def get_latest_trade(
    symbols: list[str],
    account_type: AccountType = AccountType.PAPER,
):
    symbols_str = ",".join(symbols)
    url = f"https://data.alpaca.markets/v2/stocks/trades/latest?symbols={symbols_str}&feed=iex"
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": ALPACA_ACCOUNT_CREDS[account_type]["api_key"],
        "APCA-API-SECRET-KEY": ALPACA_ACCOUNT_CREDS[account_type]["api_secret"],
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
