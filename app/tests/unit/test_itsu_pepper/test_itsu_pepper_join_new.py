from http import HTTPStatus

import httpretty
import pytest
from soteria.configuration import Configuration

from app.exceptions import EndSiteDownError, RetryLimitReachedError, NotSentError

from .setup_data import (
    CONFIG_JSON_PEPPER_BODY,
    EXPECTED_CARD_NUMBER,
    EXPECTED_ITSU_PEPPER_HEADERS,
    EXPECTED_PEPPER_ID,
    EXPECTED_PEPPER_PAYLOAD,
    MESSAGE,
    PEPPER_MERCHANT_URL,
    SECRET_ITSU_PEPPER_JOIN,
)

"""
fixture itsu is an instantiated Itsu using Mock add user from a mock join
fixture itsu_pepper is for internal join testing as it is another itsu instance configured for itsu and then pepper
"""


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
        mock_pepper_user_request(response={"id": EXPECTED_PEPPER_ID})
        returned_pepper_id = itsu_pepper.pepper_add_user(PEPPER_MERCHANT_URL)
        assert returned_pepper_id == EXPECTED_PEPPER_ID
        assert mock_itsu_signals.call_count == 3
        assert mock_itsu_signals.has("send-audit-request")
        assert mock_itsu_signals.has("send-audit-response")
        assert mock_itsu_signals.has("record-http-request")

    @httpretty.activate
    def test_call_pepper_for_card_number(self, mock_itsu_signals, itsu_pepper, mock_pepper_loyalty_request):
        mock_pepper_loyalty_request(EXPECTED_PEPPER_ID, response={"externalLoyaltyMemberNumber": EXPECTED_CARD_NUMBER})
        card_number = itsu_pepper.call_pepper_for_card_number(EXPECTED_PEPPER_ID, PEPPER_MERCHANT_URL)
        assert card_number == EXPECTED_CARD_NUMBER
        assert mock_itsu_signals.call_count == 3
        assert mock_itsu_signals.has("send-audit-request")
        assert mock_itsu_signals.has("send-audit-response")
        assert mock_itsu_signals.has("record-http-request")

    @httpretty.activate
    def test_join(self, mock_itsu_signals, itsu_pepper, mock_pepper_loyalty_request, monkeypatch):
        mock_pepper_loyalty_request(EXPECTED_PEPPER_ID, response={"externalLoyaltyMemberNumber": EXPECTED_CARD_NUMBER})
        with monkeypatch.context() as m:
            m.setattr(itsu_pepper, "set_pepper_config", lambda *_: PEPPER_MERCHANT_URL)
            m.setattr(itsu_pepper, "pepper_add_user", lambda *_: EXPECTED_PEPPER_ID)
            itsu_pepper.join()

        assert itsu_pepper.headers == EXPECTED_ITSU_PEPPER_HEADERS
        assert mock_itsu_signals.has("join-success")
        assert mock_itsu_signals.has("join-fail") is False

        args, kwargs = mock_itsu_signals.get("join-success")
        assert args[0] == itsu_pepper
        assert kwargs == {"channel": "test", "slug": itsu_pepper.scheme_slug}
        assert mock_itsu_signals.call_count == 4


class TestItsuJoinErrors:

    @httpretty.activate
    @pytest.mark.parametrize(
        "test,status,response, raises,call_count",
        [
            ("504", HTTPStatus.GATEWAY_TIMEOUT, {}, RetryLimitReachedError, 2),
            ("503", HTTPStatus.SERVICE_UNAVAILABLE, {}, NotSentError, 4),
        ],
    )
    def test_pepper_add_user_errors(
        self, mock_pepper_user_request, itsu_pepper, mock_itsu_signals, test, status, response, raises, call_count
    ):
        mock_pepper_user_request(status=status, response=response)
        with pytest.raises(raises):
            itsu_pepper.pepper_add_user(PEPPER_MERCHANT_URL)
        assert mock_itsu_signals.call_count == call_count

    @httpretty.activate
    @pytest.mark.parametrize(
        "test,status,response, raises,call_count",
        [
            ("422", HTTPStatus.UNPROCESSABLE_ENTITY, {}, EndSiteDownError, 4),
            ("504", HTTPStatus.GATEWAY_TIMEOUT, {}, RetryLimitReachedError, 2),
            ("503", HTTPStatus.SERVICE_UNAVAILABLE, {}, NotSentError, 4),
        ],
    )
    def test_pepper_card_number_errors(
        self, mock_pepper_loyalty_request, itsu_pepper, mock_itsu_signals, test, status, response, raises, call_count
    ):
        mock_pepper_loyalty_request(status=status, response=response)
        with pytest.raises(raises):
            itsu_pepper.call_pepper_for_card_number(EXPECTED_PEPPER_ID, PEPPER_MERCHANT_URL)
        assert mock_itsu_signals.call_count == call_count
