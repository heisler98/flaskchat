import os
import pytest
from main import app as flask_app
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


def test_auth(client):
    res = client.get('/login')
    assert res.status_code == 405

    res = client.post('/login', json=json.loads(json.dumps({"username": "testuser", "password": "password"})))
    assert res.status_code == 200

    login_response = json.loads(res.get_data(as_text=True))
    token = login_response["Token"]
    headers = {'tasty_token': 'Bearer {}'.format(token)}
    res = client.get('/whoami', headers=headers)

    who_response = json.loads(res.get_data(as_text=True))
    returned_username = who_response['user']
    assert res.status_code == 200
    assert returned_username == 'testuser'


def test_rooms(client):
    res = client.post('/rooms/list')
    assert res.status_code == 405

    headers = {'tasty_token': 'Bearer {}'.format(token)}
    res = client.get('/rooms/list', headers=headers)
    assert res.status_code == 200
    list_response = json.loads(res.get_data(as_text=True))

