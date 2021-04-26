# github.com/colingoodman
from werkzeug.security import check_password_hash


class User:
    def __init__(self, username, email, password, avatar, realname, identifier):
        self.username = username
        self.email = email
        self.password = password
        self.avatar = avatar
        self.realname = realname
        self.identifier = identifier

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
