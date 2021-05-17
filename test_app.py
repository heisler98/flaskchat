import os
import pytest
from app import app as flask_app
import json

token = ""


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True

    with flask_app.test_client() as client:
        yield client


def test_empty_db(client):
    res = client.get('/')
    assert res.status_code == 200
    expected = {'Hello': 'World'}
    assert expected == json.loads(res.get_data(as_text=True))


def test_login_logout(client):
    res = client.get('/login')
    assert res.status_code == 405
    res = client.post('/login', json=json.loads(json.dumps({"username": "testuser", "password": "password"})))
    assert res.status_code == 200
    response_data = json.loads(res.get_data(as_text=True))
    token = response_data["Token"]
    assert response_data
