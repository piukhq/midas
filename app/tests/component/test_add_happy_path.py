from http import HTTPStatus, HTTPMethod
from unittest.mock import MagicMock

import pytest
import responses
from flask.testing import FlaskClient
from soteria.configuration import Configuration

from app.tests.component import stonegate
from app.tests.component.mocks import Endpoint
import settings


@pytest.fixture
def common_patches(monkeypatch):
    monkeypatch.setattr("app.resources.decrypt_credentials", lambda *_: {"card_number": "3287211356"})
    monkeypatch.setattr("settings.CONFIG_SERVICE_URL", "http://mock_europa.com")
    monkeypatch.setattr(
        Configuration,
        "get_security_credentials",
        lambda *_: [{"value": {"password": "MBX1pmb2uxh5vzc@ucp", "username": "acteol.test@bink.com"}}],
    )
    monkeypatch.setattr("app.agents.stonegate.Stonegate.authenticate", lambda *_: None)
    monkeypatch.setattr("app.agents.stonegate.signal", lambda *_: MagicMock())
    monkeypatch.setattr("app.agents.base.signal", lambda *_: MagicMock())

    responses.add(
        HTTPMethod.PUT,
        f"{settings.HERMES_URL}/schemes/accounts/1/credentials",
        json={},
    )
    responses.add(
        HTTPMethod.GET,
        f"{settings.CONFIG_SERVICE_URL}/configuration",
        json={
            "merchant_url": "https://atreemouat.xxxitsucomms.co.uk",
            "retry_limit": 3,
            "log_level": 0,
            "callback_url": "",
            "country": "uk",
            "security_credentials": {
                "inbound": {
                    "service": 4,
                    "credentials": [
                        {
                            "credential_type": 3,
                            "storage_key": "a_storage_key",
                            "value": {"password": "paSSword", "username": "username@bink.com"},
                        },
                    ],
                },
                "outbound": {
                    "service": 4,
                    "credentials": [
                        {
                            "credential_type": 3,
                            "storage_key": "a_storage_key",
                            "value": {"password": "paSSword", "username": "username@bink.com"},
                        },
                    ],
                },
            },
        },
    )


@responses.activate
@pytest.mark.parametrize(
    "slug, endpoints",
    [("stonegate", stonegate.ENDPOINTS)],
)
@pytest.mark.usefixtures("common_patches")
def test_add_happy_path(slug: str, endpoints: list[Endpoint], client: FlaskClient) -> None:
    for endpoint in endpoints:
        responses.add(endpoint.method, endpoint.url, json=endpoint.response_body)

    response = client.get(
        f"/{slug}/balance?scheme_account_id=1&user_id=1&bink_user_id=1&journey_type=2&credentials=xxx&token=xxx"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {
        "points": 3,
        "points_label": "3",
        "value": 0.0,
        "value_label": "",
        "scheme_account_id": 1,
        "user_set": "1",
        "bink_user_id": 1,
        "reward_tier": 0,
        "vouchers": [],
    }
