from flask import Flask, render_template
from bot import run_bot
from views import views
import multiprocessing
import json

app = Flask(__name__)
my_bot = None
subject_file = "./subject.json"


def start():
    bot_process = multiprocessing.Process(target=run_bot, args=())
    bot_process.start()
    return bot_process


def stop(bot_process):
    bot_process.terminate()
    bot_process.join()


def run_website():
    app.run('0.0.0.0', debug=False, port=8000)


website_process = multiprocessing.Process(target=run_website, args=())


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


@app.route("/")
def home():
    global my_bot
    with open(subject_file, 'r') as file:
        data = json.load(file)
    new_list = []
    for obj in data:
        key, value = list(obj.items())[0]
        new_dict = {"subject": key, "content": value}
        new_list.append(new_dict)

    if (my_bot):
        print(my_bot.is_alive())
        return render_template('index.html', status="On", data=new_list)
    else:
        return render_template('index.html', status="Off", data=new_list)


def main():
    processes = (my_bot, website_process)
    # processes[0].start()
    processes[1].start()
    # processes[0].join()
    processes[1].join()


if __name__ == '__main__':
    main()
