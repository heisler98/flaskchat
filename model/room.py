# github.com/colingoodman
import json

from bson import json_util

class Message:
    def __init__(self, time_sent, text, username, user_id, avatar, image_id):
        self.time_sent = time_sent
        self.text = text
        self.username = username
        self.user_id = str(user_id)
        self.avatar = avatar
        self.image_id = str(image_id)

    def create_json(self):
        if self.image_id != None:
            return {
                'time_sent': self.time_sent,
                'text': self.text,
                'username': self.username,
                'user_id': self.user_id,
                'image_id': self.image_id
            }
        else:
            return {
                'time_sent': self.time_sent,
                'text': self.text,
                'username': self.username,
                'user_id': self.user_id
            }


class Room:
    def __init__(self, name, room_id, is_dm, bucket_number, created_by, emoji=None):
        self.name = name
        self.messages = []
        self.room_id = str(room_id)
        self.is_dm = is_dm
        self.bucket_number = bucket_number
        self.created_by = created_by
        self.emoji = emoji

    def set_messages(self, messages):
        self.messages = messages

    def create_json(self):
        new_dict = {
            'name': self.name,
            'room_id': self.room_id,
            'is_dm': self.is_dm,
            'bucket_number': self.bucket_number,
            'created_by': str(self.created_by),
            'messages': self.messages,
            'emoji': self.emoji
        }
        return json.loads(json_util.dumps(new_dict))

    def create_personalized_json(self, new_name):
        new_dict = { 
            'name': new_name,
            'room_id': self.room_id,
            'is_dm': self.is_dm,
            'bucket_number': self.bucket_number,
            'created_by': str(self.created_by),
            'messages': self.messages,
            'emoji': self.emoji
        }
        return json.loads(json_util.dumps(new_dict))
    
