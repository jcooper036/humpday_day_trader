import time

from pydantic import BaseModel
from prefect import flow, task, pause

from flows.prospector import prospector
from flows.reporter import reporter
from flows.trader import trader
from flows.const import AccountType, SlackChannelName


class SuspendConfig(BaseModel):
    h: int = 0  # hours
    m: int = 0  # minutes
    s: int = 0  # seconds


@task
def suspend(config: SuspendConfig):
    total_wait = (config.h * 3600) + (config.m * 60) + config.s
    print(f"waiting for {total_wait} seconds")
    for i in range(total_wait):
        time.sleep(1)
        if i % 60 == 0 and i > 0:
            print(f"... sleeping for {total_wait-i} more seconds")


@flow(
    log_prints=True,
    name="humpday_day_trader_basic",
    retries=0,
)
def humpday_day_trader_basic(
    prospect_buy_suspend: SuspendConfig,
    buy_sell_suspend: SuspendConfig,
    ticker: str | None = None,
    account_type: AccountType = AccountType.PAPER,
    slack_channel_name: SlackChannelName = SlackChannelName.BOT_TEST,
):
    ticker = prospector(
        ticker=ticker,
        slack_channel_name=slack_channel_name,
    )
    suspend(prospect_buy_suspend)
    order = trader(
        ticker=ticker,
        account_type=account_type,
        slack_channel_name=slack_channel_name,
    )
    suspend(buy_sell_suspend)
    reporter(
        ticker=ticker,
        account_type=account_type,
        slack_channel_name=slack_channel_name,
    )


@flow(
    log_prints=True,
    name="suspend_test",
    retries=0,
)
def suspend_test(
    suspend_time: SuspendConfig,
    ticker: str | None = None,
    slack_channel_name: SlackChannelName = SlackChannelName.BOT_TEST,
):
    ticker = prospector(
        ticker=ticker,
        slack_channel_name=slack_channel_name,
    )
    suspend(suspend_time)
    ticker = prospector(
        ticker=ticker,
        slack_channel_name=slack_channel_name,
    )


if __name__ == "__main__":
    humpday_day_trader_basic(
        prospect_buy_suspend=SuspendConfig(s=5),
        buy_sell_suspend=SuspendConfig(s=5),
        ticker="AMD",
        account_type="paper",
        slack_channel_name="bot-test",
    )
