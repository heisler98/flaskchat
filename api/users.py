# github.com/colingoodman
from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from db import change_user_password, get_user, change_user_realname, get_user_id, get_all_users

users_blueprint = Blueprint('users_blueprint', __name__)


@users_blueprint.route('/users/<user_id>', methods=['GET'])
@jwt_required()
def view_user(user_id):
    username = get_jwt_identity()

    current_app.logger.info('{} viewing profile of {} (GET)'.format(username, user_id))
    user_raw = get_user(int(user_id))

    try:
        some_avatar = user_raw.avatar
    except AttributeError as e:
        some_avatar = None

    try:
        some_username = user_raw.username
    except AttributeError as e:
        return jsonify({'Error': 'Bad request; are you using the user ID?'})

    user = {
        'username': some_username,
        'email': user_raw.email,
        'phone_number': None,
        'realname': user_raw.realname,
        'avatar': some_avatar,
        'ID': user_raw.identifier
    }

    return jsonify(user)


@users_blueprint.route('/users/list', methods=['GET'])
@jwt_required()
def list_users():
    username = get_jwt_identity()
    users_raw = get_all_users()
    users = []

    for user in users_raw:
        try:
            avatar = user['avatar']
        except Exception as e:
            avatar = None
        new_user = {
            'username': user['username'],
            'email': user['email'],
            'phone_number': None,
            'realname': user['realname'],
            'avatar': avatar,
            'date_joined': user['date_joined'].timestamp(),
            'ID': user['_id']
        }
        users.append(new_user)

    return jsonify({'users': users})


@users_blueprint.route('/users/<user_id>/password', methods=['POST'])
@jwt_required(fresh=True)
def change_password(user_id):
    username = get_jwt_identity()
    json_input = request.get_json()

    if request.method == 'POST':
        current_app.logger.info('NOTE: {} changing their password'.format(username, user_id))
        new_password = json_input['new_password']
        old_password = json_input['old_password']
        try:
            user_id = get_user_id(username)['_id']
            user = get_user(user_id)
        except Exception as e:
            return jsonify({'Error': ''})

        if user and user.check_password(old_password):
            change_user_password(username, new_password)
            return jsonify({'Success': 'Password changed'})
        else:
            return jsonify({'Error': 'Incorrect password'})

    return jsonify({'Error': ''})


@users_blueprint.route('/users/<user_id>/edit', methods=['POST'])
@jwt_required(fresh=True)
def edit_user(user_id):  # NOT FINISHED YET
    username = get_jwt_identity()
    json_input = request.get_json()

    var_changes = dict(json_input).keys()

    target_user = get_user(user_id)
    if target_user.username != username:
        return jsonify({'Error': 'Not authorized'})

    if len(var_changes) == 0:
        return jsonify({'Error': 'Empty json input'})

    for key in var_changes:
        if key == 'realname':
            change_user_realname(user_id, json_input[key])

