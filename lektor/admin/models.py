from flask import current_app
from flask.ext.login import UserMixin, make_secure_token
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy(current_app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    pw_hash = db.Column(db.String(40))
    tmp_token = db.Column(db.String(128))

    def __init__(self, username):
        self.username = username

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def set_password(self, password):
        self.tmp_token = ''
        self.pw_hash = generate_password_hash(password)

    def unset_password(self):
        self.pw_hash = ''

    def check_password(self, password):
        return check_password_hash(
            self.pw_hash, password) if self.pw_hash else False

    def make_tmp_token(self):
        self.tmp_token = make_secure_token(self.username)
        return self.tmp_token
