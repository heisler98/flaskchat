# github.com/colingoodman
from datetime import datetime

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import join_room, SocketIO, join_room, rooms
from .app import socketio

from db import save_message, get_room_members, get_user_id, update_checkout, get_user

sockets_blueprint = Blueprint('sockets_blueprint', __name__)
global connected_sockets
connected_sockets = {}


# this event is automatic, triggered by a new socket connection
@socketio.on('connect')
@jwt_required()
def client_connect():
    user_identity = get_jwt_identity()  # user_identity is username, NOT id

    join_room('server')
    current_socket_id = request.sid
    current_app.logger.info('A socket for {} with ID {} has been created...'.format(user_identity, current_socket_id))

    if user_identity in connected_sockets:
        if connected_sockets[user_identity] is None:
            this_user = connected_sockets[user_identity]
            connected_sockets[user_identity] = this_user.append(current_socket_id)
        else:  # None in the dict, need to debug
            this_user = [current_socket_id]
            connected_sockets[user_identity] = this_user
            # current_app.logger.info('{} added {}'.format(this_user, current_socket_id))
    else:
        this_user = [current_socket_id]
        connected_sockets[user_identity] = this_user

    current_app.logger.info(
        '{} now has the following sockets open: {}'.format(user_identity, connected_sockets[user_identity]))


# this event is automatic, triggered by a broken socket connection
@socketio.on('disconnect')
def client_disconnect():
    disconnected_id = request.sid
    current_app.logger.info('A socket with ID {} disconnected...'.format(disconnected_id))

    for key in connected_sockets:
        user_sockets = connected_sockets[key]
        if disconnected_id in user_sockets:
            user_sockets.remove(disconnected_id)
            current_app.logger.info('{} belonged to {}. They now have the following sockets open: {}'.format(disconnected_id, key, connected_sockets[key]))

            if len(user_sockets) == 0:
                update_last_seen(key)


# update user object in DB to note when they were last online
def update_last_seen(username):
    user_id = get_user_id(username)
    update_checkout(user_id)


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
    username = data['username']
    current_app.logger.info(data)
    room = data['room']  # client must pass room id here
    message = data['text']
    is_image = data['include_image']
    try:
        image_id = data['image_id']
    except Exception as e:
        image_id = None
    time_sent = datetime.now()  # .strftime('%b %d, %H:%M')
    data['time_sent'] = str(time_sent)
    data['user_id'] = str(get_user_id(username))

    if username not in connected_sockets:
        current_app.logger.info('!!: {} tried to send a message without being connected to a room.'.format(username))

    user_id = get_user_id(username)

    room_member_ids = []
    room_member_objects = get_room_members(room)  # determine who should receive this message
    for db_item in room_member_objects:
        room_member_ids.append(str(db_item['_id']['user_id']))
        current_app.logger.info(room_member_ids)

    if user_id in room_member_ids:  # if the author/sender is in the room they are trying to send to
        current_app.logger.info("{} has sent message to the room {} at {}".format(user_id, room, time_sent))

        for member in room_member_ids:
            member_name = get_user(member).username
            # current_app.logger.info("emit to {}".format(member))
            if member_name in connected_sockets:
                target_socket_ids = connected_sockets[member_name]
                try:
                    for socket in target_socket_ids:
                        socketio.emit('receive_message', data, room=socket)  # emit to specific user
                        current_app.logger.info('Sent to {}'.format(socket))
                except TypeError as e:
                    current_app.logger.info('Failed to emit message to {}, connected on {}. They may not have an open '
                                            'connection. {}'.format(member_name, connected_sockets[member_name], e))
            else:
                # current_app.logger.info('{} does not have an open socket connection.'.format(member_name))
                pass

        save_message(room, message, user_id, is_image, image_id)  # to db
    else:
        current_app.logger.info("{} not authorized to send to {}".format(username, room))


@socketio.on('send_react')
@jwt_required()
def attach_reaction():
    user_id = data['user_id']
    target_message_id = data['message_id']
    room_id = data['room']  # client must pass room id here
    reaction = data['reaction']
    time_sent = datetime.now()

    current_app.logger.info('{} reacted to {} with {} at {}'.format(user_id, target_message_id, reaction, time_sent))

    add_reaction(target_message_id, user_id, reaction)

    socketio.emit('receive_react', data, room=socket)


@socketio.on('im_typing')
@jwt_required()
def is_typing(data):
    room = data['room_id']
    socketio.emit('is_typing', data)


@socketio.on('im_not_typing')
@jwt_required()
def not_typing(data):
    username = data['room_id']
    socketio.emit('not_typing', data)

