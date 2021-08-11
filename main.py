# github.com/colingoodman
import os
import sys

from app.auth import auth_blueprint
from app.rooms import rooms_blueprint
from app.sockets import sockets_blueprint
from app.users import users_blueprint
from app.images import images_blueprint
from api.aggregate import aggregate_blueprint

from app import create_app, socketio

from flask_cors import CORS

import logging

# App Setup
production = False
cwd = os.getcwd()
app = create_app(debug=True, production=production, directory=cwd)
CORS(app)

# API Blueprints
app.register_blueprint(auth_blueprint, url_prefix='/api')
app.register_blueprint(rooms_blueprint, url_prefix='/api')
app.register_blueprint(users_blueprint, url_prefix='/api')
app.register_blueprint(images_blueprint, url_prefix='/api')
app.register_blueprint(sockets_blueprint, url_prefix='/api')
app.register_blueprint(aggregate_blueprint, url_prefix='/api')

log = logging.getLogger('werkzeug')
log.disabled = True

if __name__ == '__main__':
    if production:
        socketio.run(app, host='0.0.0.0', debug=True, port=5000)
    else:
        socketio.run(app, debug=True, port=5001)
