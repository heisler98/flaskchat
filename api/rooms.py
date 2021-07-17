# github.com/colingoodman
import json

from bson import json_util
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from db import get_room_members, get_user, get_user_id, get_messages, is_room_member, get_room, create_dm, find_dm, \
    save_room, get_rooms_for_user, add_room_member, delete_room, is_room_admin, toggle_admin, add_room_members, \
    get_latest_bucket_number, get_room_admins
from helper_functions import parse_json

rooms_blueprint = Blueprint('rooms_blueprint', __name__)


class Message:
    def __init__(self, time_sent, text, username, user_id, avatar, image_id):
        self.time_sent = time_sent
        self.text = text
        self.username = username
        self.user_id = user_id
        self.avatar = avatar
        self.image_id = image_id

    def create_json(self):
        return {
            'time_sent': self.time_sent,
            'text': self.text,
            'username': self.username,
            'user_id': self.user_id,
            'avatar_id': self.avatar,
            'image_id': self.image_id
        }


# returns a json object of a room to be returned via the API
def return_room_object(room_id):
    this_room = get_room(room_id)
    bucket_number = get_latest_bucket_number(room_id)

    if not bucket_number:
        bucket_number = 0

    if not this_room:
        raise Exception

    # grab messages for this room
    message_bson = get_messages(room_id, bucket_number)
    messages = []
    users = {}
    if message_bson:
        for item in message_bson:
            try:
                user_id = str(item['sender'])
                if user_id not in users:
                    users[user_id] = get_user(user_id)
                # self, time_sent, text, username, user_id, avatar, image_id
                messages.append(Message(item['time_sent'], item['text'], users[user_id].username, users[user_id].ID,
                                        users[user_id].avatar, str(item['image_id'])).create_json())
            except Exception as e:
                current_app.logger.info(e)

    return {
        'name': this_room['name'],
        'bucket_number': bucket_number,
        'is_dm': this_room['is_dm'],
        'messages': messages,
        'created_by': str(this_room['created_by']),
        'room_id': str(this_room['_id'])
    }


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
        this_room = return_room_object(room_parsed['_id']['room_id']['$oid'])
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

    target_room = find_dm(user_one, user_two)  # find_dm orders params properly to prevent duplicate DMs
    if target_room:
        return jsonify(return_room_object(target_room)), 200
    else:
        new_dm = create_dm(user_one, user_two)
        return jsonify(return_room_object(new_dm)), 200


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
        return return_room_object(room_id)

    return jsonify({'Error': ''}), 500


@rooms_blueprint.route('/rooms/<room_id>/messages', methods=['GET'])
@jwt_required(fresh=True)
def get_room_messages(room_id):
    room = get_room(room_id)
    user_id = get_jwt_identity()

    if room and is_room_member(room_id, user_id):
        bucket = int(request.args.get('bucket_number', 0))

        message_bson = get_messages(room_id, bucket)
        messages = []

        for item in message_bson:
            try:
                this_user = get_user(str(item['sender']))
            except Exception as e:
                current_app.logger.info(e)
                continue

            # self, time_sent, text, username, user_id, avatar, image_id
            messages.append(Message(item['time_sent'], item['text'], this_user.username, str(this_user.ID),
                                    str(this_user.avatar), str(item['image_id'])).create_json())

        return jsonify({'messages': messages})
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

    for member in members_raw:
        # print(member)
        try:
            # this is really messy, can this be improved?
            this_user = get_user(str(member['_id']['user_id']))
        except KeyError as e:
            continue
        except TypeError as e:
            return jsonify({'Error': e}), 400
        if not this_user:
            current_app.logger.info('Encountered unknown user {} in {}'.format(this_user, room_id))
            continue

        try:
            avatar = this_user.avatar
        except Exception as e:
            avatar = None

        new_member = {
            'username': this_user.username,
            'ID': this_user.ID,
            'added_at': str(member['added_at']),  # .timestamp(),
            'added_by': str(member['added_by']),
            'is_room_admin': member['is_admin'],
            'avatar': avatar
        }
        members.append(parse_json(new_member))

    return jsonify({'members': members}), 200


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
            add_room_member(room_id, target_room['name'], new_members[0], user_id)
            current_app.logger.info('Added a user to {}'.format(room_id))
        elif len(new_members) > 1:
            add_room_members(room_id, target_room['name'], new_members, user_id)
            current_app.logger.info('Added {} users to {}'.format(len(new_members), room_id))
        else:
            return jsonify({'Error': 'Bad input'}), 400
    except Exception as e:
        return jsonify({'Error': 'Failed to add user. {}'.format(e)}), 500

    return jsonify({'Success': 'User(s) added'}), 200
