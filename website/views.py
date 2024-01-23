from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, session
from flask_login import login_required, current_user
from sqlalchemy import func
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
    mybots = load_user_bots_from_database()
    if 'selected_bot' in session:
        selected_bot = session['selected_bot']
        print("loading selected bot", selected_bot)
        data, bot = load_subject_data_from_database(selected_bot)
    else:
        print("rendering bot page", mybots)
        return render_template("bots.html", user=current_user, data=mybots)
    return render_template("subjects.html", user=current_user, data=data, bot=bot, max_tokens=str(int(token_limit/4)))


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


@views.route('/save_subject', methods=['POST'])
@login_required
def save_subject():
    my_id = request.json['to_save']
    my_content = request.json['content']
    my_subject = request.json['subject']
    res = update_subject_content(my_id, my_content, my_subject)
    if res:
        return {'passed': True}
    else:
        return {'passed': False}


def load_user_bots_from_database():
    myownership = BotOwnership.query.filter_by(user_id=current_user.id).all()
    mybots = []
    for tbot in myownership:
        bot = Bot.query.filter_by(id=tbot.bot_id).first()
        mybots.append(bot)
    return mybots


def load_subject_data_from_database(bot_id):
    mysubjects = SubjectContent.query.filter_by(bot_id=bot_id).order_by(
        func.lower(SubjectContent.subject)).all()
    print("my subjects", type(mysubjects), mysubjects)
    bot = Bot.query.filter_by(id=bot_id).first()
    return mysubjects, bot


def count_string_tokens(my_text):
    return len(tokenizer.tokenize(my_text))


def update_subject_content(subj_id, new_content, new_subject):
    subj_to_update = SubjectContent.query.get(subj_id)
    if subj_to_update:
        # Reduce the count of tokens
        while count_string_tokens(new_content) > (token_limit/4):
            subtractor = 10
            if count_string_tokens(new_content) - int(token_limit/4) > subtractor:
                subtractor = count_string_tokens(
                    new_content) - int(token_limit/4)
            print("subtracting:", subtractor)
            new_content = new_content[:-subtractor]
        # Update the 'content' attribute of the found subject
        subj_to_update.content = new_content
        subj_to_update.subject = new_subject
        subj_to_update.tokens = count_string_tokens(new_content)
        print("modified:", subj_to_update)
        # Commit the change to the database
        db.session.commit()
        print(f"Content for record with id:{subj_id} has been updated.")
        return True
    else:
        print(f"No record found with id:{subj_id}")
        return False


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
        subject='', content='', tokens=0, bot_id=bot_id, user_id=current_user.id)
    db.session.add(new_subject)
    db.session.commit()
    return
