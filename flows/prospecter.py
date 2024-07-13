import pandas as pd
from prefect import flow, task

from flows.const import CURRENT_STOCK_FILE

CURRENT_STOCK_FILE = ""


def get_wikipedia_nasdaq100() -> pd.DataFrame:
    url = "https://en.m.wikipedia.org/wiki/Nasdaq-100"
    return pd.read_html(url, attrs={"id": "constituents"}, index_col="Ticker")[
        0
    ].reset_index()


@task
def pick_random_stock() -> dict:
    nasdaq_100 = get_wikipedia_nasdaq100()
    return nasdaq_100.sample(n=1).to_dict("records")


@task
def save_current_stock(stock: dict):
    with open(CURRENT_STOCK_FILE, "w") as f:
        f.write(stock["Ticker"])


@flow(log_prints=True)
def prospector():
    stock = pick_random_stock()

    print("hello there")
    # pick a random stock
    # write that stock to a local file called "next stock"
    # put together the prospectus
    # what is this company?
    # how has their stock performed over the last week?
    # including the performance from 10-1030 on wednesdys
    # send this to a slack channel
