# github.com/colingoodman
import json
from bson import json_util

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def parse_json(data):
    return json.loads(json_util.dumps(data))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


