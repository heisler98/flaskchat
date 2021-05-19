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

    connected_sockets[user_identity] = current_socket_id
    current_app.logger.info("{} has connected, {}".format(user_identity, current_socket_id))


@socketio.on('close_session')
@jwt_required()
def on_disconnect(data):
    user_identity = get_jwt_identity()  # user_identity is username, NOT id
    current_socket_id = connected_sockets[user_identity]
    current_app.logger.info("{} is disconnecting, {}".format(user_identity, current_socket_id))

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

    current_app.logger.info("{} has sent message to the room {} at {}".format(username, room, time_sent))

    save_message(room, message, username, is_image, image_id)  # to db

    room_member_objects = get_room_members(room)  # determine who should receive this message
    room_member_usernames = []

    for db_item in room_member_objects:
        room_member_usernames.append(db_item['_id']['username'])

    if username in room_member_usernames:  # if the author/sender is in the room they are trying to send to
        for member in room_member_usernames:
            if member in connected_sockets:
                target_socket_id = connected_sockets[member]
                current_app.logger.info("emit message to {} in {} at {}".format(username, room, time_sent))
                socketio.emit('receive_message', data, room=target_socket_id)  # emit to specific user

