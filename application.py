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
        serve(application, host='0.0.0.0', port=5000)
    else:
        # Development server runs as default
        application.run()


if __name__ == "__main__":
    run_website()
