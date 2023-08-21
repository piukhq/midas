from http import HTTPStatus

import httpretty
import pytest
from soteria.configuration import Configuration

from app.exceptions import (
    EndSiteDownError,
    JoinError,
    NotSentError,
    RetryLimitReachedError,
    IPBlockedError,
    ResourceNotFoundError,
    StatusLoginFailedError,


)
from .setup_data import (
    CONFIG_JSON_PEPPER_BODY,
    EXPECTED_ACCOUNT_SETUP_RESPONSE_NO_USER_NUMBER,
    EXPECTED_ACCOUNT_SETUP_RESPONSE_WITH_USER_NUMBER,
    EXPECTED_CARD_NUMBER,
    EXPECTED_CARD_NUMBER_RESPONSE,
    EXPECTED_ITSU_PEPPER_HEADERS,
    EXPECTED_PEPPER_ID,
    EXPECTED_PEPPER_PAYLOAD,
    EXPECTED_USER_LOOKUP_RESPONSE,
    MESSAGE,
    PEPPER_MERCHANT_URL,
    SECRET_ITSU_PEPPER_JOIN,
    USER_EMAIL,
)

"""
fixture itsu is an instantiated Itsu using Mock add user from a mock join
fixture itsu_pepper is for internal join testing as it is another itsu instance configured for itsu and then pepper
"""

AUDIT_RESPONSE_REQUEST_FAIL = ["send-audit-request", "send-audit-response", "record-http-request", "request-fail"]
AUDIT_RESPONSE_REQUEST = ["send-audit-request", "send-audit-response", "record-http-request"]
AUDIT_REQUEST_REQUEST_FAIL = ["send-audit-request", "request-fail"]


class TestItsuPepperJoinHappyPath:
    def test_overlay_pepper_config(self, itsu_pepper, itsu):
        payload = itsu_pepper.pepper_add_user_payload()
        assert payload == EXPECTED_PEPPER_PAYLOAD
        assert itsu_pepper.scheme_slug == MESSAGE["loyalty_plan"]
        assert itsu_pepper.headers == EXPECTED_ITSU_PEPPER_HEADERS
        assert itsu.headers == {}

    @pytest.fixture
    @httpretty.activate
    def pepper_base_url(monkeypatch, itsu_pepper, mock_europa_request):
        monkeypatch.setattr(Configuration, "get_security_credentials", lambda *_: SECRET_ITSU_PEPPER_JOIN)
        mock_europa_request(response=CONFIG_JSON_PEPPER_BODY)
        pepper_base_url = itsu_pepper.set_pepper_config()
        assert pepper_base_url == PEPPER_MERCHANT_URL

    @httpretty.activate
    def test_pepper_add_user(self, mock_itsu_signals, itsu_pepper, mock_pepper_user_request):
        mock_pepper_user_request(response=EXPECTED_ACCOUNT_SETUP_RESPONSE_WITH_USER_NUMBER)
        returned_pepper_id, card_number = itsu_pepper.pepper_add_user(PEPPER_MERCHANT_URL)
        assert returned_pepper_id == EXPECTED_PEPPER_ID
        assert card_number == EXPECTED_CARD_NUMBER
        assert mock_itsu_signals.name_list == AUDIT_RESPONSE_REQUEST

    @httpretty.activate
    def test_pepper_add_user_no_card(self, mock_itsu_signals, itsu_pepper, mock_pepper_user_request):
        mock_pepper_user_request(response=EXPECTED_ACCOUNT_SETUP_RESPONSE_NO_USER_NUMBER)
        returned_pepper_id, card_number = itsu_pepper.pepper_add_user(PEPPER_MERCHANT_URL)
        assert returned_pepper_id == EXPECTED_PEPPER_ID
        assert card_number == ""
        assert mock_itsu_signals.name_list == AUDIT_RESPONSE_REQUEST

    @httpretty.activate
    def test_pepper_get_user_by_id(self, mock_itsu_signals, itsu_pepper, mock_pepper_get_user_by_id_request):
        mock_pepper_get_user_by_id_request(response=EXPECTED_USER_LOOKUP_RESPONSE)
        returned_pepper_id = itsu_pepper.pepper_get_by_id(USER_EMAIL, PEPPER_MERCHANT_URL)
        assert returned_pepper_id == EXPECTED_PEPPER_ID
        assert mock_itsu_signals.count == 1
        assert mock_itsu_signals.has("record-http-request")

    @httpretty.activate
    def test_call_pepper_for_card_number(self, mock_itsu_signals, itsu_pepper, mock_pepper_loyalty_request):
        mock_pepper_loyalty_request(EXPECTED_PEPPER_ID, response=EXPECTED_CARD_NUMBER_RESPONSE)
        card_number = itsu_pepper.call_pepper_for_card_number(EXPECTED_PEPPER_ID, PEPPER_MERCHANT_URL)
        assert card_number == EXPECTED_CARD_NUMBER
        assert mock_itsu_signals.name_list == AUDIT_RESPONSE_REQUEST

    @httpretty.activate
    def test_join(self, mock_itsu_signals, itsu_pepper, mock_pepper_loyalty_request, monkeypatch):
        mock_pepper_loyalty_request(EXPECTED_PEPPER_ID, response=EXPECTED_CARD_NUMBER_RESPONSE)
        with monkeypatch.context() as m:
            m.setattr(itsu_pepper, "set_pepper_config", lambda *_: PEPPER_MERCHANT_URL)
            m.setattr(itsu_pepper, "pepper_add_user", lambda *_: (EXPECTED_PEPPER_ID, EXPECTED_CARD_NUMBER))
            itsu_pepper.join()

        assert itsu_pepper.headers == EXPECTED_ITSU_PEPPER_HEADERS
        assert mock_itsu_signals.count == 1
        assert mock_itsu_signals.has("join-success")

        args, kwargs = mock_itsu_signals.get("join-success")
        assert args[0] == itsu_pepper
        assert kwargs == {"channel": "test", "slug": itsu_pepper.scheme_slug}

        assert itsu_pepper.identifier_type == ["card_number"]
        assert itsu_pepper.identifier == {
            "card_number": EXPECTED_CARD_NUMBER,
            "merchant_identifier": EXPECTED_PEPPER_ID,
        }
        assert itsu_pepper.credentials["card_number"] == EXPECTED_CARD_NUMBER
        assert itsu_pepper.credentials["merchant_identifier"] == EXPECTED_PEPPER_ID

    @httpretty.activate
    def test_join_user_request_returns_no_card(
        self, mock_itsu_signals, itsu_pepper, mock_pepper_loyalty_request, monkeypatch
    ):
        mock_pepper_loyalty_request(EXPECTED_PEPPER_ID, response=EXPECTED_CARD_NUMBER_RESPONSE)
        with monkeypatch.context() as m:
            m.setattr(itsu_pepper, "set_pepper_config", lambda *_: PEPPER_MERCHANT_URL)
            m.setattr(itsu_pepper, "pepper_add_user", lambda *_: (EXPECTED_PEPPER_ID, ""))
            itsu_pepper.join()

        assert itsu_pepper.headers == EXPECTED_ITSU_PEPPER_HEADERS
        assert mock_itsu_signals.name_list == [
            "send-audit-request",
            "send-audit-response",
            "record-http-request",
            "join-success",
        ]
        args, kwargs = mock_itsu_signals.get("join-success")
        assert args[0] == itsu_pepper
        assert kwargs == {"channel": "test", "slug": itsu_pepper.scheme_slug}

        assert itsu_pepper.identifier_type == ["card_number"]
        assert itsu_pepper.identifier == {
            "card_number": EXPECTED_CARD_NUMBER,
            "merchant_identifier": EXPECTED_PEPPER_ID,
        }
        assert itsu_pepper.credentials["card_number"] == EXPECTED_CARD_NUMBER
        assert itsu_pepper.credentials["merchant_identifier"] == EXPECTED_PEPPER_ID


class TestItsuJoinErrors:
    @httpretty.activate
    @pytest.mark.parametrize(
        "test, status, response, raises, signals",
        [
            ("400", HTTPStatus.BAD_REQUEST, {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("401", HTTPStatus.UNAUTHORIZED, {}, StatusLoginFailedError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("403", HTTPStatus.FORBIDDEN, {}, IPBlockedError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("404", HTTPStatus.NOT_FOUND, {}, ResourceNotFoundError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("408", HTTPStatus.REQUEST_TIMEOUT, {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("409", HTTPStatus.CONFLICT, {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("429", HTTPStatus.TOO_MANY_REQUESTS, {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("500", HTTPStatus.INTERNAL_SERVER_ERROR, {}, RetryLimitReachedError, AUDIT_REQUEST_REQUEST_FAIL),
            ("502", HTTPStatus.BAD_GATEWAY, {}, RetryLimitReachedError, AUDIT_REQUEST_REQUEST_FAIL),
            ("503", HTTPStatus.SERVICE_UNAVAILABLE, {}, NotSentError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("504", HTTPStatus.GATEWAY_TIMEOUT, {}, RetryLimitReachedError, AUDIT_REQUEST_REQUEST_FAIL),
        ],
    )
    def test_pepper_add_user_errors(
        self, mock_pepper_user_request, itsu_pepper, mock_itsu_signals, test, status, response, raises, signals
    ):
        mock_pepper_user_request(status=status, response=response)
        with pytest.raises(raises):
            itsu_pepper.pepper_add_user(PEPPER_MERCHANT_URL)
        assert mock_itsu_signals.name_list == signals

    @httpretty.activate
    @pytest.mark.parametrize(
        "test, status, response, raises, signals",
        [
            ("400", HTTPStatus.BAD_REQUEST, {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("401", HTTPStatus.UNAUTHORIZED, {}, StatusLoginFailedError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("403", HTTPStatus.FORBIDDEN, {}, IPBlockedError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("404", HTTPStatus.NOT_FOUND, {}, ResourceNotFoundError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("408", HTTPStatus.REQUEST_TIMEOUT,  {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("409", HTTPStatus.CONFLICT, {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("422", HTTPStatus.UNPROCESSABLE_ENTITY, {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("429", HTTPStatus.TOO_MANY_REQUESTS, {}, EndSiteDownError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("500", HTTPStatus.INTERNAL_SERVER_ERROR, {}, RetryLimitReachedError, AUDIT_REQUEST_REQUEST_FAIL),
            ("502", HTTPStatus.BAD_GATEWAY, {}, RetryLimitReachedError, AUDIT_REQUEST_REQUEST_FAIL),
            ("503", HTTPStatus.SERVICE_UNAVAILABLE, {}, NotSentError, AUDIT_RESPONSE_REQUEST_FAIL),
            ("504", HTTPStatus.GATEWAY_TIMEOUT, {}, RetryLimitReachedError, AUDIT_REQUEST_REQUEST_FAIL),
        ],
    )
    def test_pepper_card_number_errors(
        self, mock_pepper_loyalty_request, itsu_pepper, mock_itsu_signals, test, status, response, raises, signals
    ):
        mock_pepper_loyalty_request(status=status, response=response)
        with pytest.raises(raises):
            itsu_pepper.call_pepper_for_card_number(EXPECTED_PEPPER_ID, PEPPER_MERCHANT_URL)
        assert mock_itsu_signals.name_list == signals

    @httpretty.activate
    def test_join_user_request_returns_no_id_or_card(
        self, mock_itsu_signals, itsu_pepper, mock_pepper_loyalty_request, monkeypatch
    ):
        mock_pepper_loyalty_request(EXPECTED_PEPPER_ID, response=EXPECTED_CARD_NUMBER_RESPONSE)
        with monkeypatch.context() as m:
            m.setattr(itsu_pepper, "set_pepper_config", lambda *_: PEPPER_MERCHANT_URL)
            m.setattr(itsu_pepper, "pepper_add_user", lambda *_: ("", ""))
            with pytest.raises(JoinError):
                itsu_pepper.join()
        assert mock_itsu_signals.name_list == ["join-fail"]
        args, kwargs = mock_itsu_signals.get("join-fail")
        assert args[0] == itsu_pepper
        assert kwargs == {"channel": "test", "error": JoinError, "slug": itsu_pepper.scheme_slug}
