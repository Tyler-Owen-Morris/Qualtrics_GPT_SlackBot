from flask import Flask, render_template, redirect, request
from bot import run_bot
import multiprocessing
import json

app = Flask(__name__)
my_bot = None
# subject_file = "./subject.json"
subject_file = "./data/new_subject.json"


def run_website():
    app.run('0.0.0.0', debug=False, port=8000)


website_process = multiprocessing.Process(target=run_website, args=())

# Utility Functions


def start():
    bot_process = multiprocessing.Process(target=run_bot, args=())
    bot_process.start()
    return bot_process


def stop(bot_process):
    bot_process.terminate()
    bot_process.join()


def add_empty_object_to_json(filename=subject_file):
    with open(filename, 'r') as file:
        data = json.load(file)
    data.append({
        "id": len(data),
        "subject": None,
        "content": None
    })
    print("after update:", data)
    with open(filename, 'w') as file:
        json.dump(data, file)


def convert_immutable_multidict(data):
    result = []
    # get maximum index
    max_index = max([int(key.split('_')[-1]) for key in data.keys()])
    for i in range(1, max_index + 1):
        id_key = f'id_{i}'
        subject_key = f'subject_{i}'
        content_key = f'content_{i}'

        if subject_key in data and content_key in data and id_key in data:
            result.append({
                'id': data[id_key],
                'subject': data[subject_key],
                'content': data[content_key]
            })
    print(result)
    return result


def save_to_json(data, filename=subject_file):
    with open(filename, 'w') as file:
        json.dump(data, file)


@app.route("/start_bot")
def start_bot():
    print("start called")
    global my_bot
    if (my_bot == None):
        my_bot = start()
        return "STARTED"
    else:
        return "ALREADY RUNNING"


@app.route("/stop_bot")
def stop_bot():
    global my_bot
    if (my_bot):
        if (my_bot.is_alive()):
            stop(my_bot)
            my_bot = None
        return "STOPPED"
    else:
        return "ALREADY STOPPED"


@app.route("/new_subject", methods=["POST"])
def create_new_subject():
    print("new subject called")
    try:
        add_empty_object_to_json()
        return {'passed': True}
    except:
        return {'passed': False}


@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == "POST":
        print("form request:", request.form, type(request.form))
        if request.args.get('new') == 'true':
            print("this is a new subject load- don't overwrite")
        converted = convert_immutable_multidict(request.form)
        save_to_json(converted)
        print("converted:", converted)
    global my_bot
    with open(subject_file, 'r') as file:
        data = json.load(file)
    new_list = []
    for obj in data:
        # key, value = list(obj.items())[0]
        # new_dict = {"subject": key, "content": value}
        # new_list.append(new_dict)
        new_list.append(obj)

    if (my_bot):
        print(my_bot.is_alive())
        return render_template('index.html', status="On", data=new_list)
    else:
        return render_template('index.html', status="Off", data=new_list)


def main():
    global my_bot
    my_bot = start_bot()
    processes = (my_bot, website_process)
    # processes[0].start()
    processes[1].start()
    # processes[0].join()
    processes[1].join()


if __name__ == '__main__':
    main()
