import slack
import openai
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, request, jsonify
from slackeventsapi import SlackEventAdapter
from utils.slack_home import home_view
from transformers import GPT2Tokenizer
import segment.analytics as analytics
import string
import boto3
from io import StringIO

# Load Environment variables
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
# Local variable for environment:
environment = os.environ['ENVIRONMENT']
analytics.write_key = os.environ['SEGMENT_WRITE_KEY']
my_model = os.environ['MODEL']
# this controls maximum tokens submitted to OpenAI
token_limit = int(os.environ['MODEL_TOKEN_LIMIT'])
gpt_system_prompt = os.environ['GPT_SYSTEM_PROMPT']
# setup the openapi auth
openai.api_key = os.environ['OPENAI_KEY']

# setup Flask server to handle callback events from slack
application = Flask(__name__)


@application.route("/health")
def health_check():
    payload = {
        'status': 'success'
    }
    return jsonify(payload), 200


my_bot = None
my_bot_id = os.environ['MY_BOT_ID']
db = SQLAlchemy()
db_endpoint = os.environ['DB_DOMAIN']
db_username = os.environ['DB_USERNAME']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
application.config['SECRET_KEY'] = os.environ['LOGIN_SECRET_KEY']
application.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}/{}'.format(
    db_username, db_password, db_endpoint, db_name)
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(application)
with application.app_context():
    db.create_all()


def create_database(app):
    db.create_all(app=app)
    print("Created database!")


class SubjectContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(250))
    content = db.Column(db.String(10000))
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Bot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(150))
    subdomain = db.Column(db.String(100))
    subject_content = db.relationship('SubjectContent')


class BotOwnership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    bots = db.relationship('BotOwnership')
    subjectContent = db.relationship('SubjectContent')


# setup the slack client based on environment
if environment == "PROD":
    slack_event_adapter = SlackEventAdapter(
        os.environ['PROD_SIGNING_SECRET'], '/slack/events', application)
    client = slack.WebClient(token=os.environ['PROD_SLACK_TOKEN'])
else:
    slack_event_adapter = SlackEventAdapter(
        os.environ['DEV_SIGNING_SECRET'], '/slack/events', application)
    client = slack.WebClient(token=os.environ['DEV_SLACK_TOKEN'])
CHANNELS = os.environ['CHANNELS'].split(',')
print("channels:", CHANNELS)
BOT_ID = client.api_call('auth.test')['user_id']
print("MYBOTID::::::", BOT_ID)

# setup tokenizer for counting tokens
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')

# setup global var for tracking repeat messages
last_msg = ''


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    # print("event:", event)
    channel_id = event.get('channel')
    channel_type = event.get('channel_type')
    user_id = event.get('user')
    text = event.get('text')
    ts = event.get('ts')
    thread_ts = event.get('thread_ts')
    print("USERID:", user_id, "  | BOTID:", BOT_ID)
    if text == None:
        return
    print("check string", text.lower()[:14])
    # if it's a DM OR the user
    if (user_id != BOT_ID and "<@"+BOT_ID+">" in text[:14] and channel_id in CHANNELS) or (channel_type == 'im' and user_id != BOT_ID and user_id != None):
        print("channel:", channel_id)
        print("channel type:", channel_type)
        print("thread_ts", thread_ts)
        print("user msg:", text)
        global last_msg
        if text == last_msg:
            return
        else:
            last_msg = text
        if "--model" in text.lower():
            analytics.track(user_id, 'Model Query', {
                'question': text, 'channelType': channel_type, 'channel_id': channel_id})
            if channel_type in ['group', 'channel']:
                if thread_ts != None:
                    ts = thread_ts  # reply in the thread
                client.chat_postMessage(channel=channel_id,
                                        text="I am currently using the model: "+my_model, thread_ts=ts)
            elif channel_type == 'im':
                client.chat_postMessage(channel=channel_id,
                                        text="I am currently using the model: "+my_model)
            return
        if "--reset" in text.lower():
            start_new_conversation(user_id)
            analytics.track(user_id, 'Conversation Reset', {
                'question': text, 'channelType': channel_type, 'channel_id': channel_id})
            if channel_type in ['group', 'channel']:
                if thread_ts != None:
                    ts = thread_ts  # reply in the thread
                client.chat_postMessage(channel=channel_id,
                                        text="Resetting the conversation and dumping memory", thread_ts=ts)
            elif channel_type == 'im':
                client.chat_postMessage(channel=channel_id,
                                        text="Resetting the conversation and dumping memory")
            return
        if "--subject" in text.lower():
            primed_data = list(load_primed_data().keys())
            primed_data.sort()
            print("**************primed data:\n", primed_data)
            subjs = "* • *".join(string.capwords(s)
                                 for s in primed_data)
            # print(">>>>>> SUBJECTS::>>>>>\n", subjs)
            analytics.track(user_id, 'Subject Query', {
                'question': text, 'channelType': channel_type, 'channel_id': channel_id, 'subjects': subjs})
            response = f"I currently have data on the subjects:\n*{subjs}*"
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
        full_msgs, warn, subject_list = construct_chat_history(user_id, text)
        # print("full message with history:", full_msgs)
        print("subject list: ", subject_list)
        completion = openai.ChatCompletion.create(
            model=my_model,
            messages=full_msgs
        )
        resp = completion.choices[0].message.content
        response = resp
        if warn == True:
            response += "\n\n WARNING: Chat history is too long. Use the --reset command to clear cache and start fresh."
        if subject_list is not None:
            print("subj List:", subject_list, "\n", len(
                subject_list), "\n"+resp+"****************")
            subj_str = ", ".join(list(subject_list))
            subj_str = "\n\n_subjects:_\n_["+str(subj_str)+"]_"
            print("subject string:", subj_str)
        print("************making response:", resp)
        if channel_type in ['group', 'channel']:
            my_resp = resp
            if thread_ts is not None:
                ts = thread_ts  # reply in the thread
            if subject_list is not None:
                my_resp += subj_str
            client.chat_postMessage(
                channel=channel_id, text=my_resp, thread_ts=ts)
        elif channel_type == 'im':
            my_resp = resp
            if subject_list is not None:
                my_resp += subj_str
            client.chat_postMessage(channel=channel_id,
                                    text=my_resp)
        analytics.track(user_id, 'Reply Generated', {
                        'question': text, 'response': resp, 'channelType': channel_type, 'channel_id': channel_id, 'subject': subject_list})
        append_and_save_conversation(user_id, text, resp)


# Listen to the app_home_opened Events API event to hear when a user opens your app from the sidebar
@slack_event_adapter.on("app_home_opened")
def app_home_opened(payload):
    event = payload.get('event', {})
    logger = payload.get('logger', {})
    user_id = event.get("user")

    try:
        # Call the views.publish method using the WebClient passed to listeners
        result = client.views_publish(
            user_id=user_id,
            view=home_view)
        # logger.info(result)
        # print("home loaded >", result)
        print("HOME loaded...")

    except Exception as e:
        # logger.error("Error fetching conversations: {}".format(e))
        print("ERROR loading HOME:", e)


def construct_chat_history(uuid, chat):
    tokens = 0
    warn = False
    subj = determine_msg_subject(chat)
    mysubjs = determine_subject(subj)
    # must return an array of the chat history
    base = [{"role": "system", "content": gpt_system_prompt},
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
        while tokens + count_conversation_tokens(history_data) > token_limit:
            warn = True
            print(">>>>>>>>>>>>>conversation too long<<<<<<<<<<<<,",
                  tokens + count_conversation_tokens(history_data))
            history_data = history_data[1:]
        base += history_data
    base += subj_data
    base.append(new)
    return base, warn, mysubjs


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
    subj = set(subj.split(","))
    accum = []
    found = False
    print("<><><><><><><><><><>subjects FROM AI to sort on:", subj)
    for subject in list(loaded.keys()):
        for sub in subj:
            # print("comparing:", subject, "|", sub)
            # if sub.lower().replace(' ', '') in subject.lower().replace(" ", "") or subject.lower().replace(' ', '') in sub.lower().replace(' ', ''):
            if sub.lower().replace(' ', '') == subject.lower().replace(' ', ''):
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


def count_string_tokens(my_text):
    return len(tokenizer.tokenize(my_text))


def determine_msg_subject(question):
    subjects = list(load_primed_data().keys())
    print("SUBJECTS LOADED:", subjects)
    # subjects = [d.get('subject') for d in load_primed_data()]
    subjs = ",".join(subjects)
    print("eligible subjects:", subjs)
    completion = openai.ChatCompletion.create(
        model=my_model,
        messages=[{"role": "system", "content": f"You are a classification bot. The user will feed you a question and you will return which subjects it relates to with ONLY the name of the subject(s). The only eligible subjects are: {subjs}. you will not elaborate. you will not add extra words. You will JUST reply with the single subject or comma separated list of up to 5 subjects. The subject(s) you reply with MUST be in the provided list: {subjs}. You will not invent new subjects- the subject(s) will ONLY be a maximum of 5 of these: {subjs}. If the question is not related to any of these subjects you will reply with the string 'None'. Reply with 'OK' if you understand."},
                  {"role": "assistant", "content": "OK"},
                  {"role": "user", "content": question}]
    )
    resp = completion.choices[0].message.content
    print("----------------- SUBJECT LIST PASS 1:", resp)
    return resp


def load_primed_data():
    try:
        # Read the file data
        mysubjects = SubjectContent.query.filter_by(bot_id=my_bot_id).all()
        for sub in mysubjects:
            print("sub:", sub.subject, sub.content)
        return convert_list_of_dicts(mysubjects)
    except Exception as e:
        print("file-load failed - loading nothing", e)
        return {}


def convert_list_of_dicts(data):
    new_dict = {}
    print("incoming data", data)
    for d in data:
        new_dict[d.subject] = d.content
    print('after organization of dict', new_dict)
    return new_dict


def convert_immutable_multidict(data):
    result = []
    # get maximum index
    max_index = max([int(key.split('_')[-1]) for key in data.keys()])
    for i in range(1, max_index + 1):
        id_key = f'id_{i}'
        subject_key = f'subject_{i}'
        content_key = f'content_{i}'

        my_content = data[content_key]
        while count_string_tokens(my_content) > int(token_limit/4)*3:
            print("my string tokens:", count_string_tokens(my_content))
            subtractor = 10
            # if the number of tokens difference is too large, we subtract a larger amount of characters than the default 10
            if count_string_tokens(my_content) - int(token_limit/4)*3 > subtractor:
                subtractor = count_string_tokens(
                    my_content) - int(token_limit/4)*3
            print("subtracting:", subtractor)
            my_content = my_content[:-subtractor]

        if subject_key in data and content_key in data and id_key in data:
            result.append({
                'id': data[id_key],
                'subject': data[subject_key],
                'content': my_content
            })
    print(result)
    return result


def run_bot():
    from waitress import serve
    if environment == "PROD":
        # WSGI server is required for production to allow simultaneous requests
        serve(application, host='0.0.0.0')
    else:
        # Development server runs as default
        # 0.0.0.0 allows run on public server.
        # application.run('0.0.0.0', debug=True, port=os.environ['SLACKBOT_PORT'])
        serve(application, host='0.0.0.0')


if __name__ == "__main__":
    # run_bot()
    application.run()
