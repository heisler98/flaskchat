# github.com/colingoodman
import json
from model.message import Message, Reaction
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from bson.json_util import dumps
from flask_jwt import JWT, jwt_required, current_identity
from pymongo.errors import DuplicateKeyError
from db import get_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, get_room_members, \
    is_room_admin, update_room, remove_room_members, save_message, get_messages, save_user, get_all_users, get_dm
from werkzeug.security import safe_str_cmp

from model.room import Room
from model.user import User

app = Flask(__name__)
app.secret_key = "1"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)

### JWT


def authenticate(username, password):
    username_table = {u.username: u for u in get_all_users()}
    user = username_table.get(username, None)
    if user and safe_str_cmp(user.password.encode('utf-8'), password.encode('utf-8')):
        return user


def identity(payload):
    userid_table = {u.id: u for u in get_all_users()}
    user_id = payload['identity']
    return userid_table.get(user_id, None)

##### NEW CODE

connectedUsers = {};

class Response:
    response_code = 0
    context = ''
    child = None

    def __init__(self, response_code, context):
        self.response_code = response_code
        self.context = context
        self.child = None

    def set_child(self, child):
        self.child = child

    # creates and returns a json of this response object
    def get_json(self):
        response_data = {'response': self.response_code, 'context': self.context, 'content': self.child}
        json_dump = json.dumps(response_data)
        json_object = json.loads(json_dump)

        return json_object


@app.route('/login', methods=['POST'])
def login():
    json_input = request.get_json(force=True)

    if current_user.is_authenticated:  # prevents user from logging in again
        return Response(401, 'Already logged in').get_json()

    try:
        user_object = json_input['child']
        username = user_object['username']
        password = user_object['password']
    except:
        return Response(400, 'unable to parse request').get_json()

    if request.method == 'POST':
        user = get_user(username)

        if user and user.check_password(password):
            login_user(user, remember=True)
            app.logger.info('%s logged in successfully', user.username)
            return Response(200, str(current_user.username + ' has been logged in.')).get_json()
        else:
            app.logger.info('%s failed to log in', user.username)
            return Response(200, 'wrong password').get_json()
    else:
        return Response(405).get_json()

    return Response(500).get_json()


@app.route('/whoami', methods=['GET'])
@login_required
def who():
    return Response(200, current_user.username).get_json()


@app.route('/logout', methods=['POST'])
@login_required
def logout(json_input):
    json_input = request.get_json(force=True)
    try:
        user_object = json_input['child']
        username = user_object['username']
    except:
        return Response(400).get_json()

    user = get_user(username)

    try:
        logout_user()
        app.logger.info('%s logged in successfully', user.username)
        return Response(200, 'successful logout').get_json()
    except:
        return Response(500).get_json()


@app.route('/room', methods=['POST'])
def add_room():
    json_input = request.get_json(force=True)

    try:
        token = json_input['token']
        child = json_input['child']

        room_name = child['name']
        room_members = child['members']
    except:
        return Response(400, 'unable to parse request').get_json()

    usernames = [username.strip() for username in request.form.get('members').split(',')]

    if request.method == 'POST':
        if len(room_name) and len(room_members):
            room_id = save_room(room_name, current_user.username)

            if current_user.username in usernames:
                room_members.remove(current_user.username)
            add_room_members(room_id, room_name, usernames, current_user.username)

            return Response(200, 'New room created').get_json()

    return Response(500, 'Error creating new room').get_json()


@app.route('/room/{roomId}')
def single_room():
    json_input = request.get_json(force=True)

    try:
        token = json_input['token']
    except:
        pass


@app.route('/user', methods=['POST'])
def add_user():
    json_input = request.get_json(force=True)

    try:
        token = json_input['token']
        child = json_input['child']

        username = child['username']
        password = child['password']
        email = child['email']
    except Exception as err:
        return Response(400, str(err)).get_json()

    try:
        save_user(username, email, password)
    except DuplicateKeyError as err:
        return Response(400, str(err)).get_json()

    return Response(200, 'created a user').get_json()


@app.route('/user/<user>', methods=['GET'])
def single_user(user):
    # json_input = request.get_json(force=True) # there should not be an input here
    requested_user = get_user(user)

    output = Response(200, 'here is a user')
    output.set_child(requested_user.get_json())
    return output.get_json()


@app.route('/', methods=['GET', 'POST'])
def ios_test_endpoint():
    json_data = request.get_json(force=True)
    secret = json_data["secret"]
    child = json_data["child"]
    username = child["username"]
    password = child["password"]
    return str(username + password)


##### OLD CODE

@app.route('/test')
def home():
    rooms = []
    if current_user.is_authenticated:
        rooms = get_rooms_for_user(current_user.username)
        print('rooms', rooms)
    else:
        return render_template('login.html')
    return render_template('index.html', rooms=rooms)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            save_user(username, email, password)
            return redirect(url_for('login'))
        except DuplicateKeyError:
            message = "User already exists!"
    return render_template('signup.html', message=message)


@app.route('/members')
@login_required
def members_list():
    message = ''
    list_of_users = get_all_users()
    return render_template('members.html', users=list_of_users)


def create_chat():
    message = ''


@app.route('/create-room', methods=['GET', 'POST'])
@login_required
def create_room():
    message = ''
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        usernames = [username.strip() for username in request.form.get('members').split(',')]
        if len(room_name) and len(usernames):
            room_id = save_room(room_name, current_user.username, is_dm=False)
            if current_user.username in usernames:
                usernames.remove(current_user.username)
            add_room_members(room_id, room_name, usernames, current_user.username)
            return redirect(url_for('view_room', room_id=room_id))
        else:
            message = 'Failed to create room'
    return render_template('create_room.html', message=message)


@app.route('/rooms/<room_id>/')
@login_required
def view_room(room_id):
    room = get_room(room_id)
    try:
        is_dm = room['is_dm']
    except KeyError:
        is_dm = False
    if room and is_room_member(room_id, current_user.username):
        room_members = get_room_members(room_id)
        messages = get_messages(room_id)
        rooms = get_rooms_for_user(current_user.username)
        return render_template('view_room.html',
                               username=current_user.username,
                               this_room=room,
                               messages=messages,
                               room_members=room_members,
                               other_rooms=rooms,
                               is_dm=is_dm)
    else:
        return "Room not found", 404


@app.route('/rooms/<room_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
        room_members_str = ",".join(existing_room_members)
        message = ''
        if request.method == 'POST':
            room_name = request.form.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)

            new_members = [username.strip() for username in request.form.get('members').split(',')]
            members_to_add = list(set(new_members) - set(existing_room_members))
            members_to_remove = list(set(existing_room_members) - set(new_members))
            if len(members_to_add):
                add_room_members(room_id, room_name, members_to_add, current_user.username)
            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            message = 'Room edited successfully'
            room_members_str = ",".join(new_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str, message=message)
    else:
        return "Room not found", 404


@socketio.on('send_message')
def handle_send_message_event(data):
    timestamp = datetime.now().strftime('%H:%M')

    # unpack the delivered json object
    try:
        input_data = json.load(data)

        message_object = input_data['child']
        username = message_object['username']
        room = message_object['room']
        content = message_object['message']
    except:
        socketio.emit(500)

    # log that a message was sent
    app.logger.info("{} to {} @ {}: {}".format(username, room, timestamp, content))

    # create a new message object with a json accordingly
    new_message = Message(username, room, content, timestamp)
    new_message_json = new_message.get_json()

    # put this new message in the database and send it out
    save_message(new_message)
    socketio.emit(new_message_json)


@socketio.on('join_room')
def handle_join_room_event(data):
    print('handle_join_room_event', data)
    app.logger.info("{} has joined the room {}".format(data['username'], data['room']))
    join_room(data['room'])
    socketio.emit('join_room_announcement', data)


@app.route('/rooms/<room_id>/messages/')
@login_required
def get_older_messages(room_id):
    print('!! view room', current_user.username, room_id)
    room = get_room(room_id)
    if room and is_room_member(room_id, current_user.username):
        page = int(request.args.get('page', 0))
        messages = get_messages(room_id, page)
        return dumps(messages)
    else:
        return "Room not found", 404


@socketio.on('leave_room')
def handle_leave_room_event(data):
    print('handle_leave_room_event', data)
    app.logger.info("{} has left the room {}".format(data['username'], data['room']))
    socketio.emit('leave_room_announcement', data)


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(user_id)
    except:
        return None


if __name__ == '__main__':
    socketio.run(app, debug=True)
