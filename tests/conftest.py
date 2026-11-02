import pytest

from drop import create_app


@pytest.fixture()
def app():
    return create_app({"TESTING": True, "PASSWORD": "test", "SECRET_KEY": "test"})


@pytest.fixture()
def client(app):
    return app.test_client()
