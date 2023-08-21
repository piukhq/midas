import json
import uuid
from http import HTTPStatus
from unittest.mock import call, patch

import httpretty
import pytest
from soteria.configuration import Configuration

from app import db
from app.agents.itsu import Itsu
from app.db import redis_raw
from app.exceptions import (
    # AccountAlreadyExistsError,; BaseError,; ConfigurationError,;
    # JoinError,; PreRegisteredCardError,; ServiceConnectionError,; UnknownError,
    EndSiteDownError,
    IPBlockedError,
    NotSentError,
    ResourceNotFoundError,
    RetryLimitReachedError,
    StatusLoginFailedError,
)
from app.retry_util import create_task, enqueue_retry_task
from app.scheme_account import JourneyTypes, SchemeAccountStatus

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

USER_INFO = {
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

MESSAGE = {
    "loyalty_plan": "itsu",
    "message_uid": "32799979732e2",
    "request_id": "234",
    "bink_user_id": "34567",
    "transaction_id": str(uuid.uuid1()),
}


@pytest.fixture
@httpretty.activate
def itsu():
    mock_europa_url = "http://mock_europa.com"
    with patch("settings.CONFIG_SERVICE_URL", mock_europa_url):
        uri = f"{mock_europa_url}/configuration"
        httpretty.register_uri(
            httpretty.GET,
            uri=uri,
            status=HTTPStatus.OK,
            body=json.dumps(CONFIG_JSON_ITSU_BODY),
            content_type="text/json",
        )
        with patch("app.agents.base.Configuration.get_security_credentials", return_value=SECRET_ITSU_ACTEOL_JOIN):
            return Itsu(5, USER_INFO, scheme_slug="itsu")


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
@patch("app.agents.base.signal", autospec=True)
def pepper_id(mock_base_signal, pepper_base_url, itsu):
    api_url = f"{pepper_base_url}/users?autoActivate=true"
    httpretty.register_uri(
        httpretty.POST,
        uri=api_url,
        status=HTTPStatus.OK,
        body=json.dumps({"id": EXPECTED_PEPPER_ID}),
        content_type="text/json",
    )
    returned_pepper_id = itsu.pepper_add_user(pepper_base_url)
    assert mock_base_signal.call_count == 3
    return returned_pepper_id


class TestItsuPepperHappyPath:
    def mock_set_pepper_base_url(self):
        return PEPPER_MERCHANT_URL

    def mock_pepper_add_user(self, _):
        return EXPECTED_PEPPER_ID

    def test_get_by_id(self, itsu):
        payload = itsu.pepper_add_user_payload()
        assert payload == EXPECTED_PEPPER_PAYLOAD
        assert itsu.headers == {}

    def test_overlay_pepper_config(self, pepper_base_url, itsu):
        assert pepper_base_url == PEPPER_MERCHANT_URL
        payload = itsu.pepper_add_user_payload()
        assert payload == EXPECTED_PEPPER_PAYLOAD
        assert itsu.scheme_slug == "itsu"
        assert itsu.headers == EXPECTED_ITSU_PEPPER_HEADERS

    @httpretty.activate
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_add_user(self, mock_base_signal, itsu):
        api_url = f"{PEPPER_MERCHANT_URL}/users?autoActivate=true"
        httpretty.register_uri(
            httpretty.POST,
            uri=api_url,
            status=HTTPStatus.OK,
            body=json.dumps({"id": EXPECTED_PEPPER_ID}),
            content_type="text/json",
        )
        returned_pepper_id = itsu.pepper_add_user(PEPPER_MERCHANT_URL)
        assert returned_pepper_id == EXPECTED_PEPPER_ID
        assert mock_base_signal.call_count == 3

    @httpretty.activate
    @patch("app.agents.base.signal", autospec=True)
    def test_call_pepper_for_card_number(self, mock_base_signal, pepper_id, pepper_base_url, itsu):
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

    @httpretty.activate
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_join(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with patch("app.agents.itsu.Itsu.set_pepper_config", self.mock_set_pepper_base_url):
            with patch("app.agents.itsu.Itsu.pepper_add_user", self.mock_pepper_add_user):
                api_url = f"{pepper_base_url}/users/{pepper_id}/loyalty"
                httpretty.register_uri(
                    httpretty.POST,
                    uri=api_url,
                    status=HTTPStatus.OK,
                    body=json.dumps({"externalLoyaltyMemberNumber": EXPECTED_CARD_NUMBER}),
                    content_type="text/json",
                )

                itsu.join()
                expected_calls = [  # The expected call stack for signal, in order
                    call("join-success"),
                    call().send(itsu, slug=itsu.scheme_slug, channel="test"),
                ]
                mock_signal.assert_has_calls(expected_calls)
                assert mock_base_signal.call_count == 3


class TestItsuPepperAddUserErrors:
    @httpretty.activate
    def call_pepper_add_user(self, status_error: HTTPStatus, pepper_base_url, itsu: Itsu, response_body=None) -> str:
        if not response_body:
            response_body = {"id": EXPECTED_PEPPER_ID}
        api_url = f"{pepper_base_url}/users?autoActivate=true"
        httpretty.register_uri(
            httpretty.POST,
            uri=api_url,
            status=status_error,
            body=json.dumps(response_body),
            content_type="text/json",
        )
        return itsu.pepper_add_user(pepper_base_url)

    def set_mock_retry(self):
        credentials = USER_INFO["credentials"]
        user_info = {
            "user_set": MESSAGE["bink_user_id"],
            "bink_user_id": MESSAGE["bink_user_id"],
            "credentials": credentials,
            "status": SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,  # TODO: check where/how this is used
            "journey_type": JourneyTypes.JOIN.value,
            "scheme_account_id": int(USER_INFO["scheme_account_id"]),
            "channel": USER_INFO["channel"],
        }
        with db.session_scope() as session:
            task = create_task(
                db_session=session,
                user_info=user_info,
                journey_type="attempt-join",
                message_uid=MESSAGE["transaction_id"],
                scheme_identifier=MESSAGE["loyalty_plan"],
                scheme_account_id=MESSAGE["request_id"],
            )
            enqueue_retry_task(connection=redis_raw, retry_task=task)
            session.commit()

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_add_user_422(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        self.call_pepper_add_user(HTTPStatus.UNPROCESSABLE_ENTITY, pepper_base_url, itsu)
        assert mock_base_signal.call_count == 4
        assert mock_signal.call_count == 0

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_add_user_504(self, mock_base_signal, mock_signal, pepper_base_url, itsu):
        with pytest.raises(RetryLimitReachedError):
            self.call_pepper_add_user(HTTPStatus.GATEWAY_TIMEOUT, pepper_base_url, itsu)
        assert mock_base_signal.call_count == 2
        assert mock_signal.call_count == 0

    @httpretty.activate
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_add_user_503(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(NotSentError):
            self.call_pepper_add_user(HTTPStatus.SERVICE_UNAVAILABLE, pepper_base_url, itsu)
        assert mock_base_signal.call_count == 4
        assert mock_signal.call_count == 0


class TestItsuPepperCardNumberErrors:
    @httpretty.activate
    def call_pepper_for_card_number(self, status_error: HTTPStatus, pepper_id, pepper_base_url, itsu: Itsu) -> str:
        api_url = f"{pepper_base_url}/users/{pepper_id}/loyalty"
        httpretty.register_uri(
            httpretty.POST,
            uri=api_url,
            status=status_error,
            body=json.dumps({"externalLoyaltyMemberNumber": EXPECTED_CARD_NUMBER}),
            content_type="text/json",
        )
        return itsu.call_pepper_for_card_number(pepper_id, pepper_base_url)

    @httpretty.activate
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_403(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(IPBlockedError):
            self.call_pepper_for_card_number(HTTPStatus.FORBIDDEN, pepper_id, pepper_base_url, itsu)
        assert mock_base_signal.call_count == 4
        assert mock_signal.call_count == 0

    @httpretty.activate
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_404(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(ResourceNotFoundError):
            self.call_pepper_for_card_number(HTTPStatus.NOT_FOUND, pepper_id, pepper_base_url, itsu)
        assert mock_base_signal.call_count == 4
        assert mock_signal.call_count == 0

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_408(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(EndSiteDownError):
            self.call_pepper_for_card_number(HTTPStatus.REQUEST_TIMEOUT, pepper_id, pepper_base_url, itsu)
            assert mock_base_signal.call_count == 4
            assert mock_signal.call_count == 0

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_422(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(EndSiteDownError):
            self.call_pepper_for_card_number(HTTPStatus.UNPROCESSABLE_ENTITY, pepper_id, pepper_base_url, itsu)
            assert mock_base_signal.call_count == 4
            assert mock_signal.call_count == 0

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_400(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(EndSiteDownError):
            self.call_pepper_for_card_number(HTTPStatus.BAD_REQUEST, pepper_id, pepper_base_url, itsu)
            assert mock_base_signal.call_count == 4
            assert mock_signal.call_count == 0

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_401(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(StatusLoginFailedError):
            self.call_pepper_for_card_number(HTTPStatus.UNAUTHORIZED, pepper_id, pepper_base_url, itsu)
            assert mock_base_signal.call_count == 4
            assert mock_signal.call_count == 0

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_504(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(RetryLimitReachedError):
            self.call_pepper_for_card_number(HTTPStatus.GATEWAY_TIMEOUT, pepper_id, pepper_base_url, itsu)
        assert mock_base_signal.call_count == 2
        assert mock_signal.call_count == 0

    @httpretty.activate
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_503(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(NotSentError):
            self.call_pepper_for_card_number(HTTPStatus.SERVICE_UNAVAILABLE, pepper_id, pepper_base_url, itsu)
        assert mock_base_signal.call_count == 4
        assert mock_signal.call_count == 0

    @httpretty.activate
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.base.signal", autospec=True)
    def test_pepper_card_number_500(self, mock_base_signal, mock_signal, pepper_id, pepper_base_url, itsu):
        with pytest.raises(RetryLimitReachedError):
            self.call_pepper_for_card_number(HTTPStatus.INTERNAL_SERVER_ERROR, pepper_id, pepper_base_url, itsu)
        assert mock_base_signal.call_count == 2
        assert mock_signal.call_count == 0
