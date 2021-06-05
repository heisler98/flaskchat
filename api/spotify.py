# github.com/colingoodman

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity

import spotipy

music_blueprint = Blueprint('music_blueprint', __name__)


@music_blueprint.route('music/auth')
@jwt_required(fresh=True)
def music_auth():
    pass
