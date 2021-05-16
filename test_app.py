import os
import pytest
from app import app as flask_app
import json


@pytest.fixture
def app():
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index(app, client):
    res = client.get('/')
    assert res.status_code == 200
    expected = {'Hello': 'World'}
    assert expected == json.loads(res.get_data(as_text=True))


def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)


def test_login(app, client):
    username = 'testuser'
    password = 'password'

    rv = login(client, username, password)
    assert rv.status_code == 200

