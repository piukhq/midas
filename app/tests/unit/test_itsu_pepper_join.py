import json
from http import HTTPStatus
from unittest.mock import patch

import httpretty
import pytest
from soteria.configuration import Configuration

from app.agents.itsu import Itsu

SECRET_ITSU_ACTEOL_JOIN = [{"value": {"password": "MBX1pmb2uxh5vzc@ucp", "username": "acteol.itsu.test@bink.com"}}]

SECRET_ITSU_PEPPER_JOIN = [{"value": {"authorization": "627b9ee5c0aebf0e54a3b3dc", "application-id": "bink-03dxtvc8"}}]

CONFIG_JSON_ITSU_BODY = {
    "merchant_url": "https://atreemouat.itsucomms.co.uk/",
    "retry_limit": 3,
    "log_level": 0,
    "callback_url": "",
    "country": "uk",
    "security_credentials": {
        "inbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": 3,
                    "storage_key": "a_storage_key",
                    "value": {"password": "paSSword", "username": "username@bink.com"},
                },
            ],
        },
        "outbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": 3,
                    "storage_key": "a_storage_key",
                    "value": {"password": "paSSword", "username": "username@bink.com"},
                },
            ],
        },
    },
}

PEPPER_MERCHANT_URL = "https://beta-api.xxxpepperhq.com"
EXPECTED_PEPPER_ID = "64d498865e2b5f4d03c2a70e"
EXPECTED_CARD_NUMBER = "1105763052"

CONFIG_JSON_PEPPER_BODY = {
    "merchant_url": PEPPER_MERCHANT_URL,
    "retry_limit": 3,
    "log_level": 0,
    "callback_url": "",
    "country": "uk",
    "security_credentials": {
        "inbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": 3,
                    "storage_key": "a_pepper_storage_key",
                    "value": {"password": "paSSword", "username": "username@bink.com"},
                },
            ],
        },
        "outbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": 3,
                    "storage_key": "a_pepper_storage_key",
                    "value": {"password": "paSSword", "username": "username@bink.com"},
                },
            ],
        },
    },
}

EXPECTED_PEPPER_PAYLOAD = {
    "firstName": "Fake",
    "lastName": "Name",
    "credentials": [
        {"provider": "EMAIL", "id": "test_mm_1@bink.com", "token": "userspassword1"},
    ],
    "hasAgreedToShareData": True,
    "hasAgreedToReceiveMarketing": True,
}


EXPECTED_ITSU_PEPPER_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Token 627b9ee5c0aebf0e54a3b3dc",
    "x-api-version": "10",
    "x-application-id": "bink-03dxtvc8",
    "x-client-platform": "BINK",
}


@pytest.fixture
@httpretty.activate
def itsu():
    mock_europa_url = "http://mock_europa.com"
    with patch("settings.CONFIG_SERVICE_URL", mock_europa_url):
        uri = f"{mock_europa_url}/configuration"
        user_info = {
            "scheme_account_id": 1235,
            "channel": "test",
            "journey_type": Configuration.JOIN_HANDLER,
            "credentials": {
                "first_name": "Fake",
                "last_name": "Name",
                "email": "test_mm_1@bink.com",
                "password": "userspassword1",
                "consents": [
                    {"id": 11738, "slug": "email_marketing", "value": True, "created_on": "1996-09-26T00:00:00"}
                ],
            },
        }
        httpretty.register_uri(
            httpretty.GET,
            uri=uri,
            status=HTTPStatus.OK,
            body=json.dumps(CONFIG_JSON_ITSU_BODY),
            content_type="text/json",
        )
        with patch("app.agents.base.Configuration.get_security_credentials", return_value=SECRET_ITSU_ACTEOL_JOIN):
            return Itsu(5, user_info, scheme_slug="itsu")


@pytest.fixture
@httpretty.activate
def pepper_base_url(itsu):
    mock_europa_url = "http://mock_europa.com"
    with patch("settings.CONFIG_SERVICE_URL", mock_europa_url):
        with patch("app.agents.base.Configuration.get_security_credentials", return_value=SECRET_ITSU_PEPPER_JOIN):
            uri = "http://mock_europa.com/configuration"
            httpretty.register_uri(
                httpretty.GET,
                uri=uri,
                status=HTTPStatus.OK,
                body=json.dumps(CONFIG_JSON_PEPPER_BODY),
                content_type="text/json",
            )
            pepper_base_url = itsu.set_pepper_config()
            return pepper_base_url


@pytest.fixture
@httpretty.activate
def pepper_id(pepper_base_url, itsu):
    api_url = f"{pepper_base_url}/users?autoActivate=true"
    httpretty.register_uri(
        httpretty.POST,
        uri=api_url,
        status=HTTPStatus.OK,
        body=json.dumps({"id": EXPECTED_PEPPER_ID}),
        content_type="text/json",
    )
    returned_pepper_id = itsu.pepper_add_user(pepper_base_url)
    return returned_pepper_id


def test_itsu_pepper_get_by_id(itsu):
    payload = itsu.pepper_add_user_payload()
    assert payload == EXPECTED_PEPPER_PAYLOAD
    assert itsu.headers == {}


def test_itsu_set_pepper_config(pepper_base_url, itsu):
    assert pepper_base_url == PEPPER_MERCHANT_URL
    payload = itsu.pepper_add_user_payload()
    assert payload == EXPECTED_PEPPER_PAYLOAD
    assert itsu.scheme_slug == "itsu"
    assert itsu.headers == EXPECTED_ITSU_PEPPER_HEADERS


@httpretty.activate
def test_itsu_pepper_add_user(pepper_base_url, itsu):
    api_url = f"{pepper_base_url}/users?autoActivate=true"
    pepper_id = "64d498865e2b5f4d03c2a70e"
    httpretty.register_uri(
        httpretty.POST,
        uri=api_url,
        status=HTTPStatus.OK,
        body=json.dumps({"id": pepper_id}),
        content_type="text/json",
    )
    returned_pepper_id = itsu.pepper_add_user(pepper_base_url)
    assert returned_pepper_id == pepper_id


@httpretty.activate
def test_itsu_call_pepper_for_card_number(pepper_id, pepper_base_url, itsu):
    api_url = f"{pepper_base_url}/users/{pepper_id}/loyalty"
    httpretty.register_uri(
        httpretty.POST,
        uri=api_url,
        status=HTTPStatus.OK,
        body=json.dumps({"externalLoyaltyMemberNumber": EXPECTED_CARD_NUMBER}),
        content_type="text/json",
    )
    card_number = itsu.call_pepper_for_card_number(pepper_id, pepper_base_url)
    assert card_number == EXPECTED_CARD_NUMBER
