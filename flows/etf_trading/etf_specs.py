import os

etf_options = os.environ.get("ETF_PICKS")
etf_options = etf_options.split(",") if isinstance(etf_options, str) else []
