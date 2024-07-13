from prefect import flow


@flow(log_prints=True)
def trader():
    print("great trades")
    # read stock name from file
    # make a request to the alpaca API
    # write the postition information to a parquet
    # send a request to the alpaca API to sell the stock 30 mintues later
    # send a report to a slack channel
