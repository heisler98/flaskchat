from flask import Blueprint

stats_blueprint = Blueprint("stats", __name__)

from app.stats import routes