import importlib
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from utils.database import Base
from dependencies import get_db, get_token_header
import requests
# import os

# Below configuration can use to override test database from the original db
# DB_USERNAME = os.getenv('DB_USERNAME')
# DB_PASSWORD = os.getenv('DB_PASSWORD')
# SQLALCHEMY_DB_URL = "postgresql://%s:%s@db/environment_test" % (DB_USERNAME, DB_PASSWORD)

# engine = create_engine(
#     SQLALCHEMY_DB_URL, connect_args={"check_same_thread": False}
# )
# TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base.metadata.create_all(bind=engine)


# def override_get_db():
#     try:
#         db = TestingSessionLocal()
#         yield db
#     finally:
#         db.close()


# app.dependency_overrides[get_db] = override_get_db
def override_get_token_header():
    return True


app.dependency_overrides[get_token_header] = override_get_token_header

client = TestClient(app)


def test_get_environments():
    response = client.get("/v1/environments")
    assert response.status_code == 200


def test_get_environment_404():
    response = client.get("/v1/environments/bb27b561-c63c-49b6-a385-c46e42430314")
    assert response.status_code == 404


def test_create_environment_201():
    response = client.post("/v1/environments", json={
        "id": "4f07cf23-cd0f-42b5-99c4-efa9022adccf",
        "name": "Test Env",
        "description": "Test Env Description",
        "deleted": False,
        "group": 'fc584042-5c3c-4f76-8c75-ab45b98bed46',  # Non existing key but using as ref
        "active": True
    })
    assert response.json() == {'success': True}
    assert response.status_code == 200


def test_get_environment_200():
    sample_id = '4f07cf23-cd0f-42b5-99c4-efa9022adccf'
    response = client.get("/v1/environments/{}".format(sample_id))
    assert response.status_code == 200


def test_update_environment_200():
    sample_id = '4f07cf23-cd0f-42b5-99c4-efa9022adccf'
    response = client.put("/v1/environments/{}".format(sample_id), json={
        "id": "4f07cf23-cd0f-42b5-99c4-efa9022adccf",
        "name": "Test Env 2",
        "description": "Test Env Description 2",
        "deleted": False,
        "group": 'fc584042-5c3c-4f76-8c75-ab45b98bed46',  # Non existing key but using as ref
        "active": False
    })
    assert response.status_code == 200


def test_delete_environment_204():
    sample_id = '4f07cf23-cd0f-42b5-99c4-efa9022adccf'
    response = client.delete("/v1/environments/{}?force=true".format(sample_id))
    assert response.status_code == 204
