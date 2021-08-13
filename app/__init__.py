# github.com/colingoodman
# flask app creation

from datetime import timedelta
import os

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins='*')


def create_app(debug=True, production=False):
    app = Flask(__name__)
    app.debug = debug
    app.secret_key = "dev"

    directory = os.getcwd()

    jwt = JWTManager(app)
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)  # = timedelta(minutes=15) !!!
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["JWT_HEADER_NAME"] = 'tasty_token'

    app.config['UPLOAD_FOLDER'] = os.path.join(directory, 'uploads')

    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["240 per minute"]
    )

    socketio.init_app(app, async_mode='eventlet')
    return app
