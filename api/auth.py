# github.com/colingoodman
import re
from datetime import timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from pymongo.errors import DuplicateKeyError

from db import get_user_id, get_user, save_user

auth_blueprint = Blueprint('auth_blueprint', __name__)


def check_if_token_revoked(jwt_header, jwt_payload):
    pass


@auth_blueprint.route('/login', methods=['POST'])
@cross_origin()
def login():
    current_app.logger.info('{} hit /login'.format(request.remote_addr))
    json_input = request.get_json(force=True)

    try:
        username = json_input['username']
        password = json_input['password']
    except KeyError as e:
        return jsonify({'Error': 'Invalid request: Missing required field.'})
    except TypeError as e:
        return jsonify({'Error': 'Invalid request: Must be a json/dict.'})

    if len(username) == 0:
        return jsonify({'Error': 'Please provide a username.'})
    if len(password) == 0:
        return jsonify({'Error': 'Please provide a password'})

    if request.method == 'POST':
        try:
            user_id = get_user_id(username)
            if not user_id:
                return jsonify({'Error': 'User not found.'})
            user = get_user(user_id)
        except TypeError as e:
            return jsonify({'Error': 'Bad username.'})

        if user and user.check_password(password):
            access_token = create_access_token(identity=username, fresh=True)
            refresh_token = create_refresh_token(identity=username)
            current_app.logger.info('%s logged in successfully', user.username)
            return jsonify({'Token': access_token, 'Refresh': refresh_token})
        elif not user:
            return jsonify({'Error': 'User not found.'})
        else:
            current_app.logger.info('%s failed to log in', username)
            return jsonify({'Error': 'Wrong password.'})
    else:
        return jsonify({'Error': 'Request must be POST'})

    return jsonify({'Error': ''})


@auth_blueprint.route('/signup', methods=['POST'])
@cross_origin()
def create_account():
    json_input = request.get_json()
    user_object = json_input['child']

    try:
        username = user_object['username']
        password = user_object['password']
        email = user_object['email']
        full_name = user_object['name']
        current_app.logger.info('{} trying to create a new account, {}'.format(request.remote_addr, username))
    except KeyError as e:
        return jsonify({'Error': 'Invalid request: Missing required field.'})
    except TypeError as e:
        return jsonify({'Error': 'Invalid request: Must be a json/dict.'})

    if re.match("^[A-Za-z_]*$", username):
        if len(password) < 6:
            return jsonify({'Error': 'Password must be 6+ characters.'})
        try:
            save_user(username, email, password, full_name)
            current_app.logger.info('{} created a new account, {}'.format(request.remote_addr, username))
            return jsonify({'200': 'User created.'})
        except DuplicateKeyError:
            return jsonify({'Error': 'User already exists.'})

    return jsonify({'Error': ''})


@auth_blueprint.route("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity, fresh=True)

    return jsonify({'Token': access_token})


@auth_blueprint.route('/logout', methods=["DELETE"])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    # jwt_redis_blocklist.set(jti, '', ex=timedelta(hours=1))
    return jsonify({'Error': ''})


@auth_blueprint.route('/whoami', methods=['GET'])
@jwt_required(fresh=True)
def who():
    username = get_jwt_identity()
    return jsonify({'user': username})


@auth_blueprint.route('/', methods=['GET'])
def hello():
    return jsonify({'Hello': 'World'})



