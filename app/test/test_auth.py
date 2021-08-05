# github.com/colingoodman
# tests for authentication

import pytest
from main import app as flask_app

import json

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True

    with flask_app.test_client() as client:
        yield client

def authenticate(client):
    res = client.post('/api/login', json=json.loads(json.dumps({"username": "testuser", "password": "password"})))

    login_response = json.loads(res.get_data(as_text=True))
    token = login_response["Token"]

    return token

