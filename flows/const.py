from pydantic import BaseModel


CURRENT_STOCK_FILE = "flows/data/current_stock.txt"
CURRENT_MKDOWN_FILE = "flows/data/report.md"
CURRENT_PLOT_FILE = "flows/data/plot.png"


class SlackChannel(BaseModel):
    id: str
    name: str


CHANNELS = {
    "bot-test": SlackChannel(id="C07C4S4ULMU", name="bot-test"),
    "humpday-day-trader": SlackChannel(id="C07CBF97UQJ", name="humpday-day-trader"),
}


ALPACA_URL = {
    "live": "https://api.alpaca.markets",
    "paper": "https://paper-api.alpaca.markets/v2",
}
