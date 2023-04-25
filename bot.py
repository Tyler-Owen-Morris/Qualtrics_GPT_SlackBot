import slack
import openai
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter

# Load Environment variables
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)

# setup Flask server to handle callback events from slack
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/slack/events', app)

# setup the openapi auth
openai.api_key = os.environ['OPENAI_KEY']

# setup the slack client
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call('auth.test')['user_id']

last_msg = ''


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    print("channel:", channel_id)
    user_id = event.get('user')
    text = event.get('text')
    print("user msg:", text)
    global last_msg
    if text == last_msg:
        return
    else:
        last_msg = text
    if user_id != BOT_ID:
        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            # model='gpt-4-0314',
            messages=[{"role": "system", "content": "You are a Qualtrics assistant. You will answer questions about the setup and functionality of the survey platform Qualtrics, and you will do so as accurately and concisely as you can. Reply with OK if you understand."},
                      {"role": "assistant", "content": "OK"},
                      {"role": "user", "content": text}]
        )

        resp = completion.choices[0].message.content
        print(resp)
        client.chat_postMessage(channel=channel_id,
                                text=resp)


if __name__ == "__main__":
    app.run(debug=True)
