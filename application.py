from website import create_app
from pathlib import Path
from dotenv import load_dotenv
import segment.analytics as analytics
import os
from slackeventsapi import SlackEventAdapter
import slack
from slackbot.slackbot import run_bot
import multiprocessing

# Load Environment variables
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
# Local variable for environment:
environment = os.environ['ENVIRONMENT']
analytics.write_key = os.environ['SEGMENT_WRITE_KEY']
app = create_app()


def run_website():
    from waitress import serve
    print("starting website")
    if environment == "PROD":
        # WSGI server is required for production to allow simultaneous requests
        serve(app, host='0.0.0.0', port=os.environ['WEBSITE_PORT'])
    else:
        # Development server runs as default
        # 0.0.0.0 allows run on public server.
        # app.run('0.0.0.0', debug=False, port=os.environ['WEBSITE_PORT'])
        serve(app, host='0.0.0.0', port=os.environ['WEBSITE_PORT'])


def run_slackbot():
    print("starting slackbot")
    run_bot()


def run_startup_process():
    websiteProcess = multiprocessing.Process(target=run_website)
    slackbotProcesss = multiprocessing.Process(target=run_slackbot)
    websiteProcess.start()
    slackbotProcesss.start()
    websiteProcess.join()
    slackbotProcesss.join()


class CustomApplicationObj:

    def __init__(self) -> None:
        pass

    def run(self, *args, **kwargs):
        run_startup_process()


application = CustomApplicationObj()

if __name__ == "__main__":
    # run_startup_process()
    application.run()
