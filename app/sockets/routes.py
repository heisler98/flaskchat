# github.com/colingoodman
from datetime import datetime
import time

from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import join_room, SocketIO, join_room, rooms

from library.apns import NotificationSystem
from app import socketio
# import redis

from db import save_message, get_room_members, get_user_id, update_checkout, get_user, get_apn, add_reaction, \
    get_latest_bucket_number, purge_apn, get_room, room_is_mute

from app.sockets import sockets_blueprint

# threading
import threading

global connected_sockets
connected_sockets = {}  # will need to move off into something like redis

notification_interface = NotificationSystem()


def announce_connect(user_id):
    socketio.emit('user_online', {
        'user_id': f'{user_id}'
    })


def announce_disconnect(user_id):
    socketio.emit('user_offline', {
        'user_id': f'{user_id}'
    })


@sockets_blueprint.route('/online', methods=['GET'])
@jwt_required()
def who_online():
    online_users = []
    for user_id in connected_sockets.keys():
        if len(connected_sockets[user_id]) > 1:
            online_users.append(user_id)
    return jsonify(online_users), 200


# return user_id list of currently online members of a given room
def room_online_members(room_id):
    room_members_list = get_room_members(room_id)
    output = []

    for room_member in room_members_list:
        output.append(str(room_member['_id']['user_id']))

    return output


# this event is automatic, triggered by a new socket connection
@socketio.on('connect')
@jwt_required()
def client_connect():
    user_id = get_jwt_identity()

    new_socket_id = request.sid
    current_app.logger.info('A socket for {} with ID {} has been created...'.format(user_id, new_socket_id))

    if not user_id:
        current_app.logger.info('WARNING: Someone attempted to connect without authentication! Closing {}'
                                .format(new_socket_id))
        socketio.disconnect(new_socket_id)

    join_room('server')  # add this new socket to room "server"

    if user_id in connected_sockets:
        # if user already has an open socket
        open_sockets_for_user = connected_sockets[user_id]
        open_sockets_for_user.append(new_socket_id)
        connected_sockets[user_id] = open_sockets_for_user
    else:
        # user does not have an open socket atm
        this_user = [new_socket_id]
        connected_sockets[user_id] = this_user

    announce_connect(user_id)
    current_app.logger.info(
        '{} now has the following sockets open: {}'.format(user_id, connected_sockets[user_id]))


def remove_connection(disconnected_id):
    current_app.logger.info('A socket with ID {} disconnected...'.format(disconnected_id))

    for key in connected_sockets:
        user_sockets = connected_sockets[key]
        if disconnected_id in user_sockets:
            user_sockets.remove(disconnected_id)
            current_app.logger.info(
                '{} belonged to {}. They now have the following sockets open: {}'.format(disconnected_id, key,
                                                                                         connected_sockets[key]))

            if len(user_sockets) == 0:
                update_last_seen(key)  # broke?
                announce_disconnect(key)

    current_app.logger.info(connected_sockets)


@socketio.on('kill_socket')
def client_disconnect():
    disconnected_id = request.sid
    remove_connection(disconnected_id)


# this event is automatic, triggered by a broken socket connection
@socketio.on('disconnect')
def client_disconnect():
    disconnected_id = request.sid
    remove_connection(disconnected_id)


# update user object in DB to note when they were last online
def update_last_seen(username):
    user_id = get_user_id(username)
    update_checkout(user_id)


def check_mute(user_id, room_id):
    return room_is_mute(room_id, user_id)


# return true if emit, false if apns
def handle_message_emit(target_user_id, data):
    if target_user_id in connected_sockets and len(connected_sockets[target_user_id]) != 0:
        target_socket_ids = connected_sockets[target_user_id]
        try:
            for socket in target_socket_ids:
                socketio.emit('receive_message', data, room=socket)  # emit to specific user
                current_app.logger.info('Sent to {}'.format(socket))
                return True
        except TypeError as e:
            current_app.logger.info('Failed to emit message to {}, connected on {}. They may not have an open '
                                    'connection. {}'.format(target_user_id, connected_sockets[target_user_id], e))
    else:  # send push notifications for anyone offline
        return False


def grab_and_validate_message_data(data, user_id):
    username = str(data['username'])
    user = get_user(user_id)

    room_id = str(data['room'])
    room = get_room(room_id)

    message = str(data['text'])

    time_sent = time.time()
    data['time_sent'] = time_sent

    data['user_id'] = user_id
    data['room_name'] = room.name

    try:
        image_id = data['image_id']
    except Exception as e:
        image_id = None

    if len(message) > 4000:  # character count limit
        raise TypeError('Bad message length')

    if len(message) == 0 and not image_id:
        raise TypeError('Bad message length')

    if not room:
        raise TypeError('Invalid room')

    return data, room, user


@socketio.on('send_message')
@jwt_required(fresh=True)
def handle_send_message_event(data):
    auth_user_id = get_jwt_identity()

    try:
        data, room, user = grab_and_validate_message_data(data, auth_user_id)
    except TypeError:
        current_app.logger.info("Invalid inputs on message from {}".format(auth_user_id))
        return None

    room_member_ids = []
    room_member_objects = get_room_members(room.room_id)  # determine who should receive this message
    for db_item in room_member_objects:
        room_member_ids.append(str(db_item['_id']['user_id']))

    if auth_user_id in room_member_ids:  # if the author/sender is in the room they are trying to send to
        current_app.logger.info("{} ({}) has sent message to the room {} at {}".format(auth_user_id, user.username, room, data['time_sent']))
        apns_targets = []

        for some_user_id in room_member_ids:  # for person in room
            res = handle_message_emit(some_user_id, data)
            if not res:
                user_apn_tokens = get_apn(some_user_id)
                if user_apn_tokens and not check_mute(some_user_id, room.room_id):
                    apns_targets.extend(user_apn_tokens)
        
        # kick off threads
        current_app.logger.info("Emitting APNS and storing message".format())

        apns_thread = threading.Thread(target=handle_apns_load, args=(apns_targets, data, room.is_dm))
        db_thread = threading.Thread(target=save_message, args=(room.room_id, data['message'], auth_user_id, data['image_id']))  # to db

        apns_thread.start()
        db_thread.start()
    else:
        current_app.logger.info("{} not authorized to send to {}".format(user.ID, room.room_id))


def handle_apns_load(apns_targets, data, is_dm=False):
    bad_tokens = []
    if is_dm:
        room_type = 1
    else:
        room_type = 0
    for token in apns_targets:
        # author, body, room_id, room_title='Channel', type=0
        new_payload = notification_interface.payload_message(data['username'], data['text'], data['room'], data['room_name'], room_type)
        success = notification_interface.send_payload(new_payload, token)
        if not success:
            bad_tokens.append(token)
    for bad_token in bad_tokens:
        purge_apn(bad_token)
        


@socketio.on('send_react')
@jwt_required()
def attach_reaction(data):
    user_id = get_jwt_identity()
    user = get_user(user_id)

    target_message_id = data['message_id']
    reaction = data['reaction']
    time_sent = datetime.now()

    data['username'] = user.username
    data['user_id'] = user.ID

    current_app.logger.info('{} reacted to {} with {} at {}'.format(user_id, target_message_id, reaction, time_sent))

    add_reaction(target_message_id, user_id, reaction)

    # need to update this for appropriate room
    socketio.emit('receive_react', data)


@socketio.on('im_typing')
@jwt_required()
def is_typing(data):
    user_id = get_jwt_identity()
    try:
        room = data['room_id']
    except TypeError as e:
        current_app.logger.info('Broken typing socket event')
    data['user_id'] = user_id
    socketio.emit('is_typing', data)


@socketio.on('im_not_typing')
@jwt_required()
def not_typing(data):
    user_id = get_jwt_identity()
    try:
        username = data['room_id']
    except TypeError as e:
        current_app.logger.info('Broken typing socket event')
    data['user_id'] = user_id
    socketio.emit('not_typing', data)


# for updating all clients regarding misc server-wide activity
@socketio.on('i_changed')
@jwt_required()
def update_user(data):
    user_id = get_jwt_identity()
    data['user_id'] = user_id
    socketio.emit('user_update', data)
