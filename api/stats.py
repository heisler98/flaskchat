# github.com/colingoodman
from flask import Blueprint
from flask_jwt_extended import jwt_required

stats_blueprint = Blueprint('stats_blueprint', __name__)


@stats_blueprint.route('/stats/message_count', methods=['GET'])
@jwt_required()
def message_count():
    return None

