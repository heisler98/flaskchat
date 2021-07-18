# github.com/colingoodman
import json

from bson import json_util

from db import get_messages, get_user


class Message:
    def __init__(self, time_sent, text, username, user_id, avatar, image_id):
        self.time_sent = time_sent
        self.text = text
        self.username = username
        self.user_id = user_id
        self.avatar = avatar
        self.image_id = image_id

    def create_json(self):
        return {
            'time_sent': self.time_sent,
            'text': self.text,
            'username': self.username,
            'user_id': self.user_id,
            'avatar_id': self.avatar,
            'image_id': self.image_id
        }


class Room:
    def __init__(self, name, room_id, is_dm, bucket_number, created_by):
        self.name = name
        self.ID = str(room_id)
        self.is_dm = is_dm
        self.bucket_number = bucket_number
        self.created_by = created_by
        self.messages = self.load_messages()

    def load_messages(self):
        message_bson = get_messages(self.ID, self.bucket_number)
        messages = []
        users = {}  # for tracking users already obtained

        if message_bson and self.bucket_number > 0:
            for item in message_bson:
                try:
                    user_id = str(item['sender'])
                    if user_id not in users:
                        users[user_id] = get_user(user_id)
                    # self, time_sent, text, username, user_id, avatar, image_id
                    messages.append(Message(item['time_sent'], item['text'], users[user_id].username, users[user_id].ID,
                                            users[user_id].avatar, str(item['image_id'])).create_json())
                except Exception as e:
                    print(e)

        return messages

    def create_json(self):
        new_dict = {
            'name': self.name,
            'ID': self.ID,
            'is_dm': self.is_dm,
            'bucket_number': self.bucket_number,
            'created_by': str(self.created_by),
            'messages': self.messages
        }
        return json.loads(json_util.dumps(new_dict))
