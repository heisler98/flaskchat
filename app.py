# github.com/colingoodman

# Base Imports
import json
import re
from datetime import datetime, timedelta
from bson import json_util
from bson.json_util import dumps

# Library Imports
from werkzeug.security import safe_str_cmp
from pymongo.errors import DuplicateKeyError

# Flask Imports
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

# Local Imports
from db import get_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, get_room_members, \
    is_room_admin, update_room, remove_room_members, save_message, get_messages, save_user, get_all_users
from model.user import User
from model.response import Response

# App Setup
app = Flask(__name__)
app.secret_key = "1"
socketio = SocketIO(app)

# JWT Configuration
jwt = JWTManager(app)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_HEADER_NAME"] = 'tasty_token'


# --- Helper Functions ---
def parse_json(data):
    return json.loads(json_util.dumps(data))


def create_json(some_dictionary):
    return json.loads(json.dumps(some_dictionary))


# --- API ---

@app.route('/login', methods=['POST'])
def login():
    app.logger.info('{} hit /login'.format(request.remote_addr))
    json_input = request.get_json(force=True)

    try:
        username = json_input['username']
        password = json_input['password']
    except KeyError as e:
        return create_json({'Error': 'Invalid request: Missing required field.'})
    except TypeError as e:
        return create_json({'Error': 'Invalid request: Must be a json/dict.'})

    if request.method == 'POST':
        user = get_user(username)

        if user and user.check_password(password):
            access_token = create_access_token(identity=username)
            app.logger.info('%s logged in successfully', user.username)
            return create_json({'Token': access_token})
        elif not user:
            return create_json({'Error': 'User not found.'})
        else:
            app.logger.info('%s failed to log in', username)
            return create_json({'Error': 'Wrong password.'})
    else:
        return create_json({'Error': ''})

    return create_json({'Error': ''})


@app.route('/signup')
def create_account():
    json_input = request.get_json()
    user_object = json_input['child']

    try:
        username = user_object['username']
        password = user_object['password']
        email = user_object['email']
        full_name = user_object['name']
    except KeyError as e:
        return create_json({'Error': 'Invalid request: Missing required field.'})
    except TypeError as e:
        return create_json({'Error': 'Invalid request: Must be a json/dict.'})

    if re.match("^[A-Za-z_]*$", username):
        try:
            save_user(username, email, password, full_name)
            # username, email, password, fullname
            return create_json({'200': 'User created.'})
        except DuplicateKeyError:
            return create_json({'Error': 'User already exists.'})

    return create_json({'Error': ''})


@app.route('/rooms/list')
@jwt_required()
def get_rooms():
    username = get_jwt_identity()
    room_list_raw = get_rooms_for_user(username)
    room_list = []

    for item in room_list_raw:
        room_list.append(parse_json(item))

    id_list = []

    for item in room_list:
        id_list.append(item['_id']['room_id']['$oid'])

    return create_json({'Rooms': id_list})


@app.route('/rooms/<room_id>')
@jwt_required() # needs to return top level dict
def single_room(room_id):
    json_input = request.get_json()
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


@app.route('/rooms/<room_id>/members')
@jwt_required()
def single_room(room_id):
    json_input = request.get_json()
    username = get_jwt_identity()
    room = get_room(room_id)

    members = room['members']
    return None # return just usernames


@app.route('/users/<user_id>', methods=['GET'])
@jwt_required()
def view_user(user_id):
    json_input = request.get_json()
    username = get_jwt_identity()

    app.logger.info('{} viewing profile of {} (GET)'.format(username, user_id))
    user = get_user(user_id).get_json()

    response_json = Response(200, 'Fetched a user.')
    response_json.set_child({'user': user})

    return response_json.get_json()


if __name__ == '__main__':
    socketio.run(app, debug=True)
