from prefect import flow


@flow(log_prints=True)
def trader_sell_stock():
    print("great trades")
    # read the stock name for the file
    # read the parquet information, make sure the two match
    # send request to the alpaca API to confirm that the postion has been exited
    # if not, then send the sell request immediatly
    # write the stock information to the parquet
    # generate a report on the performance, adding to the prospectors report
    # send to slack
