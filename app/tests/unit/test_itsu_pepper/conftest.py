import json
from http import HTTPStatus

import httpretty
import pytest
from soteria.configuration import Configuration

import settings
from app.agents.itsu import Itsu

from .setup_data import (
    CONFIG_JSON_ITSU_BODY,
    CONFIG_JSON_PEPPER_BODY,
    EXPECTED_CARD_NUMBER,
    EXPECTED_PEPPER_ID,
    MESSAGE,
    PEPPER_MERCHANT_URL,
    SECRET_ITSU_ACTEOL_JOIN,
    SECRET_ITSU_PEPPER_JOIN,
    USER_INFO,
)


@pytest.fixture
def mock_europa_request():
    def mock_request(response=None):
        uri = "http://mock_europa.com/configuration"
        httpretty.register_uri(
            httpretty.GET,
            uri=uri,
            status=HTTPStatus.OK,
            body=json.dumps(response),
            content_type="text/json",
        )

    return mock_request


@pytest.fixture()
@httpretty.activate
def itsu(monkeypatch, mock_europa_request):
    mock_europa_url = "http://mock_europa.com"
    monkeypatch.setattr(settings, "CONFIG_SERVICE_URL", mock_europa_url)
    monkeypatch.setattr(Configuration, "get_security_credentials", lambda *_: SECRET_ITSU_ACTEOL_JOIN)
    mock_europa_request(response=CONFIG_JSON_ITSU_BODY)
    return Itsu(5, USER_INFO, scheme_slug=MESSAGE["loyalty_plan"])


@pytest.fixture
@httpretty.activate
def itsu_pepper(monkeypatch, mock_europa_request):
    mock_europa_url = "http://mock_europa.com"
    monkeypatch.setattr(settings, "CONFIG_SERVICE_URL", mock_europa_url)
    monkeypatch.setattr(Configuration, "get_security_credentials", lambda *_: SECRET_ITSU_ACTEOL_JOIN)
    mock_europa_request(response=CONFIG_JSON_ITSU_BODY)
    itsu_pepper = Itsu(5, USER_INFO, scheme_slug=MESSAGE["loyalty_plan"])
    monkeypatch.setattr(Configuration, "get_security_credentials", lambda *_: SECRET_ITSU_PEPPER_JOIN)
    mock_europa_request(response=CONFIG_JSON_PEPPER_BODY)
    pepper_base_url = itsu_pepper.set_pepper_config()
    assert pepper_base_url == PEPPER_MERCHANT_URL
    return itsu_pepper


@pytest.fixture
def mock_pepper_user_request():
    def mock_request(status=HTTPStatus.OK, response=None):
        if not response:
            response = {"id": EXPECTED_PEPPER_ID}
        api_url = f"{PEPPER_MERCHANT_URL}/users?autoActivate=true"
        httpretty.register_uri(
            httpretty.POST,
            uri=api_url,
            status=status,
            body=json.dumps(response),
            content_type="text/json",
        )

    return mock_request


@pytest.fixture
def mock_pepper_loyalty_request():
    def mock_request(pepper_id=EXPECTED_PEPPER_ID, status=HTTPStatus.OK, response=None):
        if not response:
            response = {"externalLoyaltyMemberNumber": EXPECTED_CARD_NUMBER}
        api_url = f"{PEPPER_MERCHANT_URL}/users/{pepper_id}/loyalty"
        httpretty.register_uri(
            httpretty.POST,
            uri=api_url,
            status=status,
            body=json.dumps(response),
            content_type="text/json",
        )

    return mock_request


@pytest.fixture
def mock_itsu_signals(mock_signals):
    return mock_signals(patches=["app.agents.itsu.signal"], base_agent=True)
