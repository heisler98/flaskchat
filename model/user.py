# github.com/colingoodman
import json

from bson import json_util
from flask import jsonify
from werkzeug.security import check_password_hash


class User:
    def __init__(self, username, email, password, avatar, real_name, identifier, prev_avatars=None, date_joined=None):
        self.username = username
        self.email = email
        self.password = password
        self.date_joined = date_joined
        if avatar:
            self.avatar = str(avatar)
        else:
            self.avatar = None
        self.real_name = real_name
        self.ID = str(identifier)  # ObjectId in DB
        self.previous_avatars = prev_avatars

    @staticmethod
    def is_authenticated(self):
        return True

    @staticmethod
    def is_active(self):
        return True

    @staticmethod
    def is_anonymous(self):
        return False

    def get_username(self):
        return self.username

    def get_identifier(self):
        return self.identifier

    # flask-login
    def get_id(self):
        return self.username

    def check_password(self, password_input):
        return check_password_hash(self.password, password_input)

    def create_json(self):
        # username, email, password, avatar, realname, identifier, prev_avatars=None
        new_dict = {
            'username': self.username,
            'email': self.email,
            'avatar': self.avatar,
            'ID': str(self.ID),
            'real_name': self.real_name,
            'previous_avatars': self.previous_avatars
        }
        return json.loads(json_util.dumps(new_dict))
