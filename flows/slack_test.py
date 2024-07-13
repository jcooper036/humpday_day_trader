from prefect import flow
from prefect_slack import SlackCredentials
from prefect_slack.messages import send_chat_message


@flow
def example_slack_send_message_flow():
    slack_credentials = SlackCredentials.load("slackbot-cred")
    result = send_chat_message(
        slack_credentials=slack_credentials,
        text="This proves send_chat_message works!",
        channel="bot-test",
    )
    return result


if __name__ == "__main__":
    example_slack_send_message_flow()
