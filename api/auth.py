# github.com/colingoodman
import re
from datetime import timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from pymongo.errors import DuplicateKeyError

from db import get_user_id, get_user, save_user, add_log_event

auth_blueprint = Blueprint('auth_blueprint', __name__)


def check_if_token_revoked(jwt_header, jwt_payload):
    pass


@auth_blueprint.route('/login', methods=['POST'])
@cross_origin()
def login():
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    current_app.logger.info('{} hit /login'.format(ip))
    json_input = request.get_json(force=True)

    try:
        username = json_input['username']
        password = json_input['password']
    except KeyError as e:
        return jsonify({'Error': 'Invalid request: Missing required field.'}), 400
    except TypeError as e:
        return jsonify({'Error': 'Invalid request: Must be a json/dict.'}), 400

    if len(username) == 0:
        return jsonify({'Error': 'Please provide a username.'}), 400
    if len(password) == 0:
        return jsonify({'Error': 'Please provide a password'}), 400

    if request.method == 'POST':
        try:
            user_id = get_user_id(username)
            print(user_id)
            if not user_id:
                return jsonify({'Error': 'User not found.'}), 400
            user = get_user(user_id)
        except TypeError as e:
            return jsonify({'Error': 'Bad username.'}), 400

        if user and user.check_password(password):
            access_token = create_access_token(identity=username, fresh=True)
            refresh_token = create_refresh_token(identity=username)

            current_app.logger.info('%s logged in successfully', user.username)
            add_log_event(200, username, 'Login', ip_address=ip)

            return jsonify({'Token': access_token, 'Refresh': refresh_token}), 200
        elif not user:
            return jsonify({'Error': 'User not found.'}), 400
        else:
            current_app.logger.info('%s failed to log in', username)
            return jsonify({'Error': 'Wrong password.'}), 403
    else:
        return jsonify({'Error': 'Request must be POST'}), 405

    return jsonify({'Error': ''}), 500


@auth_blueprint.route('/signup', methods=['POST'])
@cross_origin()
def create_account():
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    json_input = request.get_json(force=True)

    try:
        username = json_input['username']
        password = json_input['password']
        email = json_input['email']
        full_name = json_input['name']
        current_app.logger.info('{} trying to create a new account, {}'.format(request.remote_addr, username))
    except KeyError as e:
        return jsonify({'Error': 'Invalid request: Missing required field. {}'.format(e)}), 400
    except TypeError as e:
        return jsonify({'Error': 'Invalid request: Must be a json/dict. {}'.format(e)}), 400

    if re.match("^[A-Za-z_]*$", username):
        if len(password) < 6:
            return jsonify({'Error': 'Password must be 6+ characters.'}), 400
        try:
            user_id = save_user(username, email, password, full_name)
            current_app.logger.info('{} created a new account, {}'.format(request.remote_addr, username))

            add_log_event(200, user_id, 'Signup', ip_address=ip)
            return jsonify({'200': 'User created, {}.'.format(user_id)}), 200
        except DuplicateKeyError:
            return jsonify({'Error': 'User {} already exists.'.format(username)}), 400
    else:
        return jsonify({'Error': 'Bad username.'}), 400

    return jsonify({'Error': ''}), 500


@auth_blueprint.route("/refresh")
@jwt_required(refresh=True)
def refresh():
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity, fresh=True)

    add_log_event(200, identity, 'Refresh', ip_address=ip)
    return jsonify({'Token': access_token})


@auth_blueprint.route('/logout', methods=["DELETE"])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    # jwt_redis_blocklist.set(jti, '', ex=timedelta(hours=1))
    return jsonify({'Error': ''}), 500


@auth_blueprint.route('/whoami', methods=['GET'])
@jwt_required(fresh=True)
def who():
    username = get_jwt_identity()
    return jsonify({'user': username}), 200


@auth_blueprint.route('/', methods=['GET'])
def hello():
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    return jsonify({'Hello World': ip}), 200



