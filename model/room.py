from werkzeug.security import check_password_hash
import json
from datetime import datetime


class Room:
    members = {}

    def __init__(self, name):
        self.name = name

    def add_user(self, username):
        now = datetime.now()
        self.members[username] = now

    def add_users(self, user_list):
        now = datetime.now()
        for user in user_list:
            self.add_user(user)

    def get_json(self):
        return 0
