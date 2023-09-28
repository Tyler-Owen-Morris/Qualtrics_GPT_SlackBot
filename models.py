from .application import db
from flask_login import UserMixin
from sqlalchemy.sql import func


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
