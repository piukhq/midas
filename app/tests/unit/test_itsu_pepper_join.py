import json
from http import HTTPStatus
# from unittest.mock import patch

import httpretty
from soteria.configuration import Configuration

import settings
# from app.agents.itsu import Itsu

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


CONFIG_JSON_PEPPER_BODY = {
    "merchant_url": "https://beta-api.pepperhq.com",
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


def mock_itsu_config():
    uri = f"{settings.CONFIG_SERVICE_URL}/configuration"
    httpretty.register_uri(
        httpretty.GET,
        uri=uri,
        status=HTTPStatus.OK,
        body=json.dumps(CONFIG_JSON_ITSU_BODY),
        content_type="text/json",
    )


def mock_pepper_config():
    uri = f"{settings.CONFIG_SERVICE_URL}/configuration"
    httpretty.register_uri(
        httpretty.GET,
        uri=uri,
        status=HTTPStatus.OK,
        body=json.dumps(CONFIG_JSON_PEPPER_BODY),
        content_type="text/json",
    )


@httpretty.activate
def test_itsu_pepper_get_by_id():

    user_info = {
        "scheme_account_id": 1235,
        "channel": "test",
        "journey_type": Configuration.JOIN_HANDLER,
        "credentials": {
            "first_name": "Fake",
            "last_name": "Name",
            "email": "test_mm_1@bink.com",
            "password": "userspassword1",
            "consents": [{"id": 11738, "slug": "email_marketing", "value": True, "created_on": "1996-09-26T00:00:00"}],
        },
    }
    mock_itsu_config()
    with patch("app.agents.base.Configuration.get_security_credentials", return_value=SECRET_ITSU_ACTEOL_JOIN):
        itsu = Itsu(5, user_info, scheme_slug="itsu")
        payload = itsu.pepper_add_user_payload()
        assert payload == EXPECTED_PEPPER_PAYLOAD
        mock_pepper_config()
        with patch("app.agents.base.Configuration.get_security_credentials", return_value=SECRET_ITSU_PEPPER_JOIN):
            pepper_base_url = itsu.set_pepper_config()
            assert pepper_base_url == "https://beta-api.pepperhq.com"
            httpretty.disable()

            pepper_id = itsu.pepper_add_user(pepper_base_url)
            assert pepper_id == "64d498865e2b5f4d03c2a70e"
            # itsu.pepper_get_by_id(EXPECTED_PEPPER_PAYLOAD['credentials']['id'], pepper_base_url)


    assert True
