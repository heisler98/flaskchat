import json

class Response:
    response_code = 0
    context = ''
    child = None

    def __init__(self, response_code, context):
        self.response_code = response_code
        self.context = context  # string
        self.child = None

    def set_child(self, child):
        self.child = child

    # creates and returns a json of this response object
    def get_json(self):
        response_data = {'response': self.response_code, 'context': self.context, 'content': self.child}
        json_dump = json.dumps(response_data)
        json_object = json.loads(json_dump)

        return json_object
