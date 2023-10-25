import json
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock
from urllib.parse import urljoin

import httpretty
import pytest
from soteria.configuration import Configuration

from app.agents.stonegate import Stonegate
from app.exceptions import AccountAlreadyExistsError, JoinError
from app.scheme_account import JourneyTypes

RESPONSE_DATA_FIND_CUSTOMER_DETAILS = {
    "ResponseData": {
        "Duplicated": "true",
        "CtcID": 2,
        "CpyID": 3,
        "MD5": "sample string 4",
        "ReferrerCode": "sample string 5",
        "MemberNumber": "sample string 6",
    },
    "ResponseStatus": "true",
    "Errors": [
        {"ErrorCode": 4, "ErrorDescription": "No data found"},
    ],
}

RESPONSE_DATA_NO_MEMBER_NUMBER = {
    "ResponseData": {
        "Duplicated": "true",
        "CtcID": 2,
        "CpyID": 3,
        "MD5": "sample string 4",
        "ReferrerCode": "sample string 5",
        "MemberNumber": "",
    },
    "ResponseStatus": "true",
    "Errors": [
        {"ErrorCode": 4, "ErrorDescription": "No data found"},
    ],
}

RESPONSE_DATA_ACCOUNT_NOT_EXIST = {
    "ResponseData": {
        "Duplicated": "true",
        "CtcID": 2,
        "CpyID": 3,
        "MD5": "sample string 4",
        "ReferrerCode": "sample string 5",
        "MemberNumber": "sample string 6",
    },
    "ResponseStatus": "true",
    "Errors": [
        {"ErrorCode": 4, "ErrorDescription": "No data found"},
    ],
}

RESPONSE_DATA_ACCOUNT_EXISTS = {
    "ResponseData": {
        "Duplicated": "true",
        "CtcID": 2,
        "CpyID": 3,
        "MD5": "sample string 4",
        "ReferrerCode": "sample string 5",
        "MemberNumber": "sample string 6",
    },
    "ResponseStatus": "true",
    "Errors": [],
}

RESPONSE_DATA_ERROR = {
    "ResponseData": {
        "Duplicated": "true",
        "CtcID": 2,
        "CpyID": 3,
        "MD5": "sample string 4",
        "ReferrerCode": "sample string 5",
        "MemberNumber": "sample string 6",
    },
    "ResponseStatus": "true",
    "Errors": [
        {"ErrorCode": 1, "ErrorDescription": "Some error happened"},
    ],
}

CREDENTIALS = {
    "first_name": "Fake",
    "last_name": "Name",
    "email": "email@domain.com",
    "password": "pAsSw0rD",
    "consents": [{"id": 11738, "slug": "Subscription", "value": False, "created_on": "1996-09-26T00:00:00"}],
}

OUTBOUND_SECURITY_CREDENTIALS = {
    "outbound": {
        "service": Configuration.OAUTH_SECURITY,
        "credentials": [
            {
                "value": {
                    "url": "http://fake.com",
                    "secondary-key": "12345678",
                    "client-id": "123",
                    "client-secret": "123a6ba",
                    "scope": "dunno",
                },
            }
        ],
    },
}


@pytest.fixture
def stonegate():
    with mock.patch("app.agents.base.Configuration") as mock_configuration:
        mock_config_object = MagicMock()
        mock_config_object.security_credentials = OUTBOUND_SECURITY_CREDENTIALS
        mock_config_object.integration_service = "SYNC"
        mock_configuration.return_value = mock_config_object
        stonegate = Stonegate(
            retry_count=1,
            user_info={
                "user_set": "12345",
                "credentials": CREDENTIALS,
                "status": 442,
                "journey_type": JourneyTypes.JOIN,
                "scheme_account_id": 99999,
                "channel": "com.bink.wallet",
            },
            scheme_slug="stonegate",
        )
        stonegate.base_url = "http://fake.com/"
        return stonegate


@httpretty.activate
@mock.patch("app.agents.stonegate.Stonegate.authenticate")
@mock.patch("app.agents.stonegate.signal", autospec=True)
def test_create_account_200(mock_signal, mock_authenticate, stonegate):
    details_url = urljoin(stonegate.base_url, "api/Customer/FindCustomerDetails")
    export_url = urljoin(stonegate.base_url, "api/Customer/Post")
    httpretty.register_uri(
        httpretty.POST,
        uri=details_url,
        status=HTTPStatus.OK,
        responses=[
            httpretty.Response(
                body=json.dumps(RESPONSE_DATA_ACCOUNT_NOT_EXIST),
                status=HTTPStatus.OK,
            )
        ],
    )
    httpretty.register_uri(
        httpretty.POST,
        uri=export_url,
        status=HTTPStatus.OK,
        responses=[
            httpretty.Response(
                body=json.dumps(RESPONSE_DATA_ACCOUNT_NOT_EXIST),
                status=HTTPStatus.OK,
            )
        ],
    )
    stonegate.join()

    assert stonegate.identifier == {"merchant_identifier": "sample string 6", "card_number": "sample string 6"}
    mock_authenticate.assert_called()
    mock_signal.assert_called_with("join-success")


@httpretty.activate
@mock.patch("app.agents.stonegate.Stonegate.handle_error_codes")
@mock.patch("app.agents.stonegate.Stonegate.authenticate")
@mock.patch("app.agents.stonegate.signal", autospec=True)
def test_create_account_already_exists(mock_signal, mock_authenticate, mock_handle_error, stonegate):
    details_url = urljoin(stonegate.base_url, "api/Customer/FindCustomerDetails")
    httpretty.register_uri(
        httpretty.POST,
        uri=details_url,
        status=HTTPStatus.OK,
        responses=[
            httpretty.Response(
                body=json.dumps(RESPONSE_DATA_ACCOUNT_EXISTS),
                status=HTTPStatus.OK,
            )
        ],
    )
    with pytest.raises(AccountAlreadyExistsError):
        stonegate.join()
        mock_signal.assert_called_with("join-fail")


@httpretty.activate
@mock.patch("app.agents.stonegate.Stonegate.handle_error_codes")
@mock.patch("app.agents.stonegate.Stonegate.authenticate")
@mock.patch("app.agents.stonegate.signal", autospec=True)
def test_create_account_fails_generic_exception(mock_signal, mock_authenticate, mock_handle_error, stonegate):
    details_url = urljoin(stonegate.base_url, "api/Customer/FindCustomerDetails")
    httpretty.register_uri(
        httpretty.POST,
        uri=details_url,
        status=HTTPStatus.OK,
        responses=[
            httpretty.Response(
                body=json.dumps(RESPONSE_DATA_ERROR),
                status=HTTPStatus.OK,
            )
        ],
    )
    with pytest.raises(JoinError):
        stonegate.join()
        mock_signal.assert_called_with("join-fail")


@httpretty.activate
@mock.patch("app.agents.stonegate.Stonegate.handle_error_codes")
@mock.patch("app.agents.stonegate.Stonegate.authenticate")
@mock.patch("app.agents.stonegate.signal", autospec=True)
def test_create_account_no_member_number_returned(mock_signal, mock_authenticate, mock_handle_error, stonegate):
    details_url = urljoin(stonegate.base_url, "api/Customer/FindCustomerDetails")
    export_url = urljoin(stonegate.base_url, "api/Customer/Post")
    httpretty.register_uri(
        httpretty.POST,
        uri=details_url,
        status=HTTPStatus.OK,
        responses=[
            httpretty.Response(
                body=json.dumps(RESPONSE_DATA_ACCOUNT_NOT_EXIST),
                status=HTTPStatus.OK,
            )
        ],
    )
    httpretty.register_uri(
        httpretty.POST,
        uri=export_url,
        status=HTTPStatus.OK,
        responses=[
            httpretty.Response(
                body=json.dumps(RESPONSE_DATA_NO_MEMBER_NUMBER),
                status=HTTPStatus.OK,
            )
        ],
    )
    with pytest.raises(JoinError):
        stonegate.join()
        mock_signal.assert_called_with("join-fail")


@mock.patch("app.agents.stonegate.Stonegate.authenticate")
@mock.patch("app.agents.stonegate.signal", autospec=True)
def test_get_payload_when_consents_is_true(mock_signal, mock_authenticate, stonegate):
    stonegate.credentials = {
        "first_name": "Fake",
        "last_name": "Name",
        "email": "email@domain.com",
        "password": "pAsSw0rD",
        "consents": [{"id": 11738, "slug": "Subscription", "value": True, "created_on": "1996-09-26T00:00:00"}],
    }
    payload = stonegate._get_join_payload()
    assert payload["MarketingOptin"]["EmailOptin"] is True


@mock.patch("app.agents.stonegate.Stonegate.authenticate")
@mock.patch("app.agents.stonegate.signal", autospec=True)
def test_get_payload_when_consents_is_false(mock_signal, mock_authenticate, stonegate):
    stonegate.credentials = {
        "first_name": "Fake",
        "last_name": "Name",
        "email": "email@domain.com",
        "password": "pAsSw0rD",
        "consents": [{"id": 11738, "slug": "Subscription", "value": False, "created_on": "1996-09-26T00:00:00"}],
    }
    payload = stonegate._get_join_payload()
    assert payload["MarketingOptin"]["EmailOptin"] is False
