from flask import Blueprint

rooms_blueprint = Blueprint("rooms", __name__)

from app.rooms import routes