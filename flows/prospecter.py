from prefect import flow


@flow(log_prints=True)
def prospector():
    print("hello there")
