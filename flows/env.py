import os
from dotenv import load_dotenv

load_dotenv()

FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]
ALPACA_LIVE_API_KEY = os.environ["ALPACA_LIVE_API_KEY"]
ALPACA_LIVE_API_SECRET = os.environ["ALPACA_LIVE_API_SECRET"]
ALPACA_PAPER_API_KEY = os.environ["ALPACA_PAPER_API_KEY"]
ALPACA_PAPER_API_SECRET = os.environ["ALPACA_PAPER_API_SECRET"]
