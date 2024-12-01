import asyncio
from datetime import datetime, timedelta
import os

import finnhub
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import pandas as pd
from prefect import flow, task
from prefect_slack import SlackCredentials
from prefect_slack.messages import send_chat_message
import seaborn as sns

from flows import env
from flows import const

# non-interactive backend as to not crash the thread
matplotlib.use("agg")


def get_wikipedia_nasdaq100() -> pd.DataFrame:
    url = "https://en.m.wikipedia.org/wiki/Nasdaq-100"
    return (
        pd.read_html(url, attrs={"id": "constituents"}, index_col="Symbol")[0]
        .reset_index()
        .rename(columns={"Symbol": "Ticker"})
    )


@task
def pick_stock(ticker: str | None = None) -> dict:
    if ticker is None:
        nasdaq_100 = get_wikipedia_nasdaq100()
        return nasdaq_100.sample(n=1).to_dict("records")[0]
    return {"Ticker": ticker}


@task
def save_current_stock(stock: dict):
    def safe_open_w(path):
        """Open "path" for writing, creating any parent directories as needed."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return open(path, "w")

    print(os.getcwd())
    with safe_open_w(const.CURRENT_STOCK_FILE, "w+") as f:
        f.write(stock["Ticker"])


@task
def get_stock_data(stock: dict) -> dict:
    symbol: str = stock["Ticker"]
    today: str = datetime.now().date().strftime("%Y-%m-%d")
    one_year_ago: str = (datetime.now().date() - timedelta(days=3 * 365)).strftime(
        "%Y-%m-%d"
    )
    data = {"symbol": symbol}
    data.update(stock)
    data = {k.lower().replace(" ", "_"): v for k, v in data.items()}

    # use finnhub to collect some data
    # limit 60 API calls / minute
    finnhub_client = finnhub.Client(api_key=env.FINNHUB_API_KEY)
    quote = finnhub_client.quote(symbol=symbol)
    data["current_price"] = quote["c"]
    profile = finnhub_client.company_profile2(symbol=symbol)
    data["company"] = profile["name"]
    basic_fiancials = finnhub_client.company_basic_financials(symbol, metric="all")
    data.update({m: basic_fiancials["metric"][m] for m in ["52WeekHigh", "52WeekLow"]})
    insider_info = finnhub_client.stock_insider_transactions(
        symbol=symbol,
        _from=one_year_ago,
        to=today,
    )
    data["insider_transactions"] = insider_info["data"]
    company_profile = finnhub_client.company_profile2(symbol=symbol)
    data.update({m: company_profile[m] for m in ["name", "weburl"]})
    # company_news = finnhub_client.company_news(
    #     symbol,
    #     _from=one_year_ago,
    #     to=today,
    # )
    data["recommendation_trends"] = finnhub_client.recommendation_trends(symbol)
    return data


@task
def build_report(stock_data):

    # mkdown data
    sd = stock_data
    mkdown_data = f"""{sd['company']} ({sd['ticker']}) | :mag: {sd['weburl']}
:factory: GICS Sector:{sd.get("gics_sector")}\tGICS Sub-Industry:{sd.get("gics_sub-industry")} 
:moneybag: *current price : {sd["current_price"]}*\t52WeekHigh : {sd["52WeekHigh"]}\t52WeekLow : {sd["52WeekLow"]}
    """
    print(mkdown_data)
    with open(const.CURRENT_MKDOWN_FILE, "w+") as f:
        f.write(mkdown_data)

    # plot
    # format the insider data
    df = pd.DataFrame(stock_data["insider_transactions"])
    # chrome-extension://oemmndcbldboiebfnladdacbdfmadadm/https://www.sec.gov/about/forms/form4data.pdf
    # code S is the sale of private assets. There are others that might apply, but this
    # is a simple one
    df = df.query("transactionCode=='S'").reset_index(drop=True)

    df.transactionDate = pd.to_datetime(df.transactionDate)
    df = df.sort_values("transactionDate", ascending=True)
    # we drop a bit of data, but we expect these values to be very similar so it's fine
    df = df.drop_duplicates(subset="transactionDate")
    df = df.set_index("transactionDate")

    rule = 30
    sparse = df.index.to_series().diff().dt.days.ge(rule)
    new_timestamps = df.index[sparse] - pd.Timedelta(days=rule)
    df_ = df.reindex(df.index.union(new_timestamps))
    df_["month"] = df_.index.astype(str).str[0:7]
    month_ma = df_.groupby("month").transactionPrice.mean().interpolate()
    month_ma.name = "month_moving_average"
    df_ = df_.merge(month_ma, on="month")
    insider_price_month_average = (
        df_[["month", "month_moving_average"]].drop_duplicates().reset_index(drop=True)
    )

    # add in the analyst data
    ar_data = pd.DataFrame(stock_data["recommendation_trends"])
    ar_data["month"] = ar_data["period"].str[0:7]
    pdf = insider_price_month_average.merge(ar_data, on="month", how="outer")

    # build a plot and save it
    _, axes = plt.subplots(2, 1, figsize=(12, 6))
    sns.lineplot(
        pdf,
        x="month",
        y="month_moving_average",
        ax=axes[0],
    )
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].set_title(f"({stock_data['ticker']}) Insider sell price")

    patches = [
        ("strongBuy", "darkblue"),
        ("buy", "lightblue"),
        ("hold", "orange"),
        ("sell", "red"),
        ("strongSell", "darkred"),
    ]
    legend_handles = []
    for c, col in patches:
        sns.barplot(x="month", y=c, data=pdf, color=col, ax=axes[1])
        legend_handles.append(mpatches.Patch(color=col, label=c))

    plt.legend(handles=legend_handles)

    axes[1].tick_params(axis="x", rotation=45)
    axes[1].set_ylabel("number of analysts")
    axes[1].set_title(f"({stock_data['ticker']}) Analyst reccomendations")
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda x, _: int(x)))
    plt.tight_layout()
    plt.savefig(const.CURRENT_PLOT_FILE)
    return mkdown_data


@task
async def send_prospect_message(
    slack_credentials,
    mkdown_data,
    slack_channel: const.SlackChannel,
):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": ":gem: This is NOT financial advice :gem:",
            },
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": mkdown_data.split(" | ")[0],
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": mkdown_data.split(" | ")[1]},
        },
    ]
    await send_chat_message(
        slack_credentials=slack_credentials,
        slack_blocks=blocks,
        channel=slack_channel.name,
        text=f'{mkdown_data.split(" | ")[0]}\n{mkdown_data.split(" | ")[1]}',
    )


@task
async def send_prospect_graph(
    slack_credentials,
    slack_channel: const.SlackChannel,
):
    client = slack_credentials.get_client()
    _ = await client.files_upload_v2(
        file=const.CURRENT_PLOT_FILE,
        channel=slack_channel.id,
        title="bomb proof technical analysis",
    )
    # can't do this because not paid workspace
    # https://stackoverflow.com/questions/58186399/how-to-create-a-slack-message-containing-an-uploaded-image
    # would also need to change the token type to user instead of bot
    # file_id = json.loads(result.req_args["params"]["files"])[0]["id"]
    # result = await client.files_sharedPublicURL(
    #     file=file_id,
    # )


@flow(log_prints=True)
def prospector(
    slack_channel_name: const.SlackChannelName = const.SlackChannelName.BOT_TEST,
    ticker: str | None = None,
) -> str:
    slack_channel = const.CHANNELS[slack_channel_name]
    stock = pick_stock(ticker=ticker)
    save_current_stock(stock=stock)
    stock_data = get_stock_data(stock)
    mkdown_data = build_report(stock_data=stock_data)
    slack_credentials = SlackCredentials.load("slackbot-cred")
    asyncio.run(
        send_prospect_message(
            slack_credentials=slack_credentials,
            mkdown_data=mkdown_data,
            slack_channel=slack_channel,
        )
    )
    asyncio.run(
        send_prospect_graph(
            slack_credentials=slack_credentials,
            slack_channel=slack_channel,
        )
    )
    return stock["Ticker"]


if __name__ == "__main__":
    prospector(slack_channel_name="bot-test")
