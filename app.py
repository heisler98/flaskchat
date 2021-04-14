# github.com/colingoodman

import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_socketio import SocketIO, join_room
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from bson.json_util import dumps
from pymongo.errors import DuplicateKeyError
from werkzeug.utils import secure_filename
from db import get_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, get_room_members, \
    is_room_admin, update_room, remove_room_members, save_message, get_messages, save_user, get_all_users, find_dm, \
    create_dm, \
    get_room_id, update_user, save_image, locate_image, save_avatar

app = Flask(__name__)
app.secret_key = "my secret key"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    today = datetime.now()
    date_string = today.strftime("%A, %B %d, %Y")
    rooms = []
    users = []
    app.logger.info('Visitor from {}'.format(request.remote_addr))
    if current_user.is_authenticated:
        rooms = get_rooms_for_user(current_user.username)
        users = get_all_users()
    else:
        return render_template('login.html')
    return render_template('index.html', rooms=rooms, users=users, time=date_string)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload/<room_id>', methods=['POST'])
def upload_file(room_id):
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        save_image(current_user.username, room_id, filepath)
    return view_room(room_id)


@app.route('/avatar/<user_id>', methods=['POST'])
def upload_avatar(user_id):
    if request.method == 'POST' and current_user.username == user_id:
        app.logger.info('{} changed their avatar'.format(user_id))
        file = request.files['file']
        filename = secure_filename(file.filename)
        if filename == '':
            return redirect('/users/{}'.format(user_id))
        if file and allowed_file(filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            save_avatar(user_id, filepath)
    return redirect('/users/{}'.format(user_id))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if re.match("^[A-Za-z_]*$", username):  # check if username is valid
            try:
                save_user(username, email, password)
                return redirect(url_for('login'))
            except DuplicateKeyError:
                message = "User already exists!"
        else:
            message = 'Invalid username.'

    return render_template('signup.html', message=message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:  # prevents user from logging in again
        return redirect('/')
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password_input = request.form.get('password')
        user = get_user(username)

        if not username:
            message = 'Enter a username.'
            return render_template('login.html', message=message)
        if not password_input:
            message = 'Enter a password.'
            return render_template('login.html', message=message)

        try:
            valid_password = user.check_password(password_input)
        except AttributeError:
            message = 'Failed to login.'
            return render_template('login.html', message=message)

        if user and valid_password:
            login_user(user)
            return redirect('/')
        elif user:
            message = 'Incorrect password.'
        else:
            message = 'Failed to login.'
    return render_template('login.html', message=message)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/create-room', methods=['GET', 'POST'])
@login_required
def create_room():
    message = ''
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        usernames = [username.strip() for username in request.form.get('members').split(',')]
        if len(room_name) and len(usernames):
            room_id = save_room(room_name, current_user.username)
            if current_user.username in usernames:
                usernames.remove(current_user.username)
            add_room_members(room_id, room_name, usernames, current_user.username, is_dm=False)
            return redirect(url_for('view_room', room_id=room_id))
        else:
            message = 'Failed to create room'
    return render_template('create_room.html', message=message)


@app.route('/avatars/<user_id>')
@login_required
def get_avatar(user_id):
    user = get_user(user_id)
    avatar_path = user.avatar
    return send_file(avatar_path)


@app.route('/uploads/<image_id>')
@login_required
def get_image(image_id):
    target_image = locate_image(image_id)
    app.logger.info("{} attempted to view file {}".format(current_user.username, image_id))
    if target_image:
        file_path = target_image['location']
        return send_file(file_path)
    return 'File not found', 404


@app.route('/rooms/<room_id>/')
@login_required
def view_room(room_id):
    # print('!! view room', current_user.username, room_id)
    app.logger.info('{} is viewing {}'.format(current_user.username, room_id))
    room = get_room(room_id)
    is_dm = False
    rooms = []
    users = []
    rooms = get_rooms_for_user(current_user.username)
    users = get_all_users()
    is_admin = is_room_admin(room_id, current_user.username)

    try:
        is_dm = room['is_dm']
    except:
        is_dm = False

    if room and is_room_member(room_id, current_user.username):
        room_members = get_room_members(room_id)
        messages = get_messages(room_id)
        return render_template('view_room.html',
                               username=current_user.username,
                               is_dm=is_dm,
                               room=room,
                               rooms=rooms,
                               users=users,
                               is_admin=is_admin,
                               messages=messages,
                               room_members=room_members)
    elif room and not is_room_member(room_id, current_user.username):
        return "Not authorized", 400
    else:
        return "Room not found", 404


@app.route('/view_dm/<other_user>')
@login_required
def view_dm(other_user):
    user_one = current_user
    user_two = get_user(other_user)

    target_room = find_dm(user_one, user_two)
    if target_room:
        return redirect(url_for('view_room', room_id=target_room))
    else:
        new_dm = create_dm(user_one, user_two)
        return redirect(url_for('view_room', room_id=new_dm))


@app.route('/users/<user_id>', methods=['GET'])
@login_required
def view_user(user_id):
    user = get_user(user_id)
    avatar_path = user.avatar
    print(avatar_path)
    return render_template('profile.html', user=user, username=user_id)


@app.route('/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = get_user(user_id)
    if user and user_id == current_user.username:
        message = ''
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            update_user(username, email)
            message = 'User edited successfully'
            return render_template('edit_user.html', user=user)
        return render_template('edit_user.html', user=user)
    return 'Page not found', 400


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

            app.logger.info('{} edited room {} from {}'.format(current_user.username, room_name, request.remote_addr))

            new_members = [username.strip() for username in request.form.get('members').split(',')]
            members_to_add = list(set(new_members) - set(existing_room_members))
            members_to_remove = list(set(existing_room_members) - set(new_members))
            if len(members_to_add):
                add_room_members(room_id, room_name, members_to_add, current_user.username, is_dm=False)
            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            message = 'Room edited successfully'
            room_members_str = ",".join(new_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str, message=message)
    elif room and not is_room_admin(room_id, current_user.username):
        return "You are not authorized to edit this room.", 400
    else:
        return "Room not found", 404


@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info("handle_send_message_event: {} has sent message to the room {}: {}"
                    .format(data['username'], data['room'], data['message']))
    data['time_sent'] = datetime.now().strftime('%b %d, %H:%M')
    save_message(data['room'], data['message'], data['username'])
    socketio.emit('receive_message', data, room=data['room'])


@socketio.on('join_room')
def handle_join_room_event(data):
    # print('handle_join_room_event', data)
    app.logger.info("{} has joined the room {}".format(data['username'], data['room']))
    join_room(data['room'])
    # socketio.emit('join_room_announcement', data)


def emit_image(image_id):
    image = locate_image(image_id)
    image_file_path = image['location']
    time = datetime.now().strftime("%b %d, %H:%M")

    data = {'image_file_path': image_file_path, 'author': image['author'], 'time': time}
    socketio.emit('receive_image', data)


@app.route('/rooms/<room_id>/messages/')
@login_required
def get_older_messages(room_id):
    # print('!! view room', current_user.username, room_id)
    room = get_room(room_id)
    if room and is_room_member(room_id, current_user.username):
        page = int(request.args.get('page', 0))
        messages = get_messages(room_id, page)
        return dumps(messages)
    else:
        return "Room not found", 404


@socketio.on('leave_room')
def handle_leave_room_event(data):
    # print('handle_leave_room_event', data)
    app.logger.info("{} has left the room {}".format(data['username'], data['room']))
    socketio.emit('leave_room_announcement', data)


@login_manager.user_loader
def load_user(username):
    return get_user(username)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)
    #socketio.run(app, debug=True)
