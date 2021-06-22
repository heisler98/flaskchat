import os
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


def test_empty_db(client):
    res = client.get('/api/')
    assert res.status_code == 200
    expected = {'Hello': 'World'}
    assert expected == json.loads(res.get_data(as_text=True))


def test_auth(client):
    res = client.get('/api/login')
    assert res.status_code == 405

    token = authenticate(client)

    headers = {'tasty_token': 'Bearer {}'.format(token)}
    res = client.get('/api/whoami', headers=headers)

    who_response = json.loads(res.get_data(as_text=True))
    returned_username = who_response['user']
    assert res.status_code == 200
    assert returned_username == 'testuser'


def test_rooms(client):
    res = client.post('/api/rooms/list')
    assert res.status_code == 405

    token = authenticate(client)

    headers = {'tasty_token': 'Bearer {}'.format(token)}
    res = client.get('/api/rooms/list', headers=headers)
    assert res.status_code == 200
    list_response = json.loads(res.get_data(as_text=True))['rooms']
    assert len(list_response) > 0
    some_room = list_response[0]

    res = client.get('/api/rooms/{}'.format(some_room), headers=headers)
    assert res.status_code == 200

    res = client.get('/api/rooms/all', headers=headers)
    assert res.status_code == 200
    all_rooms = json.loads(res.get_data(as_text=True))


def test_users(client):
    pass
