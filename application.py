from website import create_app
from pathlib import Path
from dotenv import load_dotenv
import segment.analytics as analytics
import os

# Load Environment variables
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
# Local variable for environment:
environment = os.environ['ENVIRONMENT']
analytics.write_key = os.environ['SEGMENT_WRITE_KEY']
application = create_app()


def run_website():
    from waitress import serve
    print("starting website")
    if environment == "PROD":
        # WSGI server is required for production to allow simultaneous requests
        serve(application, host='0.0.0.0')
    else:
        # Development server runs as default
        # 0.0.0.0 allows run on public server.
        # app.run('0.0.0.0', debug=False, port=os.environ['WEBSITE_PORT'])
        serve(application, host='0.0.0.0')


if __name__ == "__main__":
    application.run()
