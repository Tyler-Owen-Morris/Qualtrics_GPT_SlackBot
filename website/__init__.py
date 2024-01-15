from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from pathlib import Path
from os import path
from dotenv import load_dotenv
import os
import slack
import threading

db = SQLAlchemy()
# DB_NAME = "database.db"
envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
# Local variable for environment:
environment = os.environ['ENVIRONMENT']

db_endpoint = os.environ['DB_DOMAIN']
db_username = os.environ['DB_USERNAME']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
# db_table = os.environ['DB_TABLE_NAME']


def create_app():
    app = Flask(__name__)

    @app.route("/health")
    def health_check():
        payload = {
            'status': 'success'
        }
        return jsonify(payload), 200

    app.config['SECRET_KEY'] = os.environ['LOGIN_SECRET_KEY']
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}/{}'.format(
        db_username, db_password, db_endpoint, db_name)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Bot, BotOwnership, SubjectContent

    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    db.create_all(app=app)
    print('Created Database!')
