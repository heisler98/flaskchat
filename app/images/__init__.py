from flask import Blueprint

images_blueprint = Blueprint("images", __name__)

from app.images import routes