from bson import json_util
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

import json
from datetime import timedelta

from db import get_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, get_room_members, \
    is_room_admin, update_room, remove_room_members, save_message, get_messages, save_user, get_all_users


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


app = Flask(__name__)
app.secret_key = "1"
socketio = SocketIO(app)

jwt = JWTManager(app)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)


# Parse bson objects as json
def parse_json(data):
    return json.loads(json_util.dumps(data))


@app.route('/whoami', methods=['GET'])
@jwt_required()
def who():
    cur_user = get_jwt_identity()
    return Response(200, str('You are ' + cur_user)).get_json()


@app.route('/login', methods=['POST'])
def login():
    app.logger.info('{} hit /login'.format(request.remote_addr))
    json_input = request.get_json(force=True)

    try:
        user_object = json_input['child']
        username = user_object['username']
        password = user_object['password']
    except KeyError as e:
        return Response(400, 'Invalid request: Missing required field.').get_json()
    except TypeError as e:
        return Response(400, 'Invalid request: Must be a json/dict.').get_json()

    if request.method == 'POST':
        user = get_user(username)

        if user and user.check_password(password):
            access_token = create_access_token(identity=username)
            app.logger.info('%s logged in successfully', user.username)
            response_json = Response(200, str(username + ' has been logged in.'))
            response_json.set_child({'token': access_token})
            return response_json.get_json()
        elif not user:
            return Response(200, 'user does not exist').get_json()
        else:
            app.logger.info('%s failed to log in', username)
            return Response(200, 'wrong password').get_json()
    else:
        return Response(405, '').get_json()

    return Response(500, '').get_json()


@app.route('/room_list')
@jwt_required()
def get_rooms():
    username = get_jwt_identity()
    current_user = get_user(username)
    room_list_bson = get_rooms_for_user(username)
    room_list = []
    for item in room_list_bson:
        room_list.append(parse_json(item))
    json_response = Response(200, 'Fetched all your rooms.')
    json_response.set_child({'Rooms': room_list})
    return json_response.get_json()


@app.route('/room/<room_id>')
@jwt_required()
def single_room(room_id):
    json_input = request.get_json(force=True)
    username = get_jwt_identity()
    room = get_room(room_id)

    try:
        is_dm = room['is_dm']
    except KeyError as e:
        is_dm = False

    current_user = get_user(username)
    if not is_room_member(room_id, username):
        return Response(0, 'You are not a member of this room.').get_json()
    else:
        room_members_bson = get_room_members(room_id)
        room_members = []
        for item in room_members_bson:
            room_members.append(parse_json(item))
        print(room_members)
        message_bson = get_messages(room_id)
        messages = []
        for item in message_bson:
            messages.append(parse_json(item))
        print(messages)
        response_json = Response(200, 'Fetched a room.')
        response_json.set_child({'messages': messages, 'members': room_members, 'is_dm': is_dm})
        return response_json.get_json()

    return Response(500, 'Server error').get_json()


if __name__ == '__main__':
    socketio.run(app, debug=True)

