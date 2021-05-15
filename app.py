# github.com/colingoodman

# Base Imports
import json
import os
import re
from datetime import datetime, timedelta, timezone
from bson import json_util
from bson.json_util import dumps

# Library Imports
from werkzeug.security import safe_str_cmp
from pymongo.errors import DuplicateKeyError
from werkzeug.utils import secure_filename

# Flask Imports
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_socketio import SocketIO, join_room
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt import _jwt

# Local Imports
from db import get_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, get_room_members, \
    is_room_admin, update_room, remove_room_members, save_message, get_messages, save_user, get_all_users, get_user_id, \
    save_image, locate_image, change_user_password
from model.user import User
from model.response import Response

# App Setup
app = Flask(__name__)
app.secret_key = "1"
socketio = SocketIO(app, cors_allowed_origins='*')

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

# LOGIN


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
        try:
            user_id = get_user_id(username)['_id']
            user = get_user(user_id)
        except Exception as e:
            return create_json({'Error': ''})

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


@app.route('/whoami')
@jwt_required()
def who():
    username = get_jwt_identity()
    return create_json({'user': username})


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

# ROOMS


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

    return create_json({'rooms': id_list})


@app.route('/rooms/create')
@jwt_required()
def create_room():
    username = get_jwt_identity()
    json_input = request.get_json(force=True)

    try:
        name = json_input['name']
    except Exception as e:
        return create_json({'Error': 'Issue parsing JSON.'})

    room_id = save_room(name, username)
    return create_json({'Success': '{}'.format(room_id)})


@app.route('/rooms/<room_id>')
@jwt_required()
def single_room(room_id):
    json_input = request.get_json()
    username = get_jwt_identity()
    room = get_room(room_id)

    try:
        is_dm = room['is_dm']
    except KeyError as e:
        is_dm = False

    if not is_room_member(room_id, username):
        return create_json({'Error': 'You are not a member of this room.'})
    else:
        room_name = room['name']
        message_bson = get_messages(room_id)
        messages = []
        for item in message_bson:
            try:
                id = get_user_id(item['sender'])['_id']
            except:
                continue
            messages.append({
                'time_sent': item['time_sent'],
                'text': item['text'],
                'author_username': item['sender'],
                'author_id': id
            })
        return create_json({
            'name': room_name,
            'is_dm': is_dm,
            'messages': messages
        })

    return create_json({'Error': ''})


@app.route('/rooms/<room_id>/messages')
@jwt_required()
def get_room_messages(room_id):
    room = get_room(room_id)
    username = get_jwt_identity()

    if room and is_room_member(room_id, username):
        page = int(request.args.get('page', 0))

        message_bson = get_messages(room_id, page)
        messages = []
        for item in message_bson:
            try:
                id = get_user_id(item['sender'])['_id']
            except Exception as e:
                continue
            messages.append({
                'time_sent': item['time_sent'],
                'text': item['text'],
                'author_username': item['sender'],
                'author_id': id
            })

        return create_json({'messages': messages})
    else:
        return create_json({'Error': 'Room not found'})

    return create_json({'Error': ''})


@app.route('/rooms/<room_id>/members')
@jwt_required()
def single_room_members(room_id):
    json_input = request.get_json()
    username = get_jwt_identity()
    room = get_room(room_id)

    app.logger.info('{} requested members for {}'.format(username, room_id))

    members_raw = get_room_members(room_id)
    members = []

    for member in members_raw:
        try:
            this_user = get_user(get_user_id(member['_id']['username'])['_id'])
        except Exception as e:
            continue
        if not this_user:
            app.logger.info('Encountered unknown user {} in {}'.format(member['_id']['username'], room_id))
            continue

        try:
            avatar = this_user.avatar
        except Exception as e:
            avatar = None

        new_member = {
            'username': this_user.username,
            'ID': this_user.identifier,
            'added_at': member['added_at'].timestamp(),
            'added_by': member['added_by'],
            'is_room_admin': member['is_room_admin'],
            'avatar': avatar
        }
        members.append(parse_json(new_member))

    return create_json({'members': members})

# USERS --


@app.route('/users/<user_id>', methods=['GET'])
@jwt_required()
def view_user(user_id):
    json_input = request.get_json()
    username = get_jwt_identity()

    try:
        int(user_id)
    except ValueError as e:
        return create_json({'Error': 'Bad request; are you using the user ID?'})
    except TypeError as e:
        return create_json({'Error': 'Bad request; are you using the user ID?'})

    app.logger.info('{} viewing profile of {} (GET)'.format(username, user_id))
    user_raw = get_user(int(user_id))
    try:
        avatar = user_raw.avatar
    except Exception as e:
        avatar = None
    user = {
        'username': user_raw.username,
        'email': user_raw.email,
        'phone_number': None,
        'realname': user_raw.realname,
        'avatar': avatar,
        'ID': user_raw.identifier
    }

    return create_json(user)


@app.route('/users/list')
@jwt_required()
def list_users():
    username = get_jwt_identity()
    users_raw = get_all_users()
    users = []

    for user in users_raw:
        try:
            avatar = user['avatar']
        except Exception as e:
            avatar = None
        new_user = {
            'username': user['username'],
            'email': user['email'],
            'phone_number': None,
            'realname': user['realname'],
            'avatar': avatar,
            'date_joined': user['date_joined'].timestamp(),
            'ID': user['_id']
        }
        users.append(new_user)

    return create_json({'users': users})


@app.route('/users/<user_id>/password')
@jwt_required()
def change_password(user_id):
    username = get_jwt_identity()
    json_input = request.get_json()

    if request.method == 'POST':
        app.logger.info('NOTE: {} changing their password'.format(username, user_id))
        new_password = json_input['new_password']
        old_password = json_input['old_password']
        try:
            user_id = get_user_id(username)['_id']
            user = get_user(user_id)
        except Exception as e:
            return create_json({'Error': ''})

        if user and user.check_password(old_password):
            change_user_password(username, new_password)
            return create_json({'Success': 'Password changed'})
        else:
            return create_json({'Error': 'Incorrect password'})

    return create_json({'Error': ''})



# IMAGES


@app.route('/uploads/create', methods=['POST'])
@jwt_required()
def upload_image():
    username = get_jwt_identity()
    json_input = request.get_json()

    if request.method == 'POST':
        room_id = json_input['room_id']

        file = request.files['file']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        image_id = save_image(username, room_id, filepath)

        return create_json({'image_id': image_id})


@app.route('/uploads/<upload_id>')
@jwt_required()
def get_image(upload_id):
    username = get_jwt_identity()
    json_input = request.get_json()
    target_image = locate_image(upload_id)
    app.logger.info("{} attempted to view file {}".format(username, upload_id))

    if target_image:
        image_room = target_image['room_id']

        file_path = target_image['location']
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            return create_json({'File not found': upload_id})
    return create_json({'File not found': upload_id})

# SOCKETS


@socketio.on('new_session')  # https://github.com/miguelgrinberg/Flask-SocketIO/issues/568
def on_connect(self):
    token = _jwt.request_callback()
    app.logger.info("new_session socketio request")
    if token is None:
        return False
    try:
        payload = _jwt.jwt_decode_callback(token)
    except jwt.InvalidTokenError as e:
        return False


@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info("{} has sent message to the room {}: {}"
                    .format(data['username'], data['room'], data['message']))
    data['time_sent'] = datetime.now().strftime('%b %d, %H:%M')
    save_message(data['room'], data['message'], data['username'], is_image=False)
    socketio.emit('receive_message', data, room=data['room'])


if __name__ == '__main__':
    socketio.run(app, debug=True)
