import slack
import os


environment = os.environ['ENVIRONMENT']
if environment == "PROD":
    client = slack.WebClient(token=os.environ['PROD_SLACK_TOKEN'])
else:
    client = slack.WebClient(token=os.environ['DEV_SLACK_TOKEN'])


def get_username_from_id(slack_id):
    response = client.users_info(user=slack_id)
    username = response['user']['name']
    return username
