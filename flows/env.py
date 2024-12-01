# import os
# from dotenv import load_dotenv
from flows.utils.secret_access import get_gsm_secret

# load_dotenv()

FINNHUB_API_KEY = get_gsm_secret(secret_name="finnhub_api_key")
ALPACA_PAPER_API_KEY = get_gsm_secret(secret_name="alpaca_paper_api_key")
ALPACA_PAPER_API_SECRET = get_gsm_secret(secret_name="alpaca_paper_api_secret")
ALPACA_LIVE_API_API = ""
ALPACA_LIVE_API_SECRET = ""
# FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")
# ALPACA_LIVE_API_KEY = os.environ.get("ALPACA_LIVE_API_KEY")
# ALPACA_LIVE_API_SECRET = os.environ.get("ALPACA_LIVE_API_SECRET")
# ALPACA_PAPER_API_KEY = os.environ.get("ALPACA_PAPER_API_KEY")
# ALPACA_PAPER_API_SECRET = os.environ.get("ALPACA_PAPER_API_SECRET")
