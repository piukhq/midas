import json
from decimal import Decimal
from http import HTTPStatus
from unittest import TestCase, mock
from unittest.mock import ANY, MagicMock, Mock, call

import arrow
import httpretty
import requests
from flask_testing import TestCase as FlaskTestCase
from requests import Response
from soteria.configuration import Configuration

from app.agents.base import Balance, BaseAgent
from app.agents.iceland import Iceland
from app.agents.schemas import Transaction
from app.api import create_app
from app.exceptions import (
    AccountAlreadyExistsError,
    CardNotRegisteredError,
    CardNumberError,
    ConfigurationError,
    GeneralError,
    JoinError,
    JoinInProgressError,
    LinkLimitExceededError,
    NoSuchRecordError,
    NotSentError,
    ServiceConnectionError,
    StatusLoginFailedError,
    UnknownError,
)
from app.journeys.common import agent_login
from app.journeys.join import agent_join
from app.models import RetryTaskStatuses
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES, JourneyTypes, SchemeAccountStatus
from app.security.rsa import RSA
from app.tasks.resend_consents import ConsentStatus
from app.tests.unit.fixtures.rsa_keys import PRIVATE_KEY, PUBLIC_KEY


class TestIceland(TestCase):
    def setUp(self) -> None:
        self.credentials = {
            "card_number": "0000000000000000000",
            "last_name": "Smith",
            "postcode": "XX0 0XX",
        }
        self.merchant_url = "https://reflector.dev.gb.bink.com/api/v1/bink/link"
        self.token_url = "https://reflector.dev.gb.bink.com/mock/oauth2/token"

        mock_configuration_object = MagicMock()
        mock_configuration_object.security_credentials = {
            "inbound": {"service": Configuration.OPEN_AUTH_SECURITY, "credentials": []},
            "outbound": {
                "service": Configuration.OAUTH_SECURITY,
                "credentials": [
                    {
                        "credential_type": "compound_key",
                        "storage_key": "a_storage_key",
                        "value": {
                            "payload": {
                                "client_id": "a_client_id",
                                "client_secret": "a_client_secret",
                                "grant_type": "client_credentials",
                                "resource": "a_resource",
                            },
                            "prefix": "Bearer",
                            "url": self.token_url,
                        },
                    }
                ],
            },
        }
        mock_configuration_object.merchant_url = self.merchant_url
        mock_configuration_object.callback_url = None

        with mock.patch("app.agents.base.Configuration", return_value=mock_configuration_object):
            self.iceland = Iceland(
                retry_count=1,
                user_info={
                    "scheme_account_id": 1,
                    "status": SchemeAccountStatus.WALLET_ONLY,
                    "journey_type": JourneyTypes.LINK.value,
                    "user_set": "1,2",
                    "credentials": self.credentials,
                },
                scheme_slug="iceland-bonus-card",
            )

    def test_get_oauth_url_and_payload(self):
        url, payload = self.iceland.get_auth_url_and_payload()
        self.assertEqual("https://reflector.dev.gb.bink.com/mock/oauth2/token", url)
        self.assertEqual(
            {
                "client_id": "a_client_id",
                "client_secret": "a_client_secret",
                "grant_type": "client_credentials",
                "resource": "a_resource",
            },
            payload,
        )

    @httpretty.activate
    def test_refresh_token(self):
        httpretty.register_uri(
            httpretty.POST,
            self.token_url,
            responses=[httpretty.Response(body=json.dumps({"access_token": "a_token"}), status=200)],
        )

        self.assertEqual(self.iceland._refresh_token(), "a_token")

    def test_token_is_valid_true(self):
        token = {
            "iceland_access_token": "abcde12345fghij",
            "timestamp": arrow.get(2022, 1, 1, 7, 0).int_timestamp,
        }

        result = self.iceland._token_is_valid(token, arrow.get(2022, 1, 1, 7, 30).int_timestamp)

        self.assertEqual(
            result,
            True,
        )

    def test_token_is_valid_false(self):
        token = {
            "iceland_bonus_card_access_token": "abcde12345fghij",
            "timestamp": arrow.get(2022, 1, 1, 7, 0).int_timestamp,
        }

        result = self.iceland._token_is_valid(token, arrow.get(2022, 1, 1, 8, 0).int_timestamp)

        self.assertEqual(
            result,
            False,
        )

    def test_store_token(self):
        access_token = "abcde12345fghij"
        current_timestamp = arrow.get(2022, 1, 1, 7, 0).int_timestamp

        with mock.patch.object(self.iceland.token_store, "set", return_value=True) as mock_token_store:
            self.iceland._store_token(access_token, current_timestamp)

        self.assertEqual(
            mock_token_store.call_args[1]["token"],
            '{"iceland_bonus_card_access_token": "abcde12345fghij", "timestamp": 1641020400}',
        )

    def test_authenticate_stored_token_valid(self):
        with mock.patch.object(
            self.iceland.token_store,
            "get",
            return_value=json.dumps(
                {"iceland_bonus_card_access_token": "abcde12345fghij", "timestamp": arrow.utcnow().int_timestamp}
            ),
        ):
            self.iceland.authenticate()
        self.assertEqual({"Authorization": "Bearer abcde12345fghij"}, self.iceland.headers)

    @mock.patch("app.agents.iceland.Iceland._refresh_token", return_value="")
    def test_authenticate_with_expired_stored_token(self, mock_refresh_token):
        self.iceland.token_store = MagicMock()
        self.iceland.token_store.get.return_value = (
            f'{{"iceland_bonus_card_access_token": "abcde12345fghij", '
            f'"timestamp": {arrow.utcnow().int_timestamp-3600}}}'
        )
        self.iceland.authenticate()
        mock_refresh_token.assert_called()

    def test_balance(self):
        self.iceland._balance_amount = amount = Decimal(10.0).quantize(TWO_PLACES)
        expected_result = Balance(
            points=amount,
            value=amount,
            value_label="£{}".format(amount),
        )

        self.assertEqual(self.iceland.balance(), expected_result)

    def test_transactions_if_existing(self):
        self.iceland._transactions = [
            {"timestamp": "2021-03-24T03:29:20", "reference": "DEBIT", "value": -2.0, "unit": "GBP"},
            {"timestamp": "2021-02-15T23:02:47", "reference": "CREDIT", "value": 2.0, "unit": "GBP"},
        ]
        expected_result = [
            Transaction(
                date=arrow.get("2021-03-24T03:29:20"),
                description="DEBIT",
                points=Decimal("-2"),
                location=None,
                value=None,
                hash="18daf676b636277c3a8f9b856d3e882f",
            ),
            Transaction(
                date=arrow.get("2021-02-15T23:02:47"),
                description="CREDIT",
                points=Decimal("2"),
                location=None,
                value=None,
                hash="6cc797e6ccaa035bc131eb703cd0f136",
            ),
        ]

        self.assertEqual(self.iceland.transactions(), expected_result)

    def test_transactions_if_None(self):
        self.iceland._transactions = None
        self.assertEqual([], self.iceland.transactions())


class TestIcelandAdd(TestCase):
    def setUp(self) -> None:
        self.credentials = {
            "card_number": "0000000000000000000",
            "last_name": "Smith",
            "postcode": "XX0 0XX",
        }
        self.merchant_url = "https://reflector.dev.gb.bink.com/api/v1/bink/link"
        self.token_url = "https://reflector.dev.gb.bink.com/mock/oauth2/token"

        self.mock_configuration_object = MagicMock()
        self.mock_configuration_object.security_credentials = {
            "inbound": {"service": Configuration.OPEN_AUTH_SECURITY, "credentials": []},
            "outbound": {
                "service": Configuration.OAUTH_SECURITY,
                "credentials": [
                    {
                        "credential_type": "compound_key",
                        "storage_key": "a_storage_key",
                        "value": {
                            "payload": {
                                "client_id": "a_client_id",
                                "client_secret": "a_client_secret",
                                "grant_type": "client_credentials",
                                "resource": "a_resource",
                            },
                            "prefix": "Bearer",
                            "url": self.token_url,
                        },
                    }
                ],
            },
        }
        self.mock_configuration_object.merchant_url = self.merchant_url
        self.mock_configuration_object.callback_url = None

        with mock.patch("app.agents.base.Configuration", return_value=self.mock_configuration_object):
            self.iceland = Iceland(
                retry_count=1,
                user_info={
                    "scheme_account_id": 1,
                    "status": SchemeAccountStatus.WALLET_ONLY,
                    "journey_type": JourneyTypes.LINK.value,
                    "user_set": "1,2",
                    "credentials": self.credentials,
                },
                scheme_slug="iceland-bonus-card",
            )

    @mock.patch("app.redis_retry.redis")
    @mock.patch.object(Iceland, "login")
    def test_agent_login_returns_agent_instance(self, mock_login, mock_retry_redis):
        mock_login.return_value = {"message": "success"}
        user_info = {
            "metadata": {},
            "scheme_slug": "iceland-bonus-card",
            "user_id": "test user id",
            "credentials": {},
            "scheme_account_id": 2,
            "channel": "com.bink.wallet",
            "status": 442,
            "journey_type": 1,
        }

        with mock.patch("app.agents.base.Configuration", return_value=self.mock_configuration_object):
            agent_instance = agent_login(Iceland, user_info, {}, 1)

        self.assertTrue(isinstance(agent_instance, Iceland))
        self.assertTrue(mock_login.called)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_success(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "balance": 10.0,
                            "barcode": "a_barcode",
                            "card_number": "a_card_number",
                            "merchant_scheme_id1": "a_merchant_scheme_id1",
                            "merchant_scheme_id2": "a_merchant_scheme_id2",
                        }
                    ),
                    status=200,
                )
            ],
        )

        self.iceland.login()

        self.assertEqual("SYNC", self.iceland.integration_service)
        self.assertIn("barcode", str(self.iceland.user_info))
        self.assertEqual(10.0, self.iceland._balance_amount)
        self.assertEqual(
            None,
            self.iceland._transactions,
        )
        self.assertEqual(
            {"barcode": "a_barcode", "card_number": "a_card_number", "merchant_identifier": "a_merchant_scheme_id2"},
            self.iceland.identifier,
        )

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_login_does_not_expect_callback(
        self, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oath
    ):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "balance": 10.0,
                            "barcode": "a_barcode",
                            "card_number": "a_card_number",
                            "merchant_scheme_id1": "a_merchant_scheme_id1",
                            "merchant_scheme_id2": "a_merchant_scheme_id2",
                        }
                    ),
                    status=200,
                )
            ],
        )

        self.iceland.login()

        self.assertFalse(self.iceland.expecting_callback)

    def test_login_wrong_authentication_selected(self):
        self.iceland.outbound_auth_service = Configuration.RSA_SECURITY
        with self.assertRaises(ConfigurationError) as e:
            self.iceland.login()
        self.assertEqual("Configuration error", e.exception.name)
        self.assertEqual(
            "Agent expecting Security Type(s) ['Open Auth (No Authentication)', 'OAuth'] "
            "but got Security Type 'RSA' instead",
            e.exception.message,
        )

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.request", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch("app.agents.base.signal", autospec=True)
    @mock.patch.object(BaseAgent, "make_request")
    def test_login_does_not_retry_on_202(
        self, mock_make_request, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oath
    ):
        response = Response()
        response.status_code = 202
        response._content = b'{"balance": 10.0}'
        mock_make_request.return_value = response

        self.iceland.login()

        self.assertEqual(1, mock_make_request.call_count)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_401_unauthorised(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            status=401,
        )

        with self.assertRaises(StatusLoginFailedError) as e:
            self.iceland.login()

        self.assertEqual([e.exception.name, e.exception.code], ["Invalid credentials", 403])

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_validation_error(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "VALIDATION", "description": "Card owner details do not match"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(StatusLoginFailedError) as e:
            self.iceland.login()
        self.assertEqual(e.exception.code, 403)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_card_number_error(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "CARD_NUMBER_ERROR", "description": "Card number not found"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(CardNumberError) as e:
            self.iceland.login()
        self.assertEqual(e.exception.code, 436)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_link_limit_exceeded(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "LINK_LIMIT_EXCEEDED", "description": "Link limit exceeded"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(LinkLimitExceededError) as e:
            self.iceland.login()
        self.assertEqual(e.exception.code, 437)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_card_not_registered(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "error_codes": [
                                {"code": "CARD_NOT_REGISTERED", "description": "Card has not been registered"}
                            ]
                        }
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(CardNotRegisteredError) as e:
            self.iceland.login()
        self.assertEqual(e.exception.code, 438)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_general_error(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "GENERAL_ERROR", "description": "Unspecified exception"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(GeneralError) as e:
            self.iceland.login()
        self.assertEqual(e.exception.code, 439)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_not_sent_error(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps({"error_codes": [{"code": "NOT_SENT", "description": "Message was not sent"}]}),
                    status=200,
                )
            ],
        )

        with self.assertRaises(NotSentError) as e:
            self.iceland.login()
        self.assertEqual(535, e.exception.code)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_unknown_error(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "error_codes": [
                                {"code": "UNKNOWN", "description": "An unknown error has occurred with status code 500"}
                            ]
                        }
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(UnknownError) as e:
            self.iceland.login()
        self.assertEqual(520, e.exception.code)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_no_such_record_error(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "NO_SUCH_RECORD", "description": "Account does not exist"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(NoSuchRecordError) as e:
            self.iceland.login()
        self.assertEqual(444, e.exception.code)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_login_success_signals(self, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oauth):
        httpretty.register_uri(
            httpretty.POST,
            self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )

        self.iceland.login()

        expected_base_calls = [
            call("send-audit-request"),
            call().send(
                self.iceland,
                payload={
                    "card_number": ANY,
                    "last_name": "Smith",
                    "postcode": "XX0 0XX",
                    "message_uid": ANY,
                    "record_uid": ANY,
                    "callback_url": None,
                    "merchant_scheme_id1": ANY,
                    "merchant_scheme_id2": None,
                },
                scheme_slug="iceland-bonus-card",
                handler_type=ANY,
                integration_service="SYNC",
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("send-audit-response"),
            call().send(
                self.iceland,
                response=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=ANY,
                integration_service="SYNC",
                status_code=HTTPStatus.OK,
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("record-http-request"),
            call().send(
                self.iceland,
                slug="iceland-bonus-card",
                endpoint="/api/v1/bink/link",
                latency=ANY,
                response_code=HTTPStatus.OK,
            ),
        ]
        expected_iceland_calls = [
            call("log-in-success"),
            call().send(self.iceland, slug=self.iceland.scheme_slug),
        ]

        self.assertEqual(expected_base_calls, mock_base_signal.mock_calls)
        self.assertEqual(3, mock_base_signal.call_count)
        self.assertEqual(expected_iceland_calls, mock_iceland_signal.mock_calls)
        self.assertEqual(1, mock_iceland_signal.call_count)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_login_error_signals(self, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oauth):
        httpretty.register_uri(
            httpretty.POST,
            self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "VALIDATION", "description": "Card owner details do not match"}]}
                    ),
                    status=200,
                )
            ],
        )

        expected_base_calls = [
            call("send-audit-request"),
            call().send(
                self.iceland,
                payload={
                    "card_number": ANY,
                    "last_name": "Smith",
                    "postcode": "XX0 0XX",
                    "message_uid": ANY,
                    "record_uid": ANY,
                    "callback_url": None,
                    "merchant_scheme_id1": ANY,
                    "merchant_scheme_id2": None,
                },
                scheme_slug="iceland-bonus-card",
                handler_type=ANY,
                integration_service="SYNC",
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("send-audit-response"),
            call().send(
                self.iceland,
                response=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=ANY,
                integration_service="SYNC",
                status_code=HTTPStatus.OK,
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("record-http-request"),
            call().send(
                self.iceland,
                slug="iceland-bonus-card",
                endpoint="/api/v1/bink/link",
                latency=ANY,
                response_code=HTTPStatus.OK,
            ),
        ]
        expected_iceland_calls = [
            call("log-in-fail"),
            call().send(self.iceland, slug=self.iceland.scheme_slug),
        ]

        with self.assertRaises(StatusLoginFailedError):
            self.iceland.login()

        self.assertEqual(expected_base_calls, mock_base_signal.mock_calls[:6])
        self.assertEqual(3, mock_base_signal.call_count)
        self.assertEqual(expected_iceland_calls, mock_iceland_signal.mock_calls[:2])
        self.assertEqual(1, mock_iceland_signal.call_count)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_login_401_failure_signals(self, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oauth):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body="You do not have permission to view this directory or page.", status=401)
            ],
        )

        expected_base_calls = [
            call("send-audit-request"),
            call().send(
                self.iceland,
                payload={
                    "card_number": ANY,
                    "last_name": "Smith",
                    "postcode": "XX0 0XX",
                    "message_uid": ANY,
                    "record_uid": ANY,
                    "callback_url": None,
                    "merchant_scheme_id1": ANY,
                    "merchant_scheme_id2": None,
                },
                scheme_slug="iceland-bonus-card",
                handler_type=Configuration.VALIDATE_HANDLER,
                integration_service="SYNC",
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("send-audit-response"),
            call().send(
                self.iceland,
                response=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=Configuration.VALIDATE_HANDLER,
                integration_service="SYNC",
                status_code=401,
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("record-http-request"),
            call().send(
                self.iceland, slug="iceland-bonus-card", endpoint="/api/v1/bink/link", latency=ANY, response_code=401
            ),
            call("request-fail"),
            call().send(self.iceland, slug="iceland-bonus-card", channel="", error=StatusLoginFailedError),
        ]
        expected_iceland_calls = [
            call("log-in-fail"),
            call().send(
                self.iceland,
                slug=self.iceland.scheme_slug,
            ),
        ]

        with self.assertRaises(StatusLoginFailedError):
            self.iceland.login()

        self.assertEqual(expected_base_calls, mock_base_signal.mock_calls[:8])
        self.assertEqual(4, mock_base_signal.call_count)
        self.assertEqual(expected_iceland_calls, mock_iceland_signal.mock_calls[:2])
        self.assertEqual(1, mock_iceland_signal.call_count)


class TestIcelandJoin(TestCase):
    def setUp(self) -> None:
        self.credentials = {
            "town_city": "a_town",
            "county": "a_county",
            "title": "a_title",
            "address_1": "an_address_1",
            "first_name": "John",
            "last_name": "Smith",
            "date_of_birth": "1987-08-08",
            "email": "ba_test_01@testbink.com",
            "phone": "0790000000",
            "postcode": "XX0 0XX",
            "address_2": "an_address_2",
            "consents": [
                {"id": 1, "slug": "marketing_opt_in", "value": True, "journey_type": JourneyTypes.JOIN.value},
            ],
        }
        self.merchant_url = "https://reflector.dev.gb.bink.com/mock/api/v1/bink/join/"
        self.token_url = "https://reflector.dev.gb.bink.com/mock/"

        self.mock_configuration_object = MagicMock()
        self.mock_configuration_object.security_credentials = {
            "outbound": {
                "service": 0,
                "credentials": [{"storage_key": "", "value": PRIVATE_KEY, "credential_type": "bink_private_key"}],
            },
            "inbound": {
                "service": 0,
                "credentials": [
                    {"storage_key": "", "value": PRIVATE_KEY, "credential_type": "bink_private_key"},
                    {"storage_key": "", "value": PUBLIC_KEY, "credential_type": "merchant_public_key"},
                ],
            },
        }
        self.mock_configuration_object.merchant_url = self.merchant_url
        self.mock_configuration_object.callback_url = None
        self.mock_configuration_object.country = "GB"
        self.mock_configuration_object.integration_service = "ASYNC"
        self.mock_configuration_object.handler_type = Configuration.HANDLER_TYPE_CHOICES[Configuration.JOIN_HANDLER]

        with mock.patch("app.agents.base.Configuration", return_value=self.mock_configuration_object):
            self.iceland = Iceland(
                retry_count=1,
                user_info={
                    "scheme_account_id": 1,
                    "status": SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,
                    "journey_type": JourneyTypes.JOIN.value,
                    "user_set": "1,2",
                    "credentials": self.credentials,
                },
                scheme_slug="iceland-bonus-card",
            )

    @mock.patch.object(Iceland, "join")
    @mock.patch("app.journeys.join.update_pending_join_account", autospec=True)
    def test_attempt_join_returns_agent_instance(self, mock_update_pending_join_account, mock_join):
        mock_join.return_value = {"message": "success"}
        user_info = {
            "metadata": {},
            "scheme_slug": "iceland-bonus-card",
            "user_id": "test user id",
            "credentials": {},
            "scheme_account_id": 2,
            "channel": "com.bink.wallet",
            "status": 442,
            "journey_type": 0,
        }

        with mock.patch("app.agents.base.Configuration", return_value=self.mock_configuration_object):
            join_data = agent_join(Iceland, user_info, {}, 1)
        agent_instance = join_data["agent"]

        self.assertTrue(isinstance(agent_instance, Iceland))
        self.assertTrue(mock_join.called)
        self.assertFalse(mock_update_pending_join_account.called)

    @httpretty.activate
    @mock.patch("app.agents.iceland.get_task", return_value=Mock())
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch("app.agents.base.signal", autospec=True)
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_outbound_success(
        self,
        mock_consent_confirmation,
        mock_base_signal,
        mock_iceland_signal,
        mock_requests_session,
        mock_oath,
        mock_get_task,
    ):
        self.iceland.outbound_auth_service = Configuration.OAUTH_SECURITY
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body=json.dumps({"result": "OK", "message": "Callback requested with delay"}))
            ],
        )

        expected_base_signal_calls = [
            call("send-audit-request"),
            call().send(
                self.iceland,
                payload={
                    "town_city": "a_town",
                    "county": "a_county",
                    "title": "a_title",
                    "address_1": "an_address_1",
                    "first_name": "John",
                    "last_name": "Smith",
                    "email": "ba_test_01@testbink.com",
                    "postcode": "XX0 0XX",
                    "address_2": "an_address_2",
                    "record_uid": ANY,
                    "country": "GB",
                    "message_uid": ANY,
                    "callback_url": None,
                    "marketing_opt_in": True,
                    "marketing_opt_in_thirdparty": False,
                    "merchant_scheme_id1": ANY,
                    "dob": "1987-08-08",
                    "phone1": "0790000000",
                },
                scheme_slug="iceland-bonus-card",
                handler_type=ANY,
                integration_service="ASYNC",
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("send-audit-response"),
            call().send(
                self.iceland,
                response=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=ANY,
                integration_service="ASYNC",
                status_code=HTTPStatus.OK,
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("record-http-request"),
            call().send(
                self.iceland,
                slug="iceland-bonus-card",
                endpoint="/mock/api/v1/bink/join/",
                latency=ANY,
                response_code=HTTPStatus.OK,
            ),
        ]

        self.iceland.join()
        self.assertTrue(mock_consent_confirmation.called)
        self.assertEqual(expected_base_signal_calls, mock_base_signal.mock_calls)
        self.assertEqual(3, mock_base_signal.call_count)
        self.assertEqual(0, mock_iceland_signal.call_count)

    @httpretty.activate
    @mock.patch("app.agents.iceland.get_task", return_value=Mock())
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch("app.agents.base.signal", autospec=True)
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_outbound_expects_callback(
        self,
        mock_consent_confirmation,
        mock_base_signal,
        mock_iceland_signal,
        mock_requests_session,
        mock_oath,
        mock_get_task,
    ):
        self.iceland.outbound_auth_service = Configuration.OAUTH_SECURITY
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body=json.dumps({"result": "OK", "message": "Callback requested with delay"}))
            ],
        )

        self.iceland.join()

        self.assertTrue(self.iceland.expecting_callback)

    @httpretty.activate
    @mock.patch("app.agents.iceland.get_task", return_value=Mock())
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch("app.agents.base.signal", autospec=True)
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_callback_empty_response(
        self,
        mock_consent_confirmation,
        mock_base_signal,
        mock_iceland_signal,
        mock_requests_session,
        mock_oath,
        mock_get_task,
    ):
        self.iceland.outbound_auth_service = Configuration.OAUTH_SECURITY
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body="",
                )
            ],
        )

        self.iceland.join()
        self.assertTrue(mock_consent_confirmation.called)
        self.assertEqual(3, mock_base_signal.call_count)
        self.assertEqual(0, mock_iceland_signal.call_count)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch("app.agents.base.signal", autospec=True)
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_401_unauthorised(
        self, mock_consent_confirmation, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oath
    ):
        self.iceland.outbound_auth_service = Configuration.OAUTH_SECURITY
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            status=401,
        )

        with self.assertRaises(StatusLoginFailedError) as e:
            self.iceland.join()
        self.assertEqual(e.exception.code, 403)
        self.assertEqual(e.exception.name, "Invalid credentials")

    @mock.patch("app.agents.iceland.get_task", return_value=Mock())
    @mock.patch("app.agents.iceland.update_pending_join_account")
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.publish.status")
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_process_join_callback_response(
        self,
        mock_consent_confirmation,
        mock_publish_status,
        mock_iceland_signal,
        mock_update_pending_join_account,
        mock_get_task,
    ):
        data = {
            "message_uid": "a_message_uid",
            "record_uid": "a_record_uid",
            "merchant_scheme_id1": "a_merchant_scheme_id1",
            "merchant_scheme_id2": "a_merchant_scheme_id2",
            "wallet_uid": "",
            "error_codes": [],
            "card_number": "a_card_number",
            "barcode": "a_barcode",
        }
        expected_publish_status_calls = [
            call(1, SchemeAccountStatus.ACTIVE, ANY, self.iceland.user_info, journey="join")
        ]
        self.iceland._process_join_callback_response(data=data)
        self.assertEqual(
            [call([{"id": 1, "slug": "marketing_opt_in", "value": True, "journey_type": 0}], ConsentStatus.SUCCESS)],
            mock_consent_confirmation.mock_calls,
        )
        self.assertEqual(expected_publish_status_calls, mock_publish_status.mock_calls)

    @mock.patch("app.agents.iceland.delete_task")
    @mock.patch("app.error_handler.get_task")
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_process_join_callback_response_with_errors(
        self, mock_consent_confirmation, mock_iceland_signal, mock_get_task, mock_delete
    ):
        self.iceland.errors = {
            CardNumberError: "CARD_NUMBER_ERROR",
        }
        data = {
            "error_codes": [{"code": "CARD_NUMBER_ERROR", "description": "Card number not found"}],
            "message_uid": "a_message_uid",
            "record_uid": "a_record_uid",
            "merchant_scheme_id1": "a_merchant_scheme_id1",
        }
        mock_get_task.return_value.status = RetryTaskStatuses.FAILED
        with self.assertRaises(CardNumberError):
            self.iceland._process_join_callback_response(data=data)

    @mock.patch("app.agents.iceland.get_task", return_value=Mock())
    @mock.patch("requests.Session.post")
    @mock.patch("app.scheme_account.requests", autospec=True)
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_callback(
        self,
        mock_consent_confirmation,
        mock_signal,
        mock_scheme_account_requests,
        mock_session_post,
        mock_get_task,
    ):
        data = {
            "message_uid": "a_message_uid",
            "record_uid": "a_record_uid",
            "merchant_scheme_id1": "a_merchant_scheme_id1",
            "merchant_scheme_id2": "a_merchant_scheme_id2",
            "wallet_uid": "",
            "error_codes": [],
            "card_number": "a_card_number",
            "barcode": "a_barcode",
        }

        expected_signal_calls = [
            call("send-audit-response"),
            call().send(
                response=json.dumps(data),
                message_uid="a_message_uid",
                record_uid=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=Configuration.JOIN_HANDLER,
                integration_service="SYNC",
                status_code=0,
                channel="",
            ),
            call("callback-success"),
            call().send(
                self.iceland,
                slug="iceland-bonus-card",
            ),
        ]

        self.iceland.join_callback(data=data)

        self.assertTrue(mock_consent_confirmation.called)
        self.assertEqual(expected_signal_calls, mock_signal.mock_calls)
        self.assertEqual(
            {"barcode": "a_barcode", "card_number": "a_card_number", "merchant_identifier": "a_merchant_scheme_id2"},
            self.iceland.identifier,
        )
        self.assertIn("credentials", mock_scheme_account_requests.put.call_args[0][0])
        self.assertEqual(
            '{"barcode": "a_barcode", "card_number": "a_card_number", "merchant_identifier": "a_merchant_scheme_id2"}',
            mock_scheme_account_requests.put.call_args_list[0][1]["data"],
        )

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch("app.agents.base.signal", autospec=True)
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_validation_error(
        self, mock_consent_confirmation, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oath
    ):
        self.iceland.outbound_auth_service = Configuration.OAUTH_SECURITY
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "VALIDATION", "description": "Card owner details do not match"}]}
                    ),
                )
            ],
        )

        expected_base_signal_calls = [
            call("send-audit-request"),
            call().send(
                self.iceland,
                payload={
                    "town_city": "a_town",
                    "county": "a_county",
                    "title": "a_title",
                    "address_1": "an_address_1",
                    "first_name": "John",
                    "last_name": "Smith",
                    "email": "ba_test_01@testbink.com",
                    "postcode": "XX0 0XX",
                    "address_2": "an_address_2",
                    "record_uid": ANY,
                    "country": "GB",
                    "message_uid": ANY,
                    "callback_url": None,
                    "marketing_opt_in": True,
                    "marketing_opt_in_thirdparty": False,
                    "merchant_scheme_id1": ANY,
                    "dob": "1987-08-08",
                    "phone1": "0790000000",
                },
                scheme_slug="iceland-bonus-card",
                handler_type=ANY,
                integration_service="ASYNC",
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("send-audit-response"),
            call().send(
                self.iceland,
                response=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=ANY,
                integration_service="ASYNC",
                status_code=HTTPStatus.OK,
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("record-http-request"),
            call().send(
                self.iceland,
                slug="iceland-bonus-card",
                endpoint="/mock/api/v1/bink/join/",
                latency=ANY,
                response_code=HTTPStatus.OK,
            ),
        ]
        expected_consent_confirmation_calls = [
            call([{"id": 1, "slug": "marketing_opt_in", "value": True, "journey_type": 0}], ConsentStatus.FAILED)
        ]

        with self.assertRaises(StatusLoginFailedError) as e:
            self.iceland.join()
        self.assertEqual(expected_consent_confirmation_calls, mock_consent_confirmation.call_args_list)
        self.assertEqual(e.exception.code, 403)
        self.assertEqual(expected_base_signal_calls, mock_base_signal.mock_calls[:8])
        self.assertEqual(3, mock_base_signal.call_count)
        self.assertEqual(0, mock_iceland_signal.call_count)

    @mock.patch("app.error_handler.get_task", return_value=Mock())
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.scheme_account.requests", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_callback_join_in_progress_error(
        self,
        mock_consent_confirmation,
        mock_iceland_signal,
        mock_scheme_account_requests,
        mock_requests_session,
        mock_get_task,
    ):
        data = {
            "message_uid": "a_message_uid",
            "record_uid": "a_record_uid",
            "merchant_scheme_id1": "a_merchant_scheme_id1",
            "merchant_scheme_id2": "a_merchant_scheme_id2",
            "wallet_uid": "",
            "error_codes": [
                {
                    "code": "JOIN_IN_PROGRESS",
                    "description": "Card join request could not be handled - card or URN already "
                    "joined or join is in-flight",
                }
            ],
            "card_number": "a_card_number",
            "barcode": "a_barcode",
        }
        mock_get_task.return_value.status = RetryTaskStatuses.FAILED

        with self.assertRaises(JoinInProgressError) as e:
            self.iceland.join_callback(data=data)
        self.assertEqual("Join in progress", e.exception.name)
        self.assertEqual(441, e.exception.code)
        self.assertEqual(
            ConsentStatus.FAILED,
            mock_consent_confirmation.call_args_list[0][0][1],
        )
        self.assertEqual([call("send-audit-response"), call("callback-fail")], mock_iceland_signal.call_args_list)
        self.assertIn("status", mock_scheme_account_requests.post.call_args[0][0])
        self.assertEqual(
            SchemeAccountStatus.ENROL_FAILED,
            json.loads(mock_scheme_account_requests.post.call_args[1]["data"])["status"],
        )

    @mock.patch("app.error_handler.get_task", return_value=Mock())
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.scheme_account.requests", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_callback_join_error(
        self,
        mock_consent_confirmation,
        mock_iceland_signal,
        mock_scheme_account_requests,
        mock_requests_session,
        mock_get_task,
    ):
        data = {
            "message_uid": "a_message_uid",
            "record_uid": "a_record_uid",
            "merchant_scheme_id1": "a_merchant_scheme_id1",
            "merchant_scheme_id2": "a_merchant_scheme_id2",
            "wallet_uid": "",
            "error_codes": [
                {
                    "code": "JOIN_ERROR",
                    "description": "Card join response could not be handled - open join request "
                    "not found !, @WS_Message = Timeout expired. The timeout period "
                    "elapsed prior to completion of the operation or the server is "
                    "not responding",
                }
            ],
            "card_number": "a_card_number",
            "barcode": "a_barcode",
        }

        mock_get_task.return_value.status = RetryTaskStatuses.FAILED
        mock_get_task.return_value.callback_retries = 3

        with self.assertRaises(JoinError) as e:
            self.iceland.join_callback(data=data)
        self.assertEqual("General error preventing join", e.exception.name)
        self.assertEqual(538, e.exception.code)
        self.assertEqual(
            ConsentStatus.FAILED,
            mock_consent_confirmation.call_args_list[0][0][1],
        )
        self.assertEqual([call("send-audit-response"), call("callback-fail")], mock_iceland_signal.call_args_list)
        self.assertIn("status", mock_scheme_account_requests.post.call_args[0][0])
        self.assertEqual(
            SchemeAccountStatus.ENROL_FAILED,
            json.loads(mock_scheme_account_requests.post.call_args[1]["data"])["status"],
        )

    @mock.patch("app.error_handler.get_task", return_value=Mock())
    @mock.patch("app.agents.iceland.get_task", return_value=Mock())
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.scheme_account.requests", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_callback_account_already_exists_error(
        self,
        mock_consent_confirmation,
        mock_iceland_signal,
        mock_scheme_account_requests,
        mock_requests_session,
        mock_get_task,
        mock_get_task_error_handler,
    ):
        data = {
            "message_uid": "a_message_uid",
            "record_uid": "a_record_uid",
            "merchant_scheme_id1": "a_merchant_scheme_id1",
            "merchant_scheme_id2": "a_merchant_scheme_id2",
            "wallet_uid": "",
            "error_codes": [
                {
                    "code": "ACCOUNT_ALREADY_EXISTS",
                    "description": "Card join response could not be handled - open " "join request not found",
                }
            ],
            "card_number": "a_card_number",
            "barcode": "a_barcode",
        }

        mock_get_task_error_handler.return_value.status = RetryTaskStatuses.FAILED

        with self.assertRaises(AccountAlreadyExistsError) as e:
            self.iceland.join_callback(data=data)
        self.assertEqual("Account already exists", e.exception.name)
        self.assertEqual(SchemeAccountStatus.ACCOUNT_ALREADY_EXISTS, e.exception.code)
        self.assertEqual(
            ConsentStatus.FAILED,
            mock_consent_confirmation.call_args_list[0][0][1],
        )
        self.assertEqual([call("send-audit-response"), call("callback-fail")], mock_iceland_signal.call_args_list)
        self.assertIn("status", mock_scheme_account_requests.post.call_args[0][0])
        self.assertEqual(
            SchemeAccountStatus.ACCOUNT_ALREADY_EXISTS,
            json.loads(mock_scheme_account_requests.post.call_args[1]["data"])["status"],
        )

    @mock.patch("app.error_handler.get_task", return_value=Mock())
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.scheme_account.requests", autospec=True)
    @mock.patch("app.agents.iceland.signal")
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_join_callback_general_error(
        self,
        mock_consent_confirmation,
        mock_iceland_signal,
        mock_scheme_account_requests,
        mock_requests_session,
        mock_get_task,
    ):
        data = {
            "message_uid": "a_message_uid",
            "record_uid": "a_record_uid",
            "merchant_scheme_id1": "a_merchant_scheme_id1",
            "merchant_scheme_id2": "a_merchant_scheme_id2",
            "wallet_uid": "",
            "error_codes": [
                {
                    "code": "GENERAL_ERROR",
                    "description": "Unspecified exception",
                }
            ],
            "card_number": "a_card_number",
            "barcode": "a_barcode",
        }
        mock_get_task.return_value.status = RetryTaskStatuses.FAILED
        with self.assertRaises(GeneralError) as e:
            self.iceland.join_callback(data=data)
        self.assertEqual("General error", e.exception.name)
        self.assertEqual(439, e.exception.code)
        self.assertEqual(
            ConsentStatus.FAILED,
            mock_consent_confirmation.call_args_list[0][0][1],
        )
        self.assertEqual([call("send-audit-response"), call("callback-fail")], mock_iceland_signal.call_args_list)
        self.assertIn("status", mock_scheme_account_requests.post.call_args[0][0])
        self.assertEqual(
            SchemeAccountStatus.ENROL_FAILED,
            json.loads(mock_scheme_account_requests.post.call_args[1]["data"])["status"],
        )

    def test_add_additional_consent(self):
        expected_consents = [
            {"id": 1, "slug": "marketing_opt_in", "value": True, "journey_type": 0},
            {
                "id": 99999999999,
                "slug": "marketing_opt_in_thirdparty",
                "value": False,
                "created_on": ANY,
                "journey_type": 0,
            },
        ]
        self.iceland._add_additional_consent()

        self.assertEqual(expected_consents, self.iceland.user_info["credentials"]["consents"])

    def test_add_additional_consent_when_there_is_more_than_one_consent(self):
        self.iceland.user_info["credentials"]["consents"].append(
            {
                "id": 99999999999,
                "slug": "marketing_opt_in_thirdparty",
                "value": False,
                "created_on": "2020-05-26T15:30:16.096802+00:00",
                "journey_type": 0,
            }
        )
        logger = get_logger("iceland")
        with mock.patch.object(logger, "debug") as mock_logger:
            self.iceland._add_additional_consent()

        self.assertEqual(2, len(self.iceland.user_info["credentials"]["consents"]))
        self.assertEqual(call("Too many consents for Iceland scheme."), mock_logger.call_args)

    @mock.patch("app.agents.iceland.get_task", return_value=Mock())
    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch("app.agents.iceland.Iceland._join", return_value={"message_uid": ""})
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_consents_confirmed_as_pending_on_async_join(
        self, mock_consent_confirmation, mock_join, mock_authenticate, mock_get_task
    ):
        self.iceland.outbound_auth_service = Configuration.OAUTH_SECURITY
        self.iceland.join()

        self.assertTrue(mock_join.called)
        mock_consent_confirmation.assert_called_with(
            [
                {"id": 1, "slug": "marketing_opt_in", "value": True, "journey_type": JourneyTypes.JOIN.value},
            ],
            ConsentStatus.PENDING,
        )

    @mock.patch("app.agents.iceland.Iceland.authenticate", return_value="a_token")
    @mock.patch(
        "app.agents.iceland.Iceland._join", return_value={"error_codes": [{"code": "GENERAL_ERROR"}], "message_uid": ""}
    )
    @mock.patch.object(BaseAgent, "consent_confirmation")
    def test_consents_confirmed_as_failed_on_async_join(self, mock_consent_confirmation, mock_join, mock_authenticate):
        self.iceland.outbound_auth_service = Configuration.OAUTH_SECURITY
        with self.assertRaises(GeneralError):
            self.iceland.join()

        self.assertTrue(mock_join.called)
        mock_consent_confirmation.assert_called_with(
            [
                {"id": 1, "slug": "marketing_opt_in", "value": True, "journey_type": JourneyTypes.JOIN.value},
            ],
            ConsentStatus.FAILED,
        )

    @mock.patch("app.tasks.resend_consents.requests.put")
    def test_consents_confirmation_sends_updated_user_consents(self, mock_requests_put):
        mock_requests_put.return_value.status_code = 200
        consents_data = [
            {"id": 1, "slug": "consent-slug1", "value": True, "created_on": "", "journey_type": 1},
            {"id": 2, "slug": "consent-slug2", "value": False, "created_on": "", "journey_type": 1},
        ]

        self.iceland.consent_confirmation(consents_data, ConsentStatus.SUCCESS)

        mock_requests_put.assert_called_with(
            ANY, data=json.dumps({"status": ConsentStatus.SUCCESS}), headers=ANY, timeout=ANY
        )

    @mock.patch("app.tasks.resend_consents.requests.put")
    def test_consents_confirmation_works_with_empty_consents(self, mock_requests_put):
        mock_requests_put.return_value.status_code = 200
        self.iceland.consent_confirmation([], ConsentStatus.SUCCESS)

        self.assertFalse(mock_requests_put.called)

    def test_create_join_request_payload(self):
        self.iceland.user_info["credentials"]["consents"].append(
            {
                "id": 99999999999,
                "slug": "marketing_opt_in_thirdparty",
                "value": False,
                "created_on": "2020-05-26T15:30:16.096802+00:00",
                "journey_type": 0,
            }
        )
        expected_payload = {
            "town_city": "a_town",
            "county": "a_county",
            "title": "a_title",
            "address_1": "an_address_1",
            "first_name": "John",
            "last_name": "Smith",
            "email": "ba_test_01@testbink.com",
            "postcode": "XX0 0XX",
            "address_2": "an_address_2",
            "record_uid": "7gl82g4y5pvzx1wj5noqrj3dke7m9092",
            "country": "GB",
            "message_uid": ANY,
            "callback_url": None,
            "marketing_opt_in": True,
            "marketing_opt_in_thirdparty": False,
            "merchant_scheme_id1": "7gl82g4y5pvzx1wj5noqrj3dke7m9092",
            "dob": "1987-08-08",
            "phone1": "0790000000",
        }
        payload = self.iceland._create_join_request_payload()
        self.assertEqual(expected_payload, payload)

    def test_create_join_request_payload_when_no_consents(self):
        self.iceland.user_info["credentials"]["consents"] = {}
        payload = self.iceland._create_join_request_payload()
        self.assertEqual(None, payload["marketing_opt_in"])
        self.assertEqual(None, payload["marketing_opt_in_thirdparty"])


# This should potentially be moved once end-to-end test suite has been configured
class TestIcelandEndToEnd(FlaskTestCase):
    TESTING = True

    user_info = {
        "scheme_account_id": 1,
        "status": "",
        "user_set": "1",
        "journey_type": JourneyTypes.LINK.value,
        "channel": "com.bink.wallet",
        "credentials": {},
    }

    user_info_user_set = {
        "scheme_account_id": 1,
        "status": "",
        "user_set": "1,2",
        "journey_type": JourneyTypes.LINK.value,
        "channel": "com.bink.wallet",
        "credentials": {},
    }

    json_data = json.dumps(
        {
            "message_uid": "123-123-123-123",
            "record_uid": "7gl82g4y5pvzx1wj5noqrj3dke7m9092",  # hash for a scheme account id of 1
            "merchant_scheme_id1": "7gl82g4y5pvzx1wj5noqrj3dke7m9092",
            "channel": "com.bink.wallet",
        }
    )

    signature = (
        b"BQCt9fJ25heLp+sm5HRHsMeYfGmjeUb3i/GK5xaxCQwQLa6RX49Pnu/T"
        b"a2b6Mt4DMYV80rd0sP1Ebfw4cW8cSqhRMisQlvRN3fAzytJO0s8jOHyb"
        b"lNA5EQo8kmjlC4YoD2a3rYVKKmJv27DpPIYXW17tZr1i5ZMifGPKgzbv"
        b"vKzcNZeOOT2q5UE+HbGdeuw13SLoBPJkLE028g+XSk+WbDH4SwiybnGY"
        b"401duxapoRkQUpUIgayoz4b6uVlm4TbiS+vFmULVcLZ0rvhLoC2l0S1c"
        b"27Ti+F4QntxmTOfcxw6SB+V0PEr8gIk59lHSKqKiDcGRjnOIES084DKeMyuMUQ=="
    ).decode("utf8")

    def create_app(self):
        return create_app(
            self,
        )

    def setUp(self):
        mock_configuration = MagicMock()
        mock_configuration.scheme_slug = "id"
        mock_configuration.merchant_url = "stuff"
        mock_configuration.integration_service = "SYNC"
        mock_configuration.handler_type = (0, "UPDATE")
        mock_configuration.retry_limit = 2
        mock_configuration.callback_url = ""
        mock_configuration.log_level = "DEBUG"
        mock_configuration.country = "GB"
        mock_configuration.integration_service = "SYNC"
        mock_configuration.security_credentials = {
            "outbound": {
                "service": 0,
                "credentials": [{"storage_key": "", "value": PRIVATE_KEY, "credential_type": "bink_private_key"}],
            },
            "inbound": {
                "service": 0,
                "credentials": [
                    {"storage_key": "", "value": PRIVATE_KEY, "credential_type": "bink_private_key"},
                    {"storage_key": "", "value": PUBLIC_KEY, "credential_type": "merchant_public_key"},
                ],
            },
        }
        self.config = mock_configuration

    @mock.patch("app.resources_callbacks.delete_task")
    @mock.patch("app.resources_callbacks.get_task", return_value=Mock())
    @mock.patch("app.agents.iceland.delete_task")
    @mock.patch("app.agents.iceland.get_task", return_value=Mock())
    @mock.patch("app.error_handler.get_task", return_value=Mock())
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.scheme_account.requests", autospec=True)
    @mock.patch.object(BaseAgent, "consent_confirmation")
    @mock.patch("app.publish.status")
    @mock.patch("app.resources_callbacks.JoinCallback._collect_credentials")
    @mock.patch("app.resources_callbacks.redis_retry", autospec=True)
    @mock.patch.object(RSA, "decode", autospec=True)
    @mock.patch("app.security.utils.configuration.Configuration")
    def test_async_join_callback_returns_success(
        self,
        mock_config,
        mock_decode,
        mock_retry,
        mock_collect_credentials,
        mock_publish_status,
        mock_consent_confirmation,
        mock_scheme_account_requests,
        mock_iceland_signal,
        mock_get_task_error_handler,
        mock_get_task_iceland,
        mock_delete_task,
        mock_get_task_callback,
        mock_delete_task_callback,
    ):
        mock_config.return_value = self.config
        mock_decode.return_value = self.json_data

        headers = {
            "Authorization": "Signature {}".format(self.signature),
        }

        response = self.client.post("/join/merchant/iceland-bonus-card", headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertTrue(mock_retry.get_key.called)
        self.assertTrue(mock_collect_credentials.called)
        self.assertTrue(mock_publish_status.called)
        self.assertTrue(mock_consent_confirmation.called)
        self.assertTrue(mock_scheme_account_requests.put.called)

        self.assertEqual(200, response.status_code)
        self.assertEqual({"success": True}, response.json)

    @mock.patch("app.resources_callbacks.redis_retry", autospec=True)
    @mock.patch.object(RSA, "decode", autospec=True)
    @mock.patch("app.security.utils.configuration.Configuration")
    def test_join_callback_raises_error_with_bad_record_uid(
        self,
        mock_config,
        mock_decode,
        mock_retry,
    ):
        mock_config.return_value = self.config
        json_data_with_bad_record_uid = json.dumps(
            {
                "message_uid": "123-123-123-123",
                "record_uid": "a",
                "merchant_scheme_id1": "V8YaqMdl6WEPeZ4XWv91zO7o2GKQgwm5",
            }
        )
        mock_decode.return_value = json_data_with_bad_record_uid

        headers = {
            "Authorization": "Signature {}".format(self.signature),
        }

        response = self.client.post("/join/merchant/iceland-bonus-card", headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertFalse(mock_retry.get_key.called)

        self.assertEqual(520, response.status_code)
        self.assertEqual(
            {"code": 520, "message": "The record_uid provided is not valid", "name": "Unknown error"},
            response.json,
        )

    @mock.patch("app.resources_callbacks.JoinCallback._collect_credentials")
    @mock.patch("app.resources_callbacks.update_pending_join_account", autospec=True)
    @mock.patch("app.resources_callbacks.redis_retry.get_key", autospec=True)
    @mock.patch.object(RSA, "decode", autospec=True)
    @mock.patch("app.security.utils.configuration.Configuration")
    def test_join_callback_specific_error(
        self,
        mock_config,
        mock_RSA_decode,
        mock_redis_retry_get_key,
        mock_update_pending_join_account,
        mock_collect_credentials,
    ):
        mock_redis_retry_get_key.side_effect = NoSuchRecordError()
        mock_config.return_value = self.config
        mock_RSA_decode.return_value = self.json_data

        headers = {"Authorization": "Signature {}".format(self.signature)}

        response = self.client.post("/join/merchant/iceland-bonus-card", headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_RSA_decode.called)
        self.assertTrue(mock_redis_retry_get_key.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(mock_collect_credentials.called)

        self.assertEqual(444, response.status_code)

    @mock.patch("app.resources_callbacks.JoinCallback._collect_credentials")
    @mock.patch("app.resources_callbacks.update_pending_join_account", autospec=True)
    @mock.patch("app.resources_callbacks.redis_retry.get_key", autospec=True)
    @mock.patch.object(RSA, "decode", autospec=True)
    @mock.patch("app.security.utils.configuration.Configuration")
    def test_join_callback_unknown_error(
        self, mock_config, mock_decode, mock_retry, mock_update_join, mock_credentials
    ):
        mock_retry.side_effect = RuntimeError("test exception")
        mock_config.return_value = self.config
        mock_decode.return_value = self.json_data

        headers = {"Authorization": "Signature {}".format(self.signature)}

        response = self.client.post("/join/merchant/iceland-bonus-card", headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertTrue(mock_retry.called)
        self.assertTrue(mock_update_join.called)
        self.assertTrue(mock_credentials.called)

        self.assertEqual(520, response.status_code)
        self.assertEqual({"code": 520, "message": "test exception", "name": "Unknown error"}, response.json)

    @mock.patch("requests.sessions.Session.get")
    @mock.patch.object(RSA, "decode", autospec=True)
    @mock.patch("app.security.utils.configuration.Configuration")
    def test_join_callback_raises_custom_exception_if_collect_credentials_fails(
        self, mock_config, mock_decode, mock_session_get
    ):
        mock_config.return_value = self.config
        mock_decode.return_value = self.json_data

        mock_response = Response()
        mock_response.status_code = 404

        # Bad response test
        mock_session_get.return_value = mock_response
        headers = {"Authorization": f"Signature {self.signature}"}

        response = self.client.post("/join/merchant/iceland-bonus-card", headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertEqual(ServiceConnectionError().code, response.status_code)
        self.assertEqual(
            {
                "code": 537,
                "message": "404 Client Error: None for url: None",
                "name": "Service connection error",
            },
            response.json,
        )

        # Connection error test
        mock_session_get.side_effect = requests.ConnectionError

        with mock.patch("app.resources_callbacks.get_agent_class", autospec=True, return_value=Iceland):
            response = self.client.post("/join/merchant/iceland-bonus-card", headers=headers)

        self.assertEqual(
            ServiceConnectionError().code,
            response.status_code,
        )
        self.assertEqual(
            {
                "code": 537,
                "message": "There was in issue connecting to an external service.",
                "name": "Service connection error",
            },
            response.json,
        )
