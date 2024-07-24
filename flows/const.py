import enum
from pydantic import BaseModel

from flows import env

CURRENT_STOCK_FILE = "flows/data/current_stock.txt"
CURRENT_MKDOWN_FILE = "flows/data/report.md"
CURRENT_PLOT_FILE = "flows/data/plot.png"


class SlackChannel(BaseModel):
    id: str
    name: str


class AccountType(enum.StrEnum):
    LIVE = "live"
    PAPER = "paper"


class SlackChannelName(enum.StrEnum):
    BOT_TEST = "bot-test"
    HUMPDAY_DAY_TRADER = "humpday-day-trader"


CHANNELS = {
    SlackChannelName.BOT_TEST: SlackChannel(
        id="C07C4S4ULMU",
        name="bot-test",
    ),
    SlackChannelName.HUMPDAY_DAY_TRADER: SlackChannel(
        id="C07CBF97UQJ",
        name="humpday-day-trader",
    ),
}



ALPACA_URL = {
    AccountType.LIVE: "https://api.alpaca.markets",
    AccountType.PAPER: "https://paper-api.alpaca.markets/v2",
}
