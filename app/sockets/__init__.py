from flask import Blueprint

sockets_blueprint = Blueprint("sockets", __name__)

from app.sockets import routes