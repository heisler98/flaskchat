# github.com/colingoodman
from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from db import change_user_password, get_user, change_user_realname, get_user_id, get_all_users, add_log_event

users_blueprint = Blueprint('users_blueprint', __name__)


@users_blueprint.route('/users/<user_id>', methods=['GET'])
@jwt_required()
def view_user(user_id):
    username = get_jwt_identity()

    current_app.logger.info('{} viewing profile of {} (GET)'.format(username, user_id))
    user_raw = get_user(int(user_id))

    if not user_raw:
        return jsonify({'Error': 'User not found.'}), 404

    return jsonify(user_raw.create_json()), 200


@users_blueprint.route('/users/list', methods=['GET'])
@jwt_required()
def list_users():
    username = get_jwt_identity()
    users_raw = get_all_users()  # returns a list of user objects
    users = []

    current_app.logger.info('{} requested a list of all users.'.format(username))

    for user_object in users_raw:
        users.append(user_object.create_json())

    return jsonify(users), 200


@users_blueprint.route('/users/me', methods=['GET'])
@jwt_required()
def get_me():
    username = get_jwt_identity()
    this_user = get_user(get_user_id(username))

    return jsonify(this_user.create_json())


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
            user_id = get_user_id(username)
            user = get_user(user_id)
        except Exception as e:  # need to be more specific
            return jsonify({'Error': ''})

        if user and user.check_password(old_password):
            change_user_password(username, new_password)
            add_log_event(200, username, 'Password', ip_address=request.remote_addr)

            return jsonify({'Success': 'Password changed'}), 200
        else:
            return jsonify({'Error': 'Incorrect password'}), 403

    return jsonify({'Error': ''}), 500


@users_blueprint.route('/users/<user_id>/edit', methods=['POST'])
@jwt_required(fresh=True)
def edit_user(user_id):  # NOT FINISHED YET
    username = get_jwt_identity()
    json_input = request.get_json()

    var_changes = dict(json_input).keys()

    target_user = get_user(user_id)
    if target_user.username != username:
        return jsonify({'Error': 'Not authorized'}), 403

    if len(var_changes) == 0:
        return jsonify({'Error': 'Empty json input'}), 400

    for key in var_changes:
        if key == 'realname':
            change_user_realname(user_id, json_input[key])

