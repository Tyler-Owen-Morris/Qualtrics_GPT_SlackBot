from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import login_required, current_user
from transformers import GPT2Tokenizer
from . import db
import boto3
import json

views = Blueprint('views', __name__)
subject_file = "new_subject.json"
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
token_limit = 4096
s3 = boto3.client('s3')
bucket = 'gpt-chatbot-files'


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    data = []
    if request.method == 'POST':
        if request.args.get('new') == 'true':
            print("this is a new subject load- don't overwrite")
        # print("delete no recieved:", request.args)
        converted = convert_immutable_multidict(request.form)
        save_to_json(converted)
        # print("converted:", converted)
        flash('Subject data updated!!', category='success')
    try:
        print("attempting to load file")
        # with open(subject_file, 'r') as file:
        #     data = json.load(file)
        data = load_s3_file()
    except:
        print("pass")
        pass

    return render_template("subjects.html", user=current_user, data=data)


@views.route("/new_subject", methods=["POST"])
@login_required
def create_new_subject():
    print("new subject called")
    try:
        add_empty_object_to_json()
        return {'passed': True}
    except:
        return {'passed': False}


@views.route('/delete_subject', methods=['POST'])
@login_required
def delete_subject():
    my_id = request.json['to_delete']
    print("delete subject called",  my_id)
    try:
        remove_dict_from_json_file(id_number=my_id)
        flash('Subject Removed.', category='success')
        return {'passed': True}
    except:
        return {'passed': False}


def load_s3_file():
    data = s3.get_object(Bucket=bucket, Key=subject_file)
    print("data object", data)
    contents = data['Body'].read()
    print("contents object:", contents)
    return json.load(contents.decode('utf-8'))


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


def save_to_json(data, filename=subject_file):
    with open(filename, 'w') as file:
        json.dump(data, file)


def count_string_tokens(my_text):
    return len(tokenizer.tokenize(my_text))


def remove_dict_from_json_file(id_number, filename=subject_file):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        # print(id_number, len(data))
        data = [d for d in data if d.get("id") != id_number]
        # print("after:", len(data))
        with open(filename, 'w') as file:
            json.dump(data, file)
        return True
    except:
        return False


def add_empty_object_to_json(filename=subject_file):
    with open(filename, 'r') as file:
        data = json.load(file)
    data.append({
        "id": str(len(data)),
        "subject": None,
        "content": None
    })
    print("after update:", data)
    with open(filename, 'w') as file:
        json.dump(data, file)
