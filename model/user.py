# github.com/colingoodman

from werkzeug.security import check_password_hash
import json


class User:
    username = ''
    email = ''
    password = ''

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password  # hash of user password

    @staticmethod
    def is_authenticated(self):
        return True

    @staticmethod
    def is_active(self):
        return True

    @staticmethod
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    def check_password(self, password_input):
        return check_password_hash(self.password, password_input)

    def get_json(self):
        output = {'username': self.username, 'password': self.password, 'email': self.email}

        json_dump = json.dumps(output)
        json_object = json.loads(json_dump)

        return json_object
