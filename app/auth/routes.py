# github.com/colingoodman
import re
from datetime import timedelta

from app.auth import auth_blueprint

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from pymongo.errors import DuplicateKeyError

from db import get_user_id, get_user, save_user, add_log_event, store_apn


def check_if_token_revoked(jwt_header, jwt_payload):
    pass


def check_valid_email(some_input):
    regex_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not re.match(regex_email, some_input):
        return False
    else:
        return True


@auth_blueprint.route('/apn', methods=['POST'])
@jwt_required()
def register_apn_token():
    user_id = get_jwt_identity()
    current_app.logger.info('APN ENDPOINT')
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    json_input = request.get_json(force=True)

    apn_token = json_input['token']
    res = store_apn(user_id, apn_token)
    current_app.logger.info(res)

    if res:
        return jsonify({'Success': ''}), 200
    else:
        return jsonify({'Error': ''}), 500


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

    if len(username) == 0 or username == '':
        return jsonify({'Error': 'Please provide a username.'}), 400
    if len(password) == 0:
        return jsonify({'Error': 'Please provide a password'}), 400

    if not re.match("^[A-Za-z_]*$", username):
        return jsonify({'Error': 'Invalid username.'}), 400

    if request.method == 'POST':
        try:
            user_id = get_user_id(username)
            if not user_id:
                return jsonify({'Error': 'User not found.'}), 400
            user = get_user(user_id)
        except TypeError as e:
            return jsonify({'Error': 'Bad username.'}), 400

        if user and user.check_password(password):
            access_token = create_access_token(identity=user_id, fresh=True)
            refresh_token = create_refresh_token(identity=user_id)

            current_app.logger.info('Login')
            add_log_event(200, username, 'Login', ip_address=ip)

            return jsonify({'Token': access_token, 'Refresh': refresh_token}), 200
        elif not user:
            return jsonify({'Error': 'Invalid username or password.'}), 400
        else:
            current_app.logger.info('%s failed to log in', username)  # wrong password
            return jsonify({'Error': 'Invalid username or password.'}), 403
    else:
        return jsonify({'Error': 'Request must be POST'}), 405


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
        if len(username) == 0 or len(password) == 0 or len(email) == 0 or len(full_name) == 0:
            raise KeyError('Empty field.')
    except KeyError as e:
        return jsonify({'Error': 'Invalid request: Missing required field. {}'.format(e)}), 400
    except TypeError as e:
        return jsonify({'Error': 'Invalid request: Must be a json/dict. {}'.format(e)}), 400

    regex_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not check_valid_email(email):
        return jsonify({'Error': 'Invalid email address.'}), 400
    if not re.match("^[A-Za-z ]*$", full_name):
        return jsonify({'Error': 'Invalid full name.'}), 400

    if re.match("^[A-Za-z_]*$", username) and len(username) < 26:
        if len(password) < 6:
            return jsonify({'Error': 'Password must be 6+ characters.'}), 400
        try:
            user_id = save_user(username, email, password, full_name)
            current_app.logger.info('{} created a new account, {}'.format(request.remote_addr, username))

            add_log_event(200, user_id, 'Signup', ip_address=ip)
            return jsonify({'Success': 'User created.'.format(user_id)}), 200
        except DuplicateKeyError:
            return jsonify({'Error': 'Username or email is already in use.'}), 400
    else:
        return jsonify({'Error': 'Bad username.'}), 400

    return jsonify({'Error': ''}), 500


@auth_blueprint.route("/refresh")
@cross_origin()
@jwt_required(refresh=True)
def refresh():
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id, fresh=True)

    add_log_event(200, user_id, 'Refresh', ip_address=ip)
    return jsonify({'Token': access_token})


@auth_blueprint.route('/logout', methods=["DELETE"])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    jwt_redis_blocklist.set(jti, '', ex=timedelta(hours=1))
    return jsonify({'Success': 'You have logged out.'}), 200


@auth_blueprint.route('/whoami', methods=['GET'])
@jwt_required(fresh=True)
def who():
    user_id = get_jwt_identity()
    return jsonify({'user': user_id}), 200


@auth_blueprint.route('/', methods=['GET'])
def hello():
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    return jsonify({'Hello World': ip}), 200
