import json


class Message:
    def __init__(self, author, room, content, timestamp):
        self.author = author
        self.content = content
        self.room = room
        self.timestamp = timestamp

    def get_json(self):
        output = {'author': self.author, 'room': self.room, 'content': self.content}

        json_dump = json.dumps(output)
        json_object = json.loads(json_dump)

        return json_object


class Reaction:
    pass
