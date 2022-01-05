import importlib
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from utils.database import Base
from dependencies import get_db, get_token_header


def override_get_token_header():
    return True


app.dependency_overrides[get_token_header] = override_get_token_header

client = TestClient(app)


def test_get_resources():
    response = client.get("/v1/resources")
    assert response.status_code == 200


def test_get_resources_204():
    response = client.get("/v1/resources?name=x")
    assert response.json()['meta']['total_records'] == 0


def test_get_resource_404():
    response = client.get("/v1/resources/1f07cf23-cd0f-42b5-99c4-efa9022adccf")
    assert response.status_code == 404


def test_get_resource_200():
    resources = client.get("/v1/resources")
    sample_id = resources.json()['data'][0]['id']
    response = client.get("/v1/resources/{}".format(sample_id))
    assert response.status_code == 200
