# github.com/colingoodman
import json

from bson import json_util
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from db import get_room_members, get_user, get_user_id, get_messages, is_room_member, get_room, create_dm, find_dm, \
    save_room, get_rooms_for_user
from helper_functions import parse_json

rooms_blueprint = Blueprint('rooms_blueprint', __name__)


# returns a json object of a room to be returned via the API
def return_room_object(room_id):
    this_room = get_room(room_id)

    if not this_room:
        raise Exception

    # grab messages for this room
    message_bson = get_messages(room_id)
    messages = []
    for item in message_bson:
        try:
            user_id = get_user_id(item['sender'])
        except Exception as e:
            continue
        messages.append({
            'time_sent': item['time_sent'],
            'text': item['text'],
            'username': item['sender'],
            'user_id': str(user_id)
        })

    # grab this room attributes
    room_name = this_room['name']
    is_dm = this_room['is_dm']
    created_by = this_room['created_by']
    room_id = str(this_room['_id'])

    return {
        'name': room_name,
        'is_dm': is_dm,
        'messages': messages,
        'created_by': created_by,
        'room_id': room_id
    }


@rooms_blueprint.route('/rooms/list', methods=['GET'])
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

    return jsonify({'rooms': id_list}), 200


@rooms_blueprint.route('/rooms/all', methods=['GET'])
@jwt_required()
def get_all_rooms():
    username = get_jwt_identity()
    room_list_raw = get_rooms_for_user(username)

    rooms_list = []

    for room_raw in room_list_raw:
        room_parsed = parse_json(room_raw)
        this_room = return_room_object(room_parsed['_id']['room_id']['$oid'])
        rooms_list.append(this_room)

    return jsonify({'rooms': rooms_list})


@rooms_blueprint.route('/rooms/create', methods=['POST'])
@jwt_required(fresh=True)
def create_room():
    username = get_jwt_identity()
    json_input = request.get_json(force=True)

    try:
        name = json_input['name']
    except Exception as e:
        return jsonify({'Error': 'Issue parsing JSON.'}), 400

    room_id = save_room(name, username)
    return jsonify({'Success': '{}'.format(room_id)}), 200


@rooms_blueprint.route('/rooms/dm/<user_id>', methods=['GET'])
@jwt_required(fresh=True)
def view_dm(user_id):
    username = get_jwt_identity()

    user_one = get_user(get_user_id(username))
    user_two = get_user(user_id)

    target_room = find_dm(user_one, user_two)
    if target_room:
        return jsonify({'room_id': target_room}), 200
    else:
        new_dm = create_dm(user_one, user_two)
        return jsonify({'room_id': new_dm}), 200


@rooms_blueprint.route('/rooms/<room_id>', methods=['GET'])
@jwt_required(fresh=True)
def single_room(room_id):
    # json_input = request.get_json()
    username = get_jwt_identity()
    room = get_room(room_id)

    if not room:
        return jsonify({'Error': 'Room not found.'}), 404

    if not is_room_member(room_id, username):
        return jsonify({'Error': 'You are not a member of this room.'}), 403
    else:
        return return_room_object(room_id)

    return jsonify({'Error': ''}), 500


@rooms_blueprint.route('/rooms/<room_id>/messages', methods=['GET'])
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
                id = get_user_id(item['sender'])
            except Exception as e:
                continue
            messages.append({
                'time_sent': item['time_sent'],
                'text': item['text'],
                'username': item['sender'],
                'user_id': str(id)
            })

        return jsonify({'messages': messages})
    else:
        return jsonify({'Error': 'Room not found'}), 400

    return jsonify({'Error': ''}), 500


@rooms_blueprint.route('/rooms/<room_id>/members', methods=['GET'])
@jwt_required()
def single_room_members(room_id):
    username = get_jwt_identity()

    current_app.logger.info('{} requested members for {}'.format(username, room_id))

    members_raw = get_room_members(room_id)
    members = []

    for member in members_raw:
        try:
            this_user = get_user(get_user_id(member['_id']['username']))
        except KeyError as e:
            continue
        except TypeError as e:
            return jsonify({'Error': e})
        if not this_user:
            current_app.logger.info('Encountered unknown user {} in {}'.format(member['_id']['username'], room_id))
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

    return jsonify({'members': members}), 200
