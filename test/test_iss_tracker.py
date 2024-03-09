import pytest
from iss_tracker_app import get_data
from iss_tracker_app import calc_speed_3d
from iss_tracker_app import current_location
from iss_tracker_app import create_app
from iss_tracker_app import find_location
import requests
from flask import Flask, request

@pytest.fixture
def app():
    app = create_app()

    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def test_get_data():
    assert isinstance(get_data(), list) == True

def test_find_location():
    assert isinstance(find_location(4000, 1500, -5000, '2024-001T12:00:00.000Z'), list) == True
    assert find_location(4000, 1500, -5000, '2024-000') == []


def test_calc_speed_3d():
    assert calc_speed_3d(3.0, 4.0, 0.0) == 5.0
    assert calc_speed_3d(6.0, 0.0, 8.0) == 10.0
    assert calc_speed_3d('x', 'y', 'z') == 0.0

def test_return_comments(client):
    response = client.get('/comment')
    assert response.status_code == 200
    assert isinstance(response.json, list) == True

def test_return_header(client):
    response = client.get('/header')
    assert response.status_code == 200
    assert isinstance(response.json, dict) == True

def test_return_metadata(client):
    response = client.get('/metadata')
    assert response.status_code == 200
    assert isinstance(response.json, dict) == True

def test_return_all(client):
    response = client.get('/epochs')
    assert response.status_code == 200
    assert isinstance(response.json, list) == True

    response = client.get('/epochs?limit=10&offset=abc')
    assert response.status_code == 200
    assert len(response.json) == 10

    response = client.get('epochs?limit=abc')
    assert response.status_code == 200

def test_return_epoch(client):
    response = client.get('/epochs/2024-050T12:00:00.000Z')
    assert response.status_code == 200
    assert isinstance(response.json, dict) == True

    response = client.get('/epochs/2024-200')
    assert response.status_code == 200
    assert response.json == {}

def test_return_epoch_speed(client):
    response = client.get('/epochs/2024-050T12:00:00.000Z/speed')
    assert response.status_code == 200
    assert isinstance(float(response.data), float) == True

    response = client.get('/epochs/2024-200/speed')
    assert response.status_code == 200


def test_return_epoch_location(client):
    response = client.get('/epochs/2024-069T06:38:30.000Z/location')
    assert response.status_code == 200
    assert response.json != []

    response = client.get('/epochs/2024-100/location')
    assert response.status_code == 200
    assert response.json == []


def test_data_now(client):
    response = client.get('/now')
    assert response.status_code == 200
    assert isinstance(response.json, dict) == True
    assert b'SPEED' in response.data
    assert b'COORDINATES' in response.data
    assert b'ALTITUDE (km)' in response.data
    assert b'LOCATION' in response.data
    
def test_current_location():
    assert current_location([{'epoch': '2024-045T12:00:00.000Z'}], 'epoch') == {'epoch': '2024-045T12:00:00.000Z'}
    assert current_location([{'epoch': '2024-045T12:00:00.000Z', 'time' : '12am'}], 'epoch') == {'epoch': '2024-045T12:00:00.000Z', 'time': '12am'}
    assert current_location([{'epoch': '2024-045T12:00:00.000Z'}, {'epoch': '2034-045T12:00:00.000Z'}], 'epoch') == {'epoch': '2024-045T12:00:00.000Z'}
    assert current_location([{'epoch': '2024-045'}], 'epoch') == {}
    

