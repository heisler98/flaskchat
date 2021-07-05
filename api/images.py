# github.com/colingoodman
import os
import sys

from flask import Blueprint, current_app, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from db import save_image, change_user_avatar, get_user, locate_image, is_room_member
from helper_functions import allowed_file

images_blueprint = Blueprint('images_blueprint', __name__)


class EmptyNameError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class IllegalTypeError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


# For upload security, saving to disk, and recording in DB
def upload_image(file, user_id, room_id, is_avatar=False):
    os.chdir(os.path.dirname(sys.argv[0]))
    current_app.logger.info('Attempting to upload a file from {}'.format(user_id))
    current_app.logger.info('working dir {}'.format(os.getcwd()))
    filename = secure_filename(file.filename)

    if not file:
        raise TypeError

    if filename == '':
        current_app.logger.info('Bad file name')
        raise EmptyNameError('Empty file name.')

    if not allowed_file(filename):
        current_app.logger.info('Bad file type')
        raise IllegalTypeError('Invalid file type.')

    try:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.seek(0)  # save fails w/o
        file.save(filepath)  # store image locally on disk
    except Exception as e:
        current_app.logger.info(e)

    try:
        image_id = save_image(user_id, room_id, filepath, is_avatar)
    except Exception as e:
        current_app.logger.info(e)
        return None

    return image_id


@images_blueprint.route('/uploads/create', methods=['POST'])
@jwt_required(fresh=True)
def post_image():
    username = get_jwt_identity()
    json_input = request.get_json()
    current_app.logger.info("{} attempted to upload a file".format(username))

    if request.method == 'POST':
        room_id = json_input['room_id']
        file = request.files['file']

        try:
            image_id = upload_image(file, username, room_id)
        except Exception as e:
            jsonify({'Error': 'Failed to upload, {}'.format(e)})

        return jsonify({'image_id': image_id}), 200


@images_blueprint.route('/uploads/<upload_id>', methods=['GET'])
@jwt_required()
def get_image(upload_id):
    username = get_jwt_identity()
    target_image = locate_image(upload_id)
    current_app.logger.info("{} attempted to view file {}".format(username, upload_id))

    if target_image:
        image_room = target_image['room_id']
        if not is_room_member(image_room, username) and not target_image['avatar']:  # avatars can be accessed anywhere
            return jsonify({'Error': 'Not authorized'}), 403

        file_path = target_image['location']
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            return jsonify({'File not found': upload_id})

    return jsonify({'File not found': upload_id}), 400


@images_blueprint.route('/avatar/<user_id>', methods=['GET'])
@jwt_required()
def get_avatar(user_id):
    target_user = get_user(user_id)

    if not target_user:
        return jsonify({'Error': 'User not found'}), 400

    if request.method == 'GET':
        target_image_id = target_user.avatar
        if not target_image_id:
            return jsonify({'Error': 'No associated avatar with this user'})
        target_image = locate_image(image_id=target_image_id)
        if not target_image:
            return jsonify({'File not found': str(user_id + ' avatar')}), 400
        image_location = target_image['location']

        if os.path.exists(image_location):
            # abs_path = os.path.abspath(os.path.join('..', image_location))
            abs_path = os.path.join('..', image_location)
            return send_file(abs_path)
        else:
            return jsonify({'File not found': image_location}), 400


@images_blueprint.route('/avatar/<user_id>/create', methods=['POST'])
@jwt_required(fresh=True)
def new_avatar(user_id):
    os.chdir(os.path.dirname(sys.argv[0]))
    username = get_jwt_identity()
    target_user = get_user(user_id)

    if not target_user:
        return jsonify({'Error': 'User not found'}), 400

    if target_user.username != username:
        current_app.logger.info('!!! {} tried to change another users avatar: {}'.format(username, target_user.username))
        return jsonify({'Error': 'Not authorized'}), 403

    if request.method == 'POST':
        current_app.logger.info('Shit! Holy fuck!!')
        file = request.files['file']
        image_id = ''

        try:
            image_id = upload_image(file, user_id, None, True)
            #change_user_avatar(user_id, image_id)
        except Exception as e:
            current_app.logger.info('Broke {}'.format(e))
            return jsonify({'Error': 'Failed to upload, {}'.format(e)})

        if image_id == '':
            return jsonify({'Error': 'No idea'}), 500

        change_user_avatar(user_id, image_id)
        current_app.logger.info('{} {} changed their avatar'.format(user_id, username))
        return jsonify({'Success': 'Avatar changed, GET user for ID'}), 200


@images_blueprint.route('/avatar/<user_id>/switch', methods=['POST'])
@jwt_required()
def switch_avatar(user_id):
    os.chdir(os.path.dirname(sys.argv[0]))
    username = get_jwt_identity()
    target_user = get_user(user_id)
    json_input = request.get_json()
    target_image = json_input['image_id']

    if not target_user:
        return jsonify({'Error': 'User not found'}), 400

    if target_user.username != username:
        current_app.logger.info('!!! {} tried to change another users avatar: {}'.format(username, target_user.username))
        return jsonify({'Error': 'Not authorized'}), 403

    if len(target_image) == 0:
        return jsonify({'Error': 'Empty image_id'}), 400

    if not locate_image(target_image):
        return jsonify({'Error': 'Image not found.'}), 400

    if request.method == 'POST':
        change_user_avatar(target_user.username, target_image)
        current_app.logger.info('{} switched their avatar with an existing image, {}'.format(username, image_id))
        return jsonify({'Success': 'Avatar changed.'}), 200



@images_blueprint.route('/avatar/<user_id>/previous', methods=['GET'])
@jwt_required()
def previous_avatars_list(user_id):
    os.chdir(os.path.dirname(sys.argv[0]))
    username = get_jwt_identity()
    target_user = get_user(user_id)

    if not target_user:
        return jsonify({'Error': 'User not found'}), 400

    if request.method == 'GET':
        pass

