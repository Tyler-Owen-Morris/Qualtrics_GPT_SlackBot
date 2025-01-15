import slack
from openai import OpenAI
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
import time
from io import StringIO
import threading
import datetime
from utils.aws_utils import upload_folder_to_s3
from utils.qualtrics_utils import write_response_to_survey

# Load Environment variables
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
# Local variable for environment:
environment = os.environ['ENVIRONMENT']
analytics.write_key = os.environ['SEGMENT_WRITE_KEY']
my_model = os.environ['MODEL']
# this controls maximum tokens submitted to OpenAI
gpt_system_prompt = os.environ['GPT_SYSTEM_PROMPT']
# Limit Handling
token_limit = int(os.environ['MODEL_TOKEN_LIMIT'])
# globals for limit reporting
rate_limit_limitRequests = None
rate_limit_limitTokens = None
rate_limit_remaining_requests = None
rate_limit_remaining_tokens = None
rate_limit_reset = None

aiclient = OpenAI(
    api_key=os.environ['OPENAI_TOKEN']
)
# Hardcoded Values
bucket_name = 'gpt-chatbot-files'
local_folder_path = 'conversations'

# setup Flask server to handle callback events from slack
application = Flask(__name__)


@application.route("/health")
def health_check():
    payload = {
        'status': 'success'
    }
    return jsonify(payload), 200


@application.route('/backup-logs', methods=['POST'])
def backup_logs():
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")
        s3_folder_path = f"{os.environ['S3_LOG_FOLDER']}/{ts}/"
        upload_folder_to_s3(bucket_name, s3_folder_path, local_folder_path)
        return jsonify(status='success'), 200
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500


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


# def create_database(app):
#     db.create_all(app=app)
#     print("Created database!")


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
    # print("USERID:", user_id, "  | BOTID:", BOT_ID)
    if text == None:
        return
    # print("check string", text.lower()[:14])
    # if it's a DM OR the user
    if (user_id != BOT_ID and "<@"+BOT_ID+">" in text[:14] and channel_id in CHANNELS) or (channel_type == 'im' and user_id != BOT_ID and user_id != None):
        print("channel:", channel_id)
        print("channel type:", channel_type)
        print("thread_ts", thread_ts)
        print("user msg:", text)
        last_user_message = get_last_user_content(user_id)
        global last_msg
        print("last user message", last_user_message)
        if text == last_user_message or text == last_msg:
            # if message is a duplicate then ignore it.
            return
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
            # print("**************primed data:\n", primed_data)
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
        if "--image" in text.lower()[:7]:
            myprompt = text[7:]
            print("image prompt:", myprompt)
            img_response = aiclient.images.generate(
                model="dall-e-3",
                prompt=myprompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            img_url = img_response.data[0].url
            print("image url:", img_url)
            if channel_type in ['group', 'channel']:
                if thread_ts is not None:
                    ts = thread_ts  # reply in the thread
                client.chat_postMessage(
                    channel=channel_id, text="Here is your image", attachments=[{"image_url": img_url, "alt_text": "image", "fallback": "your image"}], thread_ts=ts)
            elif channel_type == 'im':
                client.chat_postMessage(channel=channel_id,
                                        attachments=[
                                            {"image_url": img_url, "alt_text": "image", "fallback": "your image"}],
                                        text="Here is your image")
            return
        if "--rates" in text.lower()[:7]:
            if rate_limit_limitTokens is None:
                no_data_message = "There is no rate limit data currently available. Ask a message to the bot to cache new data before using this command again."
                post_message_to_slack(
                    no_data_message, channel_type, ts, thread_ts, channel_id)
            else:
                rate_limit_pct = int(
                    (int(rate_limit_remaining_tokens) / int(rate_limit_limitTokens))*100)
                rate_limit_message = f"I currently have *%{rate_limit_pct}* of my token capacity remaining.\nI have used *{str(int(rate_limit_limitTokens)-int(rate_limit_remaining_tokens))}* leaving *{rate_limit_remaining_tokens}* tokens available of the total *{rate_limit_limitTokens}* allowed.\nI have gone through *{int(rate_limit_limitRequests)- int(rate_limit_remaining_requests)}* requests of the total *{rate_limit_limitRequests}* requests allowed leaving *{rate_limit_remaining_requests}* remaining."
                post_message_to_slack(
                    rate_limit_message, channel_type, ts, thread_ts, channel_id)
            return

        # SEEDED CHAT OPTION
        if channel_type in ['group', 'channel']:
            # drop the bot opening from history and henceforth
            text = text[14:]
        full_msgs, token_limit_warning, subject_list, total_tokens = construct_chat_history(
            user_id, text)
        # print("full message with history:", full_msgs)
        # print("subject list: ", subject_list)

        # Generate the response from the openai client
        response = aiclient.chat.completions.with_raw_response.create(
            model=my_model,
            messages=full_msgs
        )
        completion = response.parse()

        # Get Rate limit data
        near_rate_limit_warning = handle_openai_limit_data(response=response)
        # Handle responding if we've already hit the rate limit
        if response.status_code == 429:
            limit_message = "You have reached the rate limit for openAI - please wait before querying the bot again."
            post_message_to_slack(
                limit_message, channel_type, ts, thread_ts, channel_id)
            return
        # Parse the response from the bot
        bot_response = completion.choices[0].message.content
        response = bot_response

        # if user is nearing the token limit, append a warning to the message
        if token_limit_warning == True:
            response += "\n\n*WARNING*: Chat history is too long. Use the --reset command to clear cache and start fresh."

        # If nearing openai ratelimit send warning back with the response message
        if near_rate_limit_warning:
            response += "\n\n*WARNING*: You are nearing the OpenAI API rate limit. Use the --reset command to reduce your token usage, or wait a few minutes before resuming your conversation."

        # if subjects were used from the database, append them to the message
        subj_str = ''
        if subject_list is not None:
            # print("subj List:", subject_list, "\n", len(
            #     subject_list), "\n"+resp+"****************")
            subj_str = ", ".join(list(subject_list))
            subj_str = "\n\n_subjects:_\n_["+str(subj_str)+"]_"
            # print("subject string:", subj_str)
        # print("************making response:", resp)
        token_string = None
        if total_tokens > 10000:
            cost = round(total_tokens * 0.000005, 2)
            token_string = f"\n\n_tokens: {total_tokens} | cost: ${cost}_"
        post_message_to_slack(bot_response, channel_type, ts,
                              thread_ts, channel_id, subj_str, token_string)

        # Record message to Analytics Tracker
        analytics.track(user_id, 'Reply Generated', {
                        'question': text, 'response': bot_response, 'channelType': channel_type, 'channel_id': channel_id, 'subject': subject_list})
        # Save the data locally for message history
        append_and_save_conversation(
            user_id, text, bot_response, subject_list, total_tokens)


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


def handle_openai_limit_data(response):
    global rate_limit_limitRequests
    global rate_limit_limitTokens
    global rate_limit_remaining_requests
    global rate_limit_remaining_tokens
    global rate_limit_reset
    near_limit = False
    rate_limit_limitRequests = response.headers.get(
        'x-ratelimit-limit-requests')
    rate_limit_limitTokens = response.headers.get(
        'x-ratelimit-limit-tokens')
    rate_limit_remaining_requests = response.headers.get(
        'x-ratelimit-remaining-requests')
    rate_limit_remaining_tokens = response.headers.get(
        'x-ratelimit-remaining-tokens')
    rate_limit_reset = response.headers.get('x-ratelimit-reset-requests')
    rate_limit_pct = int(rate_limit_remaining_tokens) / \
        int(rate_limit_limitTokens)
    rate_limit_pct = int(rate_limit_pct*100)
    print(f"Rate Limit Requests: {rate_limit_limitRequests}")
    print(f"Requests Remaining Requests: {rate_limit_remaining_requests}")
    print(f"Rate Limit Tokens: {rate_limit_limitTokens}")
    print(f"Rate Limit Remaining Tokens {rate_limit_remaining_tokens}")
    print(f"Rate Limit Resets at: {rate_limit_reset}")
    print(f"Rate Limit percentage: %{rate_limit_pct}")
    if rate_limit_pct <= 20:
        near_limit = True
    return near_limit


def post_message_to_slack(message, channel_type, ts, thread_ts, channel_id, subj_str='',  token_string=None):
    if channel_type in ['group', 'channel']:
        my_message = message
        if thread_ts is not None:
            ts = thread_ts  # reply in the thread
        if subj_str != '':
            my_message += subj_str
        if token_string is not None:
            my_message += token_string
        client.chat_postMessage(
            channel=channel_id, text=my_message, thread_ts=ts)
    elif channel_type == 'im':
        my_message = message
        if subj_str != '':
            my_message += subj_str
        if token_string is not None:
            my_message += token_string
        client.chat_postMessage(channel=channel_id,
                                text=my_message)


def construct_chat_history(uuid, chat):
    total_tokens = 0
    warn = False
    subj = determine_msg_subject(chat)
    mysubjs = determine_subject(subj)
    # must return an array of the chat history
    base = [{"role": "system", "content": gpt_system_prompt},
            {"role": "assistant", "content": "OK"}]
    subj_data = load_subj_data(mysubjs)
    new_message = {'role': 'user', 'content': chat}
    new_tokens = count_conversation_tokens([new_message])
    base_tokens = count_conversation_tokens(base)
    primed_tokens = count_conversation_tokens(subj_data)
    total_tokens += base_tokens + new_tokens + primed_tokens
    history_data = load_or_create_json_file(uuid)
    if len(history_data) > 0:
        historical_data_tokens = count_conversation_tokens(history_data)
        print('historical conversation tokens:', historical_data_tokens)
        removal_count = 0
        while total_tokens + historical_data_tokens > token_limit:
            warn = True
            print(">>>>>>>>>>>>>conversation too long<<<<<<<<<<<<,",
                  total_tokens + count_conversation_tokens(history_data))
            history_data = history_data[1:]
            historical_data_tokens = count_conversation_tokens(history_data)
            removal_count += 1
            if removal_count >= 100:
                break
        base += history_data
    base += subj_data
    base.append(new_message)
    total_tokens = count_conversation_tokens(base)
    print(f"message using {total_tokens} tokens")
    return base, warn, mysubjs, total_tokens


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
    while count_conversation_tokens([{'content': "data:"+text}]) > round(token_limit/2):
        # print("shortening loaded data:", len(text))
        text = text[15:]
    # Construct
    ret = [{"role": "system", "content": "data: "+text}]
    return ret


def determine_subject(subj):
    loaded = load_primed_data()
    subj = set(subj.split(","))
    accum = []
    found = False
    # print("<><><><><><><><><><>subjects FROM AI to sort on:", subj)
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


def get_last_user_content(user_id):
    data = load_or_create_json_file(user_id)
    if not data or data == [[]]:
        return ""
    for message in reversed(data):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def append_and_save_conversation(user_id, user_string, bot_string, subject_string, total_tokens):
    try:
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
    except:
        print("failed to write conversation to local json file")

    # Write the response to Qualtrics (try)
    try:
        write_response_to_survey(
            my_bot_id, user_string, bot_string, subject_string, user_id, total_tokens)
    except:
        print("failed to write data to Qualtrics survey")


def start_new_conversation(user_id):
    file_name = f"conversations/{user_id}.json"
    # Check if file exists
    if not os.path.exists(file_name):
        # If not, create the file and initialize with an empty array inside of an array
        with open(file_name, "w") as json_file:
            # Creates an empty array inside of an array
            json.dump([[]], json_file)
        return
    # If file exists, proceed to append an empty array
    with open(file_name, "r") as json_file:
        try:
            data = json.load(json_file)
        except json.JSONDecodeError:
            # In case the file is empty and can't be parsed
            data = [[]]
    convo = []
    data.append(convo)
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
    # print("SUBJECTS LOADED:", subjects)
    # subjects = [d.get('subject') for d in load_primed_data()]
    subjs = ",".join(subjects)
    # print("eligible subjects:", subjs)
    completion = aiclient.chat.completions.create(
        model=my_model,
        messages=[{"role": "system", "content": f"You are a classification bot. The user will feed you a question and you will return which subjects it relates to with ONLY the name of the subject(s). The only eligible subjects are: {subjs}. you will not elaborate. you will not add extra words. You will JUST reply with the single subject or comma separated list of up to 5 subjects. The subject(s) you reply with MUST be in the provided list: {subjs}. You will not invent new subjects- the subject(s) will ONLY be a maximum of 5 of these: {subjs}. If the question is not related to any of these subjects you will reply with the string 'None'. Reply with 'OK' if you understand."},
                  {"role": "assistant", "content": "OK"},
                  {"role": "user", "content": question}]
    )
    resp = completion.choices[0].message.content
    # print("----------------- SUBJECT LIST PASS 1:", resp)
    return resp


def load_primed_data():
    try:
        # Read the file data
        mysubjects = SubjectContent.query.filter_by(bot_id=my_bot_id).all()
        # for sub in mysubjects:
        #     print("sub:", sub.subject, sub.content)
        return convert_list_of_dicts(mysubjects)
    except Exception as e:
        print("file-load failed - loading nothing", e)
        return {}


def convert_list_of_dicts(data):
    new_dict = {}
    # print("incoming data", data)
    for d in data:
        new_dict[d.subject] = d.content
    # print('after organization of dict', new_dict)
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
            # print("my string tokens:", count_string_tokens(my_content))
            subtractor = 10
            # if the number of tokens difference is too large, we subtract a larger amount of characters than the default 10
            if count_string_tokens(my_content) - int(token_limit/4)*3 > subtractor:
                subtractor = count_string_tokens(
                    my_content) - int(token_limit/4)*3
            # print("subtracting:", subtractor)
            my_content = my_content[:-subtractor]

        if subject_key in data and content_key in data and id_key in data:
            result.append({
                'id': data[id_key],
                'subject': data[subject_key],
                'content': my_content
            })
    # print(result)
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


def schedule_upload():
    while True:
        try:
            ts = datetime.datetime.now().strftime("%Y-%m-%d")
            s3_folder_path = f"{os.environ['S3_LOG_FOLDER']}/{ts}/"
            upload_folder_to_s3(bucket_name, s3_folder_path, local_folder_path)
        except:
            pass
        time.sleep(7200)  # Sleep for 2 hours before the next upload


def run_app():
    application.run()


if __name__ == "__main__":

    application_thread = threading.Thread(target=run_app)
    application_thread.start()

    upload_thread = threading.Thread(target=schedule_upload)
    upload_thread.start()

    application_thread.join()
    upload_thread.join()
