# github.com/colingoodman
import os

from flask import Blueprint, current_app, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from db import save_image, change_user_avatar, get_user, locate_image, is_room_member
from helper_functions import allowed_file

images_blueprint = Blueprint('images_blueprint', __name__)


@images_blueprint.route('/uploads/create', methods=['POST'])
@jwt_required(fresh=True)
def upload_image():
    username = get_jwt_identity()
    json_input = request.get_json()
    current_app.logger.info("{} attempted to upload a file".format(username))

    if request.method == 'POST':
        room_id = json_input['room_id']
        file = request.files['file']

        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        image_id = save_image(username, room_id, filepath)

        return jsonify({'image_id': image_id})


@images_blueprint.route('/uploads/<upload_id>', methods=['GET'])
@jwt_required()
def get_image(upload_id):
    username = get_jwt_identity()
    target_image = locate_image(upload_id)
    current_app.logger.info("{} attempted to view file {}".format(username, upload_id))

    if target_image:
        image_room = target_image['room_id']
        if not is_room_member(image_room, username) and not target_image['avatar']:  # avatars can be accessed anywhere
            return jsonify({'Error': 'Not authorized'})

        file_path = target_image['location']
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            return jsonify({'File not found': upload_id})
    return jsonify({'File not found': upload_id})


@images_blueprint.route('/avatar/<user_id>', methods=['GET'])
@jwt_required()
def get_avatar(user_id):
    target_user = get_user(user_id)

    if not target_user:
        return jsonify({'Error': 'User not found'})

    if request.method == 'GET':
        target_image_id = target_user.avatar
        if not target_image_id:
            return jsonify({'Error': 'No associated avatar with this user'})
        image_location = locate_image(upload_id=target_image_id)['location']

        if os.path.exists(image_location):
            return send_file(image_location)
        else:
            return jsonify({'File not found': image_location})


@images_blueprint.route('/avatar/<user_id>/create', methods=['POST'])
@jwt_required(fresh=True)
def new_avatar(user_id):
    username = get_jwt_identity()
    target_user = get_user(user_id)

    if not target_user:
        return jsonify({'Error': 'User not found'})

    if target_user.username != username:
        current_app.logger.info('!!! {} tried to change another users avatar: {}'.format(username, target_user.username))
        return jsonify({'Error': 'Not authorized'})

    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)

        if filename == '':
            current_app.logger.info('{} posted a file with no name!'.format(username))
            return jsonify({'Error': 'Bad filename'})
        if not file:
            current_app.logger.info('{} posted file {} and had some issue.'.format(username, filename))
            return jsonify({'Error': 'Bad file'})
        if not allowed_file(file):
            current_app.logger.info('{} posted a bad file type, {}'.format(username, filename))
            pass
            # return jsonify({'Error': 'Bad file type'})

        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        image_id = save_image(None, None, filepath, is_avatar=True)
        change_user_avatar(target_user.username, image_id)

        file.save(filepath)  # store image locally on disk

        current_app.logger.info('{} {} changed their avatar'.format(user_id, username))
        return jsonify({'Success': 'Avatar changed, GET user for ID'})

