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
        if "--subjects" in text.lower():
            subjs = "*\n*".join(list(load_primed_data().keys()))
            # print(">>>>>> SUBJECTS::>>>>>\n", subjs)
            response = f"I currently have data on the subjects: \n *{subjs}*"
            if channel_type in ['group', 'channel']:
                if thread_ts != None:
                    ts = thread_ts  # reply in the thread
                client.chat_postMessage(
                    channel=channel_id, text=response, thread_ts=ts)
            elif channel_type == 'im':
                client.chat_postMessage(channel=channel_id,
                                        text=response)
            return

        # SEEDED CHAT OPTION
        if channel_type in ['group', 'channel']:
            # drop the bot opening from history and henceforth
            text = text[14:]
        full_msgs, warn = construct_chat_history(user_id, text)
        print("full message with history:", full_msgs)

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
    subj = determine_msg_subject(chat)
    mysubjs = determine_subject(subj)
    # must return an array of the chat history
    base = [{"role": "system", "content": "You are a Qualtrics assistant. You will ONLY answer questions about the setup and functionality of the survey platform Qualtrics, and you will do so as accurately and concisely as you can. You will refuse to answer any questions unrelated to Qualtrics. The system will give you data on the specific subject of the user's question - the data from the system will override any other information you have on the subject. The data from the system will be formatted with a URL where the information was found, followed by a summary of the information. You will not give the user URLs that the system has not provided. You will not make up URLs. You will use the data from the system to more accurately answer the users question. Reply with OK if you understand."},
            {"role": "assistant", "content": "OK"}]
    subj_data = load_subj_data(mysubjs)
    new = {'role': 'user', 'content': chat}
    new_tokens = count_conversation_tokens([new])
    base_tokens = count_conversation_tokens(base)
    primed_tokens = count_conversation_tokens(subj_data)
    tokens += base_tokens + new_tokens + primed_tokens
    history_data = load_or_create_json_file(uuid)
    if len(history_data) > 0:
        data_tokens = count_conversation_tokens(history_data)
        print('historical conversation tokens:', data_tokens)
        while tokens + count_conversation_tokens(history_data) > 4096:
            warn = True
            print(">>>>>>>>>>>>>conversation too long<<<<<<<<<<<<,",
                  tokens + count_conversation_tokens(history_data))
            history_data = history_data[1:]
        base += history_data
    base += subj_data
    base.append(new)
    return base, warn


def load_subj_data(subjs):
    # return empty array for no subjects
    if subjs == None:
        return []
    # load the full subject data
    data = load_primed_data()
    text = ""
    for subj in subjs:
        text += data[subj]+" "
    # limit the token count
    while count_conversation_tokens([{'content': "data:"+text}]) > 3000:
        print("shortening loaded data:", len(text))
        text = text[15:]
    # Construct
    ret = [{"role": "system", "content": "data: "+text}]
    return ret


def determine_subject(subj):
    loaded = load_primed_data()
    subj = subj.split(",")
    accum = []
    found = False
    for subject in list(loaded.keys()):
        for sub in subj:
            print("comparing:", subject, "|", sub)
            if sub.lower().replace(' ', '') in subject.lower().replace(" ", "") or subject.lower().replace(' ', '') in sub.lower().replace(' ', ''):
                accum.append(subject)
                found = True
    if found:
        return accum
    else:
        return None


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


def determine_msg_subject(question):
    subjects = list(load_primed_data().keys())
    subjs = ",".join(subjects)
    print("eligible subjects:", subjs)
    completion = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{"role": "system", "content": f"You are a classification bot. The user will feed you a question and you will return which subjects it relates to with ONLY the name of the subject(s). The only eligible subjects are: {subjs}. you will not elaborate. you will not add extra words. You will JUST reply with the single subject or comma separated list of up to 5 subjects. The subject(s) you reply with MUST be in the provided list: {subjs}. You will not invent new subjects- the subject(s) will ONLY be a maximum of 5 of these: {subjs}. If the question is not related to any of these subjects you will reply with the string 'None'. Reply with 'OK' if you understand."},
                  {"role": "assistant", "content": "OK"},
                  {"role": "user", "content": question}]
    )
    resp = completion.choices[0].message.content
    print("bot thinks this question is to do with this subject:", resp)
    return resp


def load_primed_data():
    file_name = "data/primed_created-1.json"
    try:
        # Read the file data
        with open(file_name, "r") as json_file:
            data = json.load(json_file)
        # returns a dictionary of the historical tweets
        return data
    except Exception as e:
        print("file-load failed - loading nothing", e)
        return {}


if __name__ == "__main__":
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)
    # app.run('0.0.0.0', debug=True)  # 0.0.0.0 allows run on public server
