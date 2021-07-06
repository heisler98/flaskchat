# github.com/colingoodman
import os
import sys

from api.auth import auth_blueprint
from api.rooms import rooms_blueprint
from api.sockets import sockets_blueprint
from api.users import users_blueprint
from api.images import images_blueprint
from api.app import create_app, socketio

from flask_cors import CORS

# App Setup
app = create_app(debug=True)
CORS(app)
production = False

# API Blueprints
app.register_blueprint(auth_blueprint, url_prefix='/api')
app.register_blueprint(rooms_blueprint, url_prefix='/api')
app.register_blueprint(users_blueprint, url_prefix='/api')
app.register_blueprint(images_blueprint, url_prefix='/api')
app.register_blueprint(sockets_blueprint, url_prefix='/api')


if __name__ == '__main__':
    if production:
        os.chdir(os.path.dirname(sys.argv[0]))
        socketio.run(app, host='0.0.0.0', debug=True)
    else:
        socketio.run(app, debug=True)
