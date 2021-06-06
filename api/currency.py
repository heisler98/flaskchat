# github.com/colingoodman

from flask import Blueprint, request, jsonify, current_app

currency_blueprint = Blueprint('currency_blueprint', __name__)

@currency_blueprint.route('/purchase')
@jwt_required()
def buy_something():
    username = get_jwt_identity()


