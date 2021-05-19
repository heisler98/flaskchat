from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins='*')


def create_app(debug=True):
    app = Flask(__name__)
    app.debug = debug
    app.secret_key = "dev"

    cors = CORS(app)
    app.config['CORS_HEADERS'] = 'Content-Type'

    jwt = JWTManager(app)
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["JWT_HEADER_NAME"] = 'tasty_token'

    socketio.init_app(app)
    return app
