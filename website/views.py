from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, session
from flask_login import login_required, current_user
from transformers import GPT2Tokenizer
from . import db
from .models import SubjectContent, Bot, User, BotOwnership
import boto3
import json
from io import StringIO
from pathlib import Path
from dotenv import load_dotenv
import os

# Load Environment variables
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)

views = Blueprint('views', __name__)
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
token_limit = int(os.environ['MODEL_TOKEN_LIMIT'])
# selected_bot = None


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    data = []
    if request.method == 'POST':
        if request.args.get('new') == 'true':
            print("this is a new subject load- don't overwrite")
        # print("delete no recieved:", request.args)
        converted = convert_immutable_multidict(request.form)
        save_json_to_database(converted)
        # print("converted:", converted)
        flash('Subject data updated!!', category='success')
    mybots = load_user_bots_from_database()
    if 'selected_bot' in session:
        selected_bot = session['selected_bot']
        print("loading selected bot", selected_bot)
        data, bot = load_subject_data_from_database(selected_bot)
    else:
        print("rendering bot page")
        return render_template("bots.html", user=current_user, data=mybots)

    return render_template("subjects.html", user=current_user, data=data, bot=bot)


@views.route("/select_bot", methods=["POST"])
@login_required
def select_bot():
    print("select bot called")
    bot_id = request.json['bot_id']
    try:
        chosen_bot = Bot.query.filter_by(id=bot_id).first()
        if chosen_bot:
            session['selected_bot'] = chosen_bot.id
            print("my new selected bot value:", session["selected_bot"])
        return {'passed': True}
    except:
        return {'passed': False}


@views.route("/unselect_bot", methods=["POST"])
@login_required
def unselect_bot():
    print("unselect bot called")
    try:
        if 'selected_bot' in session:
            del session['selected_bot']
        return {'passed': True}
    except:
        return {'passed': False}


@views.route("/new_subject", methods=["POST"])
@login_required
def create_new_subject():
    print("new subject called")
    try:
        add_blank_subject_to_database(session['selected_bot'])
        return {'passed': True}
    except:
        return {'passed': False}


@views.route('/delete_subject', methods=['POST'])
@login_required
def delete_subject():
    my_id = request.json['to_delete']
    print("delete subject called",  my_id)
    try:
        remove_subject_from_database(my_id)
        flash('Subject Removed.', category='success')
        return {'passed': True}
    except:
        return {'passed': False}


def load_user_bots_from_database():
    myownership = BotOwnership.query.filter_by(user_id=current_user.id).all()
    mybots = []
    for tbot in myownership:
        bot = Bot.query.filter_by(id=tbot.bot_id).first()
        mybots.append(bot)
    return mybots


def load_subject_data_from_database(bot_id):
    mysubjects = SubjectContent.query.filter_by(bot_id=bot_id).all()
    print("my subjects", type(mysubjects), mysubjects)
    bot = Bot.query.filter_by(id=bot_id).first()
    return mysubjects, bot


def save_json_to_database(data):
    print("input :", (data))
    for subj_data in data:
        rec_to_update = SubjectContent.query.get(subj_data['id'])
        rec_to_update.subject = subj_data['subject']
        rec_to_update.content = subj_data['content']
    db.session.commit()
    return


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
    # print(result)
    return result


def count_string_tokens(my_text):
    return len(tokenizer.tokenize(my_text))


def remove_subject_from_database(subj_id):
    subj_to_delete = SubjectContent.query.get(subj_id)
    if subj_to_delete:
        print("put delete statement here")
        db.session.delete(subj_to_delete)
        db.session.commit()
    else:
        print(f"No record found with id:{subj_id}")


def add_blank_subject_to_database(bot_id):
    print("add new subject hit")
    mybot = Bot.query.filter_by(id=bot_id).first()
    new_subject = SubjectContent(
        subject='', content='', bot_id=bot_id, user_id=current_user.id)
    db.session.add(new_subject)
    db.session.commit()
    return
