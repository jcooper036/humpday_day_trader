from flows.utils.secret_access import get_gsm_secret

gcp_etf_options = get_gsm_secret(secret_name="etf_picks")
etf_options = gcp_etf_options.split(",") if isinstance(gcp_etf_options, str) else []
