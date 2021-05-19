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
from flask_cors import CORS, cross_origin

# Flask Imports
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_socketio import SocketIO, join_room, rooms
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

# Local Imports
from db import get_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, get_room_members, \
    is_room_admin, update_room, remove_room_members, save_message, get_messages, save_user, get_all_users, get_user_id, \
    save_image, locate_image, change_user_password, change_user_realname, find_dm, create_dm, change_user_avatar
from model.user import User
from model.response import Response

# App Setup
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.secret_key = "dev"
socketio = SocketIO(app, cors_allowed_origins='*')
connected_sockets = {}

# JWT Configuration
jwt = JWTManager(app)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_HEADER_NAME"] = 'tasty_token'

# Uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'uploads'


# --- Helper Functions ---
def parse_json(data):
    return json.loads(json_util.dumps(data))


def create_json(some_dictionary):
    return json.loads(json.dumps(some_dictionary))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- API ---

# LOGIN


@app.route('/login', methods=['POST'])
@cross_origin()
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
            refresh_token = create_refresh_token(identity=username)
            app.logger.info('%s logged in successfully', user.username)
            return create_json({'Token': access_token, 'Refresh': refresh_token})
        elif not user:
            return create_json({'Error': 'User not found.'})
        else:
            app.logger.info('%s failed to log in', username)
            return create_json({'Error': 'Wrong password.'})
    else:
        return create_json({'Error': ''})

    return create_json({'Error': ''})


@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)

    return create_json({'Token': access_token})


@app.route('/whoami', methods=['GET'])
@jwt_required(fresh=True)
def who():
    username = get_jwt_identity()
    return create_json({'user': username})


@app.route('/', methods=['GET'])
def hello():
    return create_json({'Hello': 'World'})


@app.route('/signup', methods=['POST'])
@cross_origin()
def create_account():
    json_input = request.get_json()
    user_object = json_input['child']

    try:
        username = user_object['username']
        password = user_object['password']
        email = user_object['email']
        full_name = user_object['name']
        app.logger.info('{} trying to create a new account, {}'.format(request.remote_addr, username))
    except KeyError as e:
        return create_json({'Error': 'Invalid request: Missing required field.'})
    except TypeError as e:
        return create_json({'Error': 'Invalid request: Must be a json/dict.'})

    if re.match("^[A-Za-z_]*$", username):
        try:
            save_user(username, email, password, full_name)
            app.logger.info('{} created a new account, {}'.format(request.remote_addr, username))
            return create_json({'200': 'User created.'})
        except DuplicateKeyError:
            return create_json({'Error': 'User already exists.'})

    return create_json({'Error': ''})

# ROOMS


@app.route('/rooms/list', methods=['GET'])
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


@app.route('/rooms/create', methods=['POST'])
@jwt_required(fresh=True)
def create_room():
    username = get_jwt_identity()
    json_input = request.get_json(force=True)

    try:
        name = json_input['name']
    except Exception as e:
        return create_json({'Error': 'Issue parsing JSON.'})

    room_id = save_room(name, username)
    return create_json({'Success': '{}'.format(room_id)})


@app.route('/rooms/dm/<user_id>', methods=['GET'])
@jwt_required(fresh=True)
def view_dm(user_id):
    username = get_jwt_identity()

    user_one = get_user(get_user_id(username))
    user_two = get_user(user_id)

    target_room = find_dm(user_one, user_two)
    if target_room:
        return create_json({'room_id': target_room})
    else:
        new_dm = create_dm(user_one, user_two)
        return create_json({'room_id': new_dm})


@app.route('/rooms/<room_id>', methods=['GET'])
@jwt_required(fresh=True)
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


@app.route('/rooms/<room_id>/messages', methods=['GET'])
@jwt_required(fresh=True)
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


@app.route('/rooms/<room_id>/members', methods=['GET'])
@jwt_required()
def single_room_members(room_id):
    username = get_jwt_identity()

    app.logger.info('{} requested members for {}'.format(username, room_id))

    members_raw = get_room_members(room_id)
    members = []

    for member in members_raw:
        try:
            this_user = get_user(get_user_id(member['_id']['username'])['_id'])
        except KeyError as e:
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
    username = get_jwt_identity()

    app.logger.info('{} viewing profile of {} (GET)'.format(username, user_id))
    user_raw = get_user(int(user_id))

    try:
        some_avatar = user_raw.avatar
    except AttributeError as e:
        some_avatar = None

    try:
        some_username = user_raw.username
    except AttributeError as e:
        return create_json({'Error': 'Bad request; are you using the user ID?'})

    user = {
        'username': some_username,
        'email': user_raw.email,
        'phone_number': None,
        'realname': user_raw.realname,
        'avatar': some_avatar,
        'ID': user_raw.identifier
    }

    return create_json(user)


@app.route('/users/list', methods=['GET'])
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


@app.route('/users/<user_id>/password', methods=['POST'])
@jwt_required(fresh=True)
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


@app.route('/users/<user_id>/edit', methods=['POST'])
@jwt_required(fresh=True)
def edit_user(user_id):  # NOT FINISHED YET
    username = get_jwt_identity()
    json_input = request.get_json()

    var_changes = dict(json_input).keys()

    target_user = get_user(user_id)
    if target_user.username != username:
        return create_json({'Error': 'Not authorized'})

    if len(var_changes) == 0:
        return create_json({'Error': 'Empty json input'})

    for key in var_changes:
        if key == 'realname':
            change_user_realname(user_id, json_input[key])

# IMAGES


@app.route('/uploads/create', methods=['POST'])
@jwt_required(fresh=True)
def upload_image():
    username = get_jwt_identity()
    json_input = request.get_json()
    app.logger.info("{} attempted to upload a file".format(username))

    if request.method == 'POST':
        room_id = json_input['room_id']
        file = request.files['file']

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        image_id = save_image(username, room_id, filepath)

        return create_json({'image_id': image_id})


@app.route('/uploads/<upload_id>', methods=['GET'])
@jwt_required()
def get_image(upload_id):
    username = get_jwt_identity()
    target_image = locate_image(upload_id)
    app.logger.info("{} attempted to view file {}".format(username, upload_id))

    if target_image:
        image_room = target_image['room_id']
        if not is_room_member(image_room, username) and not target_image['avatar']:  # avatars can be accessed anywhere
            return create_json({'Error': 'Not authorized'})

        file_path = target_image['location']
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            return create_json({'File not found': upload_id})
    return create_json({'File not found': upload_id})


@app.route('/avatar/<user_id>', methods=['GET'])
@jwt_required()
def get_avatar(user_id):
    target_user = get_user(user_id)

    if not target_user:
        return create_json({'Error': 'User not found'})

    if request.method == 'GET':
        target_image_id = target_user.avatar
        if not target_image_id:
            return create_json({'Error': 'No associated avatar with this user'})
        image_location = locate_image(upload_id=target_image_id)['location']

        if os.path.exists(image_location):
            return send_file(image_location)
        else:
            return create_json({'File not found': image_location})


@app.route('/avatar/<user_id>/create', methods=['POST'])
@jwt_required(fresh=True)
def new_avatar(user_id):
    username = get_jwt_identity()
    target_user = get_user(user_id)

    if not target_user:
        return create_json({'Error': 'User not found'})

    if target_user.username != username:
        app.logger.info('!!! {} tried to change another users avatar: {}'.format(username, target_user.username))
        return create_json({'Error': 'Not authorized'})

    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)

        if filename == '':
            return create_json({'Error': 'Bad filename'})
        if not file:
            return create_json({'Error': 'Bad file'})
        if not allowed_file(file):
            return create_json({'Error': 'Bad file type'})

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_id = save_image(None, None, filepath, is_avatar=True)
        change_user_avatar(target_user.username, image_id)

        app.logger.info('{} {} changed their avatar'.format(user_id, username))
        return create_json({'Success': 'Avatar changed, GET user for ID'})


# STATISTICS


@app.route('/stats/message_count', methods=['GET'])
@jwt_required()
def message_count():
    return None

# SOCKETS


@socketio.on('new_session')
@jwt_required()
def on_connect(data):
    user_identity = get_jwt_identity()  # user_identity is username, NOT id

    join_room('server')
    current_socket_id = request.sid

    connected_sockets[user_identity] = current_socket_id
    app.logger.info("{} has connected, {}".format(user_identity, current_socket_id))


@socketio.on('close_session')
@jwt_required()
def on_disconnect(data):
    user_identity = get_jwt_identity()  # user_identity is username, NOT id
    current_socket_id = connected_sockets[user_identity]
    app.logger.info("{} is disconnecting, {}".format(user_identity, current_socket_id))

    connected_sockets.pop(user_identity)


@socketio.on('send_message')
@jwt_required(fresh=True)
def handle_send_message_event(data):
    username = data['username']
    room = data['room']  # client must pass room id here
    message = data['message']
    is_image = data['include_image']
    try:
        image_id = data['image_id']
    except Exception as e:
        image_id = None
    time_sent = datetime.now().strftime('%b %d, %H:%M')
    data['time_sent'] = time_sent

    app.logger.info("{} has sent message to the room {} at {}".format(username, room, time_sent))

    save_message(room, message, username, is_image, image_id)  # to db

    room_member_objects = get_room_members(room)  # determine who should receive this message
    room_member_usernames = []

    for db_item in room_member_objects:
        room_member_usernames.append(db_item['_id']['username'])

    if username in room_member_usernames:  # if the author/sender is in the room they are trying to send to
        for member in room_member_usernames:
            if member in connected_sockets:
                target_socket_id = connected_sockets[member]
                app.logger.info("emit message to {} in {} at {}".format(username, room, time_sent))
                socketio.emit('receive_message', data, room=target_socket_id)  # emit to specific user


if __name__ == '__main__':
    socketio.run(app, debug=True)
