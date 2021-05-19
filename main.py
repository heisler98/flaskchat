# github.com/colingoodman

# Blueprints
from api.auth import auth_blueprint
from api.rooms import rooms_blueprint
from api.sockets import sockets_blueprint
from api.users import users_blueprint
from api.images import images_blueprint
from api.app import create_app, socketio

# App Setup
app = create_app(debug=True)

# API Blueprints
app.register_blueprint(auth_blueprint)
app.register_blueprint(rooms_blueprint)
app.register_blueprint(users_blueprint)
app.register_blueprint(images_blueprint)
app.register_blueprint(sockets_blueprint)


if __name__ == '__main__':
    socketio.run(app, debug=True)
