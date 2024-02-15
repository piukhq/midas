import pytest
from typing import Generator
from flask.testing import FlaskClient

from app.api import create_app


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    yield client
