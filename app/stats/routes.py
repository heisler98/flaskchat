# github.com/colingoodman

from app.stats import stats_blueprint

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, current_app, request, jsonify, send_file

from db import store_click_openroom


@stats_blueprint.route('/stats/<user_id>/click', methods=['POST'])
@jwt_required()
def get_rooms(user_id):
    auth_user_id = get_jwt_identity()

    if auth_user_id != user_id:
        return jsonify({'Error': 'Not authorized'}), 403

    json_input = request.get_json(force=True)

    try:
        room_id = json_input['room_id']
    except KeyError as e:
        return jsonify({'Error': 'Invalid request: Missing required field.'}), 400
    except TypeError as e:
        return jsonify({'Error': 'Invalid request: Must be a json/dict.'}), 400

    store_click_openroom(user_id, room_id)

    return jsonify({'Success': 'Click saved'}), 200

