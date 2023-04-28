import slack
import openai
import os
import json
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
    # print("event:", event)
    channel_id = event.get('channel')
    print("channel:", channel_id)
    channel_type = event.get('channel_type')
    print("channel type:", channel_type)
    user_id = event.get('user')
    text = event.get('text')
    print("user msg:", text)
    global last_msg
    if text == last_msg:
        return
    else:
        last_msg = text
    if user_id != BOT_ID:
        # SEEDED CHAT OPTION
        full_msgs = construct_chat_history(user_id, text)
        print("full message with history:", full_msgs)
        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            # model='curie:ft-personal-2023-04-28-05-11-33',
            # messages=[{"role": "system", "content": "You are a Qualtrics assistant. You will ONLY answer questions about the setup and functionality of the survey platform Qualtrics, and you will do so as accurately and concisely as you can. You will refuse to answer any questions unrelated to Qualtrics. Reply with OK if you understand."},
            #           {"role": "assistant", "content": "OK"},
            #           {"role": "user", "content": text}]
            messages=full_msgs
        )
        resp = completion.choices[0].message.content

        # FINE-TUNED SINGLE COMPLETION OPTION
        # completion = openai.Completion.create(
        #     model='curie:ft-personal-2023-04-28-05-11-33',
        #     prompt=text,
        #     max_tokens=1000
        # )
        # resp = completion.choices[0].text

        print(resp)
        client.chat_postMessage(channel=channel_id,
                                text=resp)
        append_and_save_conversation(user_id, text, resp)


def construct_chat_history(uuid, chat):
    # must return an array of the chat history
    data = load_or_create_json_file(uuid)
    base = [{"role": "system", "content": "You are a Qualtrics assistant. You will ONLY answer questions about the setup and functionality of the survey platform Qualtrics, and you will do so as accurately and concisely as you can. You will refuse to answer any questions unrelated to Qualtrics. Reply with OK if you understand."},
            {"role": "assistant", "content": "OK"}]
    if len(data) > 0:
        base += data
    new = {'role': 'user', 'content': chat}
    base.append(new)
    return base


def load_or_create_json_file(user_id):
    file_name = f"conversations/{user_id}.json"
    # Write the empty file if it doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, "w") as json_file:
            json.dump([], json_file)
    # Read the file data
    with open(file_name, "r") as json_file:
        data = json.load(json_file)

    return data


def append_and_save_conversation(user_id, user_string, bot_string):
    data = load_or_create_json_file(user_id)
    file_name = f"conversations/{user_id}.json"

    user_message = {"role": "user", "content": user_string}
    bot_message = {"role": "assistant", "content": bot_string}

    data.append(user_message)
    data.append(bot_message)

    with open(file_name, "w") as json_file:
        json.dump(data, json_file)


if __name__ == "__main__":
    app.run(debug=True)
