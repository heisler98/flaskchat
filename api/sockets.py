# github.com/colingoodman
from datetime import datetime

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import join_room, SocketIO, join_room, rooms
from .app import socketio

from db import save_message, get_room_members

sockets_blueprint = Blueprint('sockets_blueprint', __name__)
connected_sockets = {}


@socketio.on('new_session')
@jwt_required()
def on_connect(data):
    user_identity = get_jwt_identity()  # user_identity is username, NOT id

    join_room('server')
    current_socket_id = request.sid

    if user_identity in connected_sockets:
        if connected_sockets[user_identity]:
            this_user = connected_sockets[user_identity]
            connected_sockets[user_identity] = this_user.append(current_socket_id)
        else:  # None in the dict, need to debug
            this_user = [current_socket_id]
            connected_sockets[user_identity] = this_user
    else:
        this_user = [current_socket_id]
        connected_sockets[user_identity] = this_user

    current_app.logger.info("{} has connected, {}".format(user_identity, current_socket_id))


@socketio.on('disconnect')
def client_disconnect():
    disconnected_id = request.namespace.socket.sessid
    current_app.logger.info('{} disconnected, searching for associated user...'.format(disconnected_id))

    for key in connected_sockets:
        user_sockets = connected_sockets[key]
        if disconnected_id in user_sockets:
            current_app.logger.info('{} belonged to {}, removing now.'.format(disconnected_id, key))
            user_sockets.remove(disconnected_id)


@socketio.on('close_session')  # to be replaced with broken connection handling
@jwt_required()
def on_disconnect(data):
    user_identity = get_jwt_identity()  # user_identity is username, NOT id
    current_socket_ids = connected_sockets[user_identity]

    socket_id_close = data['socket_id']  # client must pass their socket id
    new_socket_ids_list = current_socket_ids.pop(socket_id_close)

    if len(new_socket_ids_list) == 0:
        removing_entry = connected_sockets.pop(user_identity, None)
        if not removing_entry:
            raise Exception
    else:
        connected_sockets[user_identity] = new_socket_ids_list

    current_app.logger.info("{} is disconnecting, {}".format(user_identity, socket_id_close))


@socketio.on('send_message')
@jwt_required(fresh=True)
def handle_send_message_event(data):
    current_app.logger.info('Connected sockets: {}'.format(connected_sockets))

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

    room_member_usernames = []
    room_member_objects = get_room_members(room)  # determine who should receive this message
    for db_item in room_member_objects:
        room_member_usernames.append(db_item['_id']['username'])

    if username in room_member_usernames:  # if the author/sender is in the room they are trying to send to
        current_app.logger.info("{} has sent message to the room {} at {}".format(username, room, time_sent))

        for member in room_member_usernames:
            current_app.logger.info("emit to {}, members {}".format(room, room_member_usernames))
            if member in connected_sockets:
                target_socket_ids = connected_sockets[member]
                current_app.logger.info("emit message to {} in {} at {}".format(username, room, time_sent))
                try:
                    for socket in target_socket_ids:
                        socketio.emit('receive_message', data, room=socket)  # emit to specific user
                except TypeError as e:
                    current_app.logger.info('Failed to emit message to {}, connected on {}'.format(member, connected_sockets[member]))

        save_message(room, message, username, is_image, image_id)  # to db
    else:
        current_app.logger.info("{} not authorized to send to {}".format(username, room))


@socketio.on('im_typing')
@jwt_required()
def is_typing(data):
    username = data['username']
    room = data['room']
    socketio.emit('is_typing', data)


@socketio.on('im_not_typing')
@jwt_required()
def not_typing(data):
    username = data['username']
    socketio.emit('not_typing', data)

