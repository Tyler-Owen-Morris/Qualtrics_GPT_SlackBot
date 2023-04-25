import slack
import openai
import os
import json
from time import sleep
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter

# channelid = 'C027SGCGHC3'  # team-everest
# channelName = 'team-everest'
channelid = 'C027PH1PVUL'  # Tech-questions
channelName = 'tech-questions'
# channelid = 'C05474MUDD3' # dev-channel

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


csv_raw = "type,text,ts\n"
hist = client.api_call('conversations.history', params={
                       "channel": channelid,
                       'limit': 200})
# print(len(hist['messages']))
# print(hist['response_metadata']['next_cursor'])
# with open('result.json', 'w') as fp:
#     json.dump(hist['messages'], fp)
for msg in hist['messages']:
    is_thread = False
    if 'thread_ts' in msg.keys():
        is_thread = True
        # print("this is a thread")
        repl = client.api_call('conversations.replies', params={
            "channel": channelid,
            "ts": msg['thread_ts']})
        # print(repl)
        for reply in repl['messages']:
            apnd = ",".join(['reply', reply['text'].replace(
                ',', '').replace('\n', ''), reply['ts']])
            csv_raw += apnd+'\n'
    if not is_thread:
        appnd = ",".join(["channel msg", msg['text'].replace(
            "\n", '').replace(',', ''), msg['ts']])
        csv_raw += appnd+"\n"
myCursor = hist['response_metadata']['next_cursor']
count = 200
while myCursor != "":
    hist = client.api_call('conversations.history', params={
        "channel": channelid,
        'limit': 200,
        'cursor': myCursor})
    print("paginating, current count:", count)
    print("current cursor:", myCursor)
    count += len(hist['messages'])
    try:
        if hist['response_metadata'] != None:
            myCursor = hist['response_metadata']['next_cursor']
        else:
            myCursor = ""
        for msg in hist['messages']:
            is_thread = False
            if 'thread_ts' in msg.keys():
                is_thread = True
                print("this is a thread")
                repl = client.api_call('conversations.replies', params={
                    "channel": channelid,
                    "ts": msg['thread_ts']})
                # print(type(repl), repl)
                print("threaded_messages", type(repl['messages']))
                count += len(repl['messages'])
                for reply in repl['messages']:
                    apnd = ",".join(['reply', reply['text'].replace(
                        ',', '').replace('\n', ''), reply['ts']])
                    csv_raw += apnd+'\n'
            if not is_thread:
                print("unthreaded", type(msg))
                appnd = ",".join(["channel msg", msg['text'].replace(
                    "\n", '').replace(',', ''), msg['ts']])
                csv_raw += appnd+"\n"
        if count > 100000:
            break
        print("waiting...")
        sleep(30)
    except Exception as e:
        print("Looping error on:", e, hist)
f = open(channelName+'.csv', 'wb')
f.write(csv_raw.encode('utf-8'))

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
