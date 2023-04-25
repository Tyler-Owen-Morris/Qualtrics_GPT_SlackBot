import slack
import openai
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter

envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)

# setup Flask server to handle callback events from slack
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['PROD_SIGNING_SECRET'], '/slack/events', app)
# slack_event_adapter = SlackEventAdapter(
#     os.environ['SIGNING_SECRET'], '/slack/events', app)

# setup the slack client
client = slack.WebClient(token=os.environ['PROD_SLACK_TOKEN'])
# client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call('auth.test')['user_id']

# hist = client.api_call('conversations.history', params={
#                        "channel": 'C05474MUDD3'})
# print(len(hist['messages']))
# with open('result.json', 'w') as fp:
#     json.dump(hist['messages'], fp)

# csv_raw = "user,text,ts\n"
# for msg in hist['messages']:
#     is_thread = False
#     if 'thread_ts' in msg.keys():
#         is_thread = True
#         # print("this is a thread")
#         repl = client.api_call('conversations.replies', params={
#             "channel": 'C05474MUDD3',
#             "ts": msg['thread_ts']})
#         # print(repl)
#         for reply in repl['messages']:
#             apnd = ",".join([reply['user'], reply['text'].replace(
#                 ',', '').replace('\n', ''), reply['ts']])
#             csv_raw += apnd+'\n'
#         with open('replies.json', 'w') as fp:
#             json.dump(repl['messages'], fp)
#     if not is_thread:
#         appnd = ",".join([msg['user'], msg['text'].replace(
#             "\n", '').replace(',', ''), msg['ts']])
#         csv_raw += appnd+"\n"

# f = open('output.csv', 'wb')
# f.write(csv_raw.encode('utf-8'))

last_msg = ''


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    global last_msg
    if text == last_msg:
        return
    else:
        last_msg = text
    print("channel:", channel_id)
    print("text:", text)


if __name__ == "__main__":
    app.run(debug=True)
