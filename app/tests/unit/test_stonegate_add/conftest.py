import json
from http import HTTPStatus

import httpretty
import pytest
from soteria.configuration import Configuration

import settings

from .setup_data import MERCHANT_URL


@pytest.fixture()
def patch_balance_login(monkeypatch, mock_europa_request, redis_retry_pretty_fix):
    def patchit(credentials, secret, conf_body):
        monkeypatch.setattr("app.resources.decrypt_credentials", lambda *_: credentials)
        monkeypatch.setattr(settings, "CONFIG_SERVICE_URL", "http://mock_europa.com")
        monkeypatch.setattr(Configuration, "get_security_credentials", lambda *_: secret)
        monkeypatch.setattr("app.agents.stonegate.Stonegate.authenticate", lambda *_: None)
        mock_europa_request(conf_body)

    return patchit


@pytest.fixture
def http_pretty_find_user():
    def mock_request(status=HTTPStatus.OK, response=None):
        api_url = f"{MERCHANT_URL}/api/Customer/FindCustomerDetails"
        httpretty.register_uri(
            httpretty.POST,
            uri=api_url,
            status=status,
            body=json.dumps(response),
            content_type="text/json",
        )

    return mock_request


@pytest.fixture
def http_pretty_user_patch():
    def mock_request(status=HTTPStatus.OK, response=None):
        api_url = f"{MERCHANT_URL}/api/Customer/Patch"
        httpretty.register_uri(
            httpretty.PATCH,
            uri=api_url,
            status=status,
            body=json.dumps(response),
            content_type="text/json",
        )

    return mock_request


@pytest.fixture
def http_pretty_send_credentials():
    def mock_request(account_id, status=HTTPStatus.OK, response=None):
        api_url = f"https://127.0.0.1:8000/schemes/accounts/{account_id}/credentials"
        httpretty.register_uri(
            httpretty.PUT,
            uri=api_url,
            status=status,
            body=json.dumps(response),
            content_type="text/json",
        )

    return mock_request


@pytest.fixture
def mock_stonegate_signals(mock_signals):
    return mock_signals(patches=["app.agents.stonegate.signal"], base_agent=True)
