from datetime import timedelta
import os

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
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["JWT_HEADER_NAME"] = 'tasty_token'

    app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.join('..', 'uploads'))

    socketio.init_app(app)
    return app
