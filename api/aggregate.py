import json

from bson import json_util
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from db import get_room_members, get_user, get_user_id, get_all_users, get_rooms_for_user, get_room
from model.room import Room, Message
from model.user import User
from helper_functions import parse_json

aggregate_blueprint = Blueprint('aggregate_blueprint', __name__)

@aggregate_blueprint.route('/aggregate', methods=['GET'])
@jwt_required()
def get_aggregate(): # collects and returns all end-user related objects 
    # get the ingredients
    user_id = get_jwt_identity()

    # collect data
    rooms_retval = get_rooms(user_id)
    users_retval = get_users()
    me_retval = get_me(user_id)

    # return data
    retval = { 
        'rooms': rooms_retval,
        'users': users_retval,
        'me': me_retval
    }
    return jsonify(retval), 200


def get_me(user_id):
    user = get_user(user_id)
    return jsonify(user.create_json())

# logged-in user will NOT be returned first 
def get_users():
    users_raw = get_all_users()
    users = list(map(lambda u: u.create_json(), users_raw))
    return jsonify(users)


def get_rooms(user_id):
    room_list_raw = get_rooms_for_user(user_id)
    room_list = []
    user = get_user(user_id)

    for item in room_list_raw:
        # parse the room
        room_parsed = parse_json(item)
        room_id = str(room_parsed['_id']['room_id']['$oid'])
        
        # get room members
        members_raw = get_room_members(room_id)
        members = list(map(lambda m: get_user(str(m['_id']['user_id'])).create_json(), members_raw))
        # ignoring check for is_room_member, some bug for me to complain about later

        # get room
        room_object = get_room(room_id)
        this_room = return_enumerated_room(room_object, user.username, user_id, members)
        room_list.append(this_room)

    return jsonify(room_list) # returns an array of rooms


def return_enumerated_room(room, username, user_id, members):
    new_name = room.name
    if room.is_dm:
        if user_id in room.name:  # new nomenclature: ID concatentation
            other_id = room.name.replace(user_id, '')
            if not other_id: # DM with self – name should be self's username
                new_name = username
            else: # lookup the name of the other user in the DM
                other_user = get_user(other_id)
                new_name = other_user.real_name
        elif username in room.name:  # old nomenclature: name concatenation
            other_username = room.name.replace(username, '')
            other_user_id = get_user_id(other_username)
            other_user = get_user(other_user_id)
            new_name = other_user.real_name
        else:  # unknown state (perhaps nomenclature changed once more)
            new_name = room.name
    return room.create_aggregate_json(new_name, members)