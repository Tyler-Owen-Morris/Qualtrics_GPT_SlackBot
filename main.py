from website import create_app
from pathlib import Path
from dotenv import load_dotenv
import segment.analytics as analytics
import os
from slackeventsapi import SlackEventAdapter
import slack

# Load Environment variables
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
# Local variable for environment:
environment = os.environ['ENVIRONMENT']
analytics.write_key = os.environ['SEGMENT_WRITE_KEY']
app = create_app()

if environment == "PROD":
    slack_event_adapter = SlackEventAdapter(
        os.environ['PROD_SIGNING_SECRET'], '/slack/events', app)
    client = slack.WebClient(token=os.environ['PROD_SLACK_TOKEN'])
else:
    slack_event_adapter = SlackEventAdapter(
        os.environ['SIGNING_SECRET'], '/slack/events', app)
    client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

BOT_ID = client.api_call('auth.test')['user_id']
print(BOT_ID)


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    print("event:", event)


def run_app():
    from waitress import serve
    if environment == "PROD":
        # WSGI server is required for production to allow simultaneous requests
        serve(app, host='0.0.0.0', port=os.environ['WEBSITE_PORT'])
    else:
        # Development server runs as default
        # app.run('0.0.0.0', debug=False)  # 0.0.0.0 allows run on public server
        serve(app, host='0.0.0.0', port=os.environ['WEBSITE_PORT'])


if __name__ == "__main__":
    run_app()
