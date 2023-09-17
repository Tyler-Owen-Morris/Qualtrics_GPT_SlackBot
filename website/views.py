from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import login_required, current_user
from .models import SubjectContent
from . import db
import json

views = Blueprint('views', __name__)
subject_file = "./data/new_subject.json"


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    data = []
    try:
        print("attempting to load file")
        with open(subject_file, 'r') as file:
            data = json.load(file)
    except:
        print("pass")
        pass
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')

        if len(subject) < 1:
            flash('Note is too short!', category='error')
        else:

            # providing the schema for the note
            new_subject = SubjectContent(
                subject=subject, content=content, user_id=current_user.id)
            db.session.add(new_subject)  # adding the note to the database
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("subjects.html", user=current_user, data=data)


# @views.route('/delete-note', methods=['POST'])
# def delete_note():
#     # this function expects a JSON from the INDEX.js file
#     note = json.loads(request.data)
#     noteId = note['noteId']
#     note = Note.query.get(noteId)
#     if note:
#         if note.user_id == current_user.id:
#             db.session.delete(note)
#             db.session.commit()

#     return jsonify({})


@views.route('/delete-subject', methods=['POST'])
def delete_subject():
    # this function expects a JSON from the INDEX.js file
    subject = json.loads(request.data)
    subjectId = subject['subjectId']
    subject = SubjectContent.query.get(subjectId)
    if subject:
        if subject.user_id == current_user.id:
            db.session.delete(subject)
            db.session.commit()

    return jsonify({})
