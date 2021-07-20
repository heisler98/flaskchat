# github.com/colingoodman
import json

from bson import json_util
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from db import get_room_members, get_user, get_user_id, get_messages, is_room_member, get_room, create_dm, find_dm, \
    save_room, get_rooms_for_user, add_room_member, delete_room, is_room_admin, toggle_admin, add_room_members, \
    get_latest_bucket_number, get_room_admins, add_log_event, room_is_mute, toggle_mute
from helper_functions import parse_json
from model.room import Message
from model.user import User

rooms_blueprint = Blueprint('rooms_blueprint', __name__)


@rooms_blueprint.route('/rooms/list', methods=['GET'])
@jwt_required()
def get_rooms():
    user_id = get_jwt_identity()
    room_list_raw = get_rooms_for_user(user_id)
    room_list = []

    for item in room_list_raw:
        room_list.append(parse_json(item))

    id_list = []

    for item in room_list:
        id_list.append(item['_id']['room_id']['$oid'])

    return jsonify({'rooms': id_list}), 200


@rooms_blueprint.route('/rooms/all', methods=['GET'])
@jwt_required()
def get_all_rooms():
    user_id = get_jwt_identity()
    room_list_raw = get_rooms_for_user(user_id)

    rooms_list = []

    for room_raw in room_list_raw:
        room_parsed = parse_json(room_raw)
        room_object = get_room(str(room_parsed['_id']['room_id']['$oid']))
        this_room = room_object.create_json()
        rooms_list.append(this_room)

    return jsonify({'rooms': rooms_list})


@rooms_blueprint.route('/rooms/create', methods=['POST'])
@jwt_required(fresh=True)
def create_room():
    user_id = get_jwt_identity()
    json_input = request.get_json(force=True)

    try:
        name = json_input['name']
    except Exception as e:
        return jsonify({'Error': 'Issue parsing JSON.'}), 400

    room_id = save_room(name, user_id)
    add_room_member(room_id, name, user_id, user_id, True, True)

    return jsonify({'Success': '{}'.format(room_id)}), 200


@rooms_blueprint.route('/rooms/<room_id>', methods=['DELETE'])
@jwt_required()
def delete_some_room(room_id):
    user_id = get_jwt_identity()

    if is_room_admin(room_id, user_id):
        print('is admin')
        delete_room(room_id)
    else:
        return jsonify({'Error': 'Not authorized'}), 403

    return jsonify({'Success': '{} has been purged.'.format(room_id)})


@rooms_blueprint.route('/rooms/<room_id>/more', methods=['GET'])
@jwt_required()
def get_room_more(room_id):
    user_id = get_jwt_identity()
    room_admins = get_room_admins()

    return jsonify({
        'admins': room_admins
    })


@rooms_blueprint.route('/rooms/dm/<user_id>', methods=['GET'])
@jwt_required(fresh=True)
def view_dm(user_id):
    auth_user_id = get_jwt_identity()

    user_one = get_user(auth_user_id)
    user_two = get_user(user_id)

    if user_one.ID == user_two.ID:
        return jsonify({'Error': 'Requested DM with self.'}), 400

    try:
        target_room = find_dm(user_one, user_two)  # find_dm orders params properly to prevent duplicate DMs
        if target_room:
            room_object = get_room(target_room)
            return jsonify(room_object.create_json()), 200
        else:
            new_dm = create_dm(user_one, user_two)
            room_object = get_room(new_dm)
            return jsonify(room_object.create_json()), 200
    except BrokenPipeError as e:
        ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        add_log_event(200, auth_user_id, '{}'.format(e), ip_address=ip)
        return jsonify({'Error': 'Please try again. {}'.format(e)}), 500


@rooms_blueprint.route('/rooms/<room_id>', methods=['GET'])
@jwt_required(fresh=True)
def single_room(room_id):
    if room_id == 'create':
        return jsonify({'Error': ''}), 405

    user_id = get_jwt_identity()
    room = get_room(room_id)

    if not room:
        return jsonify({'Error': 'Room not found.'}), 404

    if not is_room_member(room_id, user_id):
        return jsonify({'Error': 'You are not a member of this room.'}), 403
    else:
        return jsonify(room.create_json())

    return jsonify({'Error': ''}), 500


@rooms_blueprint.route('/rooms/<room_id>/mute', methods=['GET', 'PUT'])
@jwt_required()
def room_mute(room_id):
    user_id = get_jwt_identity()

    if not is_room_member(room_id, user_id):
        return jsonify({'Error': 'You are not a member of this room.'}), 403

    if request.method == 'GET':
        mute_status = room_is_mute(room_id, user_id)
        return jsonify({
            'muted': mute_status
        })
    elif request.method == 'PUT':
        mute_status = toggle_mute(room_id, user_id)
        return jsonify({
            'muted': mute_status
        })


@rooms_blueprint.route('/rooms/<room_id>', methods=['POST'])
@jwt_required()
def edit_single_room(room_id):
    auth_user_id = get_jwt_identity()
    user = get_user(auth_user_id)
    room = get_room(room_id)

    json_input = request.get_json(force=True)


@rooms_blueprint.route('/rooms/<room_id>/messages', methods=['GET'])
@jwt_required(fresh=True)
def get_room_messages(room_id):
    room = get_room(room_id)
    user_id = get_jwt_identity()

    if room and is_room_member(room_id, user_id):
        bucket_number = int(get_latest_bucket_number(room_id))  # defaulted to latest bucket if none given in args
        requested_bucket_number = int(request.args.get('bucket_number', bucket_number))

        message_bson = get_messages(room_id, requested_bucket_number)
        messages = []
        users = {}
        for item in message_bson:
            try:
                user_id = str(item['sender'])
                if user_id not in users:
                    users[user_id] = get_user(user_id)
                # time_sent, text, username, user_id, avatar, image_id)
                messages.append(Message(item['time_sent'], item['text'], users[user_id].username, users[user_id].ID,
                                        users[user_id].avatar, str(item['image_id'])).create_json())
            except Exception as e:
                current_app.logger.info(e)
        return jsonify(messages)
    else:
        return jsonify({'Error': 'Room not found'}), 400


@rooms_blueprint.route('/rooms/<room_id>/admin', methods=['PUT'])
@jwt_required()
def toggle_room_admin(room_id):
    username = get_jwt_identity()
    user_id = get_user_id(username)
    toggle_admin(room_id, user_id)

    return jsonify({'Success': 'Toggled admin'})


@rooms_blueprint.route('/rooms/<room_id>/members', methods=['GET'])
@jwt_required()  # is this checking for perms?
def single_room_members(room_id):
    user_id = get_jwt_identity()
    current_app.logger.info('{} requested members for {}'.format(user_id, room_id))

    members_raw = get_room_members(room_id)
    members = []

    if not is_room_member(room_id, user_id):
        return jsonify({'Error': 'You are not a member of the requested room.'}), 403

    for member in members_raw:
        try:
            # this is really messy, can this be improved?
            this_user = get_user(str(member['_id']['user_id']))
        except KeyError as e:
            continue
        except TypeError as e:
            return jsonify({'Error': e}), 400
        if not this_user:
            continue

        new_member = get_user(this_user.ID)
        members.append(new_member.create_json())

    return jsonify(members), 200


@rooms_blueprint.route('/rooms/<room_id>/members', methods=['POST'])
@jwt_required()
def room_add_members(room_id):
    user_id = get_jwt_identity()
    json_input = request.get_json(force=True)

    current_app.logger.info('{} wants to add member(s) to {}'.format(user_id, room_id))

    try:
        new_members = json_input['add_members']
    except Exception as e:
        return jsonify({'Error': 'Bad input'}), 400

    try:
        target_room = get_room(room_id)
    except Exception as e:
        return jsonify({'Error': 'Room not found'}), 400

    # room_id, room_name, user_id, added_by, is_admin=False, is_owner=False

    try:
        if len(new_members) == 1:
            add_room_member(room_id, target_room.name, new_members[0], user_id)
            current_app.logger.info('Added a user to {}'.format(room_id))
        elif len(new_members) > 1:
            add_room_members(room_id, target_room.name, new_members, user_id)
            current_app.logger.info('Added {} users to {}'.format(len(new_members), room_id))
        else:
            return jsonify({'Error': 'Bad input'}), 400
    except Exception as e:
        return jsonify({'Error': 'Failed to add user. {}'.format(e)}), 500

    return jsonify({'Success': 'User(s) added'}), 200


@rooms_blueprint.route('/rooms/search', methods=['POST'])
@jwt_required()
def search_messages():  # !! this is a slow (brute-force) implementation of search
    json_input = request.get_json(force=True)
    key_words = list(json_input['words'])
    rooms = list(json_input['room_ids'])

    output = []

    for room in rooms:
        bucket_max = get_latest_bucket_number(room)
        for bucket in range(1, bucket_max):
            messages = get_messages(room, bucket)
            for message in messages:
                for word in key_words:
                    if word in message:
                        output.append(message)

    return jsonify({
        'results': output
    })

