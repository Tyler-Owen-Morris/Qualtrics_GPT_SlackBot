import slack
import openai
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter
from transformers import GPT2Tokenizer

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
CHANNELS = os.environ['CHANNELS'].split(',')
print("channels:", CHANNELS)
BOT_ID = client.api_call('auth.test')['user_id']
print(BOT_ID)

# setup tokenizer for counting tokens
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')

# setup global var for tracking repeat messages
last_msg = ''


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    # print("event:", event)
    channel_id = event.get('channel')
    print("channel:", channel_id)
    channel_type = event.get('channel_type')
    print("channel type:", channel_type)
    user_id = event.get('user')
    text = event.get('text')
    ts = event.get('ts')
    thread_ts = event.get('thread_ts')
    print("thread_ts", thread_ts)
    print("user msg:", text)
    if text == None:
        return
    print("check string", text.lower()[:14])
    # if it's a DM OR the user
    if (user_id != BOT_ID and "<@"+BOT_ID+">" in text[:14] and channel_id in CHANNELS) or (channel_type == 'im' and user_id != BOT_ID):
        global last_msg
        if text == last_msg:
            return
        else:
            last_msg = text
        if "--reset" in text.lower():
            start_new_conversation(user_id)
            client.chat_postMessage(channel=channel_id,
                                    text="Resetting the conversation and dumping memory")
            return
        # SEEDED CHAT OPTION
        if channel_type in ['group', 'channel']:
            # drop the bot opening from history and henceforth
            text = text[14:]
        full_msgs, warn = construct_chat_history(user_id, text)
        # print("full message with history:", full_msgs)

        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=full_msgs
        )
        resp = completion.choices[0].message.content
        if warn == True:
            resp += "\n\n WARNING: Chat history is too long. Use the --reset command to clear cache and start fresh."
        print(resp)
        if channel_type in ['group', 'channel']:
            if thread_ts != None:
                ts = thread_ts  # reply in the thread
            client.chat_postMessage(
                channel=channel_id, text=resp, thread_ts=ts)
        elif channel_type == 'im':
            client.chat_postMessage(channel=channel_id,
                                    text=resp)
        append_and_save_conversation(user_id, text, resp)


def construct_chat_history(uuid, chat):
    tokens = 0
    warn = False
    # must return an array of the chat history
    base = [{"role": "system", "content": "You are a Qualtrics assistant. You will ONLY answer questions about the setup and functionality of the survey platform Qualtrics, and you will do so as accurately and concisely as you can. You will refuse to answer any questions unrelated to Qualtrics. Reply with OK if you understand."},
            {"role": "assistant", "content": "OK"}]
    new = {'role': 'user', 'content': chat}
    new_tokens = count_conversation_tokens([new])
    base_tokens = count_conversation_tokens(base)
    tokens += base_tokens + new_tokens
    data = load_or_create_json_file(uuid)
    if len(data) > 0:
        data_tokens = count_conversation_tokens(data)
        print('data tokens:', data_tokens)
        while tokens + count_conversation_tokens(data) > 4096:
            warn = True
            print(">>>>>>>>>>>>>conversation too long<<<<<<<<<<<<,",
                  tokens + count_conversation_tokens(data))
            data = data[1:]
        base += data
    base.append(new)
    return base, warn


def load_or_create_json_file(user_id):
    file_name = f"conversations/{user_id}.json"
    # Write the empty file if it doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, "w") as json_file:
            json.dump([[]], json_file)
    # Read the file data
    with open(file_name, "r") as json_file:
        data = json.load(json_file)[-1]

    return data


def append_and_save_conversation(user_id, user_string, bot_string):
    file_name = f"conversations/{user_id}.json"
    with open(file_name, "r") as json_file:
        data = json.load(json_file)
    last_conv = data[-1]
    # print("full data:", data)
    # print("last convo:", last_conv)
    user_message = {"role": "user", "content": user_string}
    bot_message = {"role": "assistant", "content": bot_string}

    last_conv.append(user_message)
    last_conv.append(bot_message)
    if len(data) > 1:
        data = data[:-1]
        data.append(last_conv)
    else:
        data = [last_conv]
    # print("data before write:", data)
    with open(file_name, "w") as json_file:
        json.dump(data, json_file)


def start_new_conversation(user_id):
    file_name = f"conversations/{user_id}.json"
    with open(file_name, "r") as json_file:
        data = json.load(json_file)
    convo = []
    # print("data before reset", data)
    data.append(convo)
    # print("data after reset", data)
    with open(file_name, "w") as json_file:
        json.dump(data, json_file)


def count_conversation_tokens(conversation):
    total_tokens = 0
    # print(conversation)
    for message in conversation:
        # print(message)
        # print(type(message))
        tokens = tokenizer.tokenize(message['content'])
        total_tokens += len(tokens) + 3
    return total_tokens


if __name__ == "__main__":
    app.run('0.0.0.0', debug=True)  # 0.0.0.0 allows run on public server
