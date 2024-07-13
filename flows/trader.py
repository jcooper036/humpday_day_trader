from prefect import flow


@flow(log_prints=True)
def trader_buy_stock():
    print("great trades")


@flow(log_prints=True)
def trader_sell_stock():
    print("great trades")
