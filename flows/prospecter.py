from prefect import flow


@flow(log_prints=True)
def prospector():
    print("hello there")
    # pick a random stock
    # write that stock to a local file called "next stock"
    # put together the prospectus
    # what is this company?
    # how has their stock performed over the last week?
    # including the performance from 10-1030 on wednesdys
    # send this to a slack channel
