from http import HTTPStatus
from unittest import TestCase, mock
from unittest.mock import ANY, call
from urllib.parse import urljoin

import httpretty
from soteria.configuration import Configuration

from app.agents.base import ApiMiner, BaseMiner, check_correct_authentication, create_error_response
from app.agents.exceptions import (
    CARD_NUMBER_ERROR,
    END_SITE_DOWN,
    GENERAL_ERROR,
    IP_BLOCKED,
    STATUS_LOGIN_FAILED,
    AgentError,
    JoinError,
    LoginError,
)
from app.scheme_account import SchemeAccountStatus
from app.tasks.resend_consents import ConsentStatus


class TestBase(TestCase):
    def test_create_error_response(self):
        response_json = create_error_response("NOT_SENT", "This is a test error")

        self.assertIn("NOT_SENT", response_json)

    @mock.patch.object(ApiMiner, "join")
    def test_attempt_join(self, mocked_join):
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)

        m.attempt_join(credentials={})
        self.assertTrue(mocked_join.called)

    @httpretty.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_agenterror_calls_signals(self, mock_signal):
        """
        Check that correct params are passed to the signals for an unsuccessful (AgentError) request
        """
        # GIVEN
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)
        m.base_url = "http://fake.com"
        ctcid = "54321"
        api_path = "/api/Contact/AddMemberNumber"
        api_query = f"?CtcID={ctcid}"
        api_url = urljoin(m.base_url, api_path) + api_query
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("record-http-request"),
            mock.call().send(
                m,
                endpoint=api_path,
                latency=mock.ANY,
                response_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                slug=m.scheme_slug,
            ),
            mock.call("request-fail"),
            mock.call().send(
                m,
                channel=m.channel,
                error=END_SITE_DOWN,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            AgentError,
            m.make_request,
            api_url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_loginerror_calls_signals(self, mock_signal):
        """
        Check that correct params are passed to the signals for an unsuccessful (LoginError) request
        """
        # GIVEN
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)
        m.base_url = "http://fake.com"
        ctcid = "54321"
        api_path = "/api/Contact/AddMemberNumber"
        api_query = f"?CtcID={ctcid}"
        api_url = urljoin(m.base_url, api_path) + api_query
        httpretty.register_uri(httpretty.GET, api_url, status=HTTPStatus.UNAUTHORIZED)
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("record-http-request"),
            mock.call().send(
                m,
                endpoint=api_path,
                latency=mock.ANY,
                response_code=HTTPStatus.UNAUTHORIZED,
                slug=m.scheme_slug,
            ),
            mock.call("request-fail"),
            mock.call().send(
                m,
                channel=m.channel,
                error=STATUS_LOGIN_FAILED,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(LoginError, m.make_request, api_url, method="get")

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_timeout_calls_signals(self, mock_signal):
        """
        Check that correct params are passed to the signals for an unsuccessful (Timeout) request
        """
        # GIVEN
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)
        m.base_url = "http://fake.com"
        ctcid = "54321"
        api_path = "/api/Contact/AddMemberNumber"
        api_query = f"?CtcID={ctcid}"
        api_url = urljoin(m.base_url, api_path) + api_query
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.REQUEST_TIMEOUT,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("record-http-request"),
            mock.call().send(
                m,
                endpoint=api_path,
                latency=mock.ANY,
                response_code=HTTPStatus.REQUEST_TIMEOUT,
                slug=m.scheme_slug,
            ),
            mock.call("request-fail"),
            mock.call().send(
                m,
                channel=m.channel,
                error=END_SITE_DOWN,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            AgentError,
            m.make_request,
            api_url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_unauthorized_calls_signals(self, mock_signal):
        """
        Check that correct params are passed to the signals for an unsuccessful (unauthorized) request
        """
        # GIVEN
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)
        m.base_url = "http://fake.com"
        ctcid = "54321"
        api_path = "/api/Contact/AddMemberNumber"
        api_query = f"?CtcID={ctcid}"
        api_url = urljoin(m.base_url, api_path) + api_query
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.UNAUTHORIZED,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("record-http-request"),
            mock.call().send(
                m,
                endpoint=api_path,
                latency=mock.ANY,
                response_code=HTTPStatus.UNAUTHORIZED,
                slug=m.scheme_slug,
            ),
            mock.call("request-fail"),
            mock.call().send(
                m,
                channel=m.channel,
                error=STATUS_LOGIN_FAILED,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            AgentError,
            m.make_request,
            api_url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_forbidden_calls_signals(self, mock_signal):
        """
        Check that correct params are passed to the signals for an unsuccessful (forbidden) request
        """
        # GIVEN
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)
        m.base_url = "http://fake.com"
        ctcid = "54321"
        api_path = "/api/Contact/AddMemberNumber"
        api_query = f"?CtcID={ctcid}"
        api_url = urljoin(m.base_url, api_path) + api_query
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.FORBIDDEN,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(
                m,
                channel=m.channel,
                error=IP_BLOCKED,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            AgentError,
            m.make_request,
            api_url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    def test_handle_errors_raises_exception(self):
        agent = ApiMiner(
            retry_count=0, user_info={"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        )
        agent.errors = {
            GENERAL_ERROR: "GENERAL_ERROR",
        }
        with self.assertRaises(LoginError) as e:
            agent._handle_errors(error_code="GENERAL_ERROR")
        self.assertEqual("General Error", e.exception.name)
        self.assertEqual(439, e.exception.code)

    def test_handle_errors_raises_exception_if_not_in_agent_self_errors(self):
        agent = ApiMiner(
            retry_count=0, user_info={"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        )
        agent.errors = {
            GENERAL_ERROR: "GENERAL_ERROR",
        }
        with self.assertRaises(AgentError) as e:
            agent._handle_errors(error_code="VALIDATION")
        self.assertEqual("An unknown error has occurred", e.exception.name)
        self.assertEqual(520, e.exception.code)

    @mock.patch("app.agents.base.update_pending_join_account")
    @mock.patch("app.publish.status")
    @mock.patch.object(BaseMiner, "consent_confirmation")
    def test_process_join_response(
        self, mock_consent_confirmation, mock_publish_status, mock_update_pending_join_account
    ):
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        agent = ApiMiner(retry_count=0, user_info=user_info)
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
        expected_publish_status_calls = [call(194, SchemeAccountStatus.ACTIVE, ANY, user_info, journey="join")]
        agent._process_join_response(data=data, consents=[])
        self.assertEqual([call([], ConsentStatus.SUCCESS)], mock_consent_confirmation.mock_calls)
        self.assertEqual(expected_publish_status_calls, mock_publish_status.mock_calls)

    def test_process_join_response_with_errors(self):
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        agent = ApiMiner(retry_count=0, user_info=user_info)
        agent.errors = {
            CARD_NUMBER_ERROR: "CARD_NUMBER_ERROR",
        }
        data = {
            "error_codes": [{"code": "CARD_NUMBER_ERROR", "description": "Card number not found"}],
            "message_uid": "a_message_uid",
            "record_uid": "a_record_uid",
            "merchant_scheme_id1": "a_merchant_scheme_id1",
        }
        with self.assertRaises(JoinError):
            agent._process_join_response(data=data, consents=[])

    def test_check_correct_authentication(self):
        actual_config_auth_type = Configuration.OAUTH_SECURITY
        allowed_config_auth_types = [Configuration.OAUTH_SECURITY, Configuration.OPEN_AUTH_SECURITY]

        self.assertEqual(None, check_correct_authentication(allowed_config_auth_types, actual_config_auth_type))

    def test_check_incorrect_authentication_raises_error(self):
        actual_config_auth_type = Configuration.RSA_SECURITY
        allowed_config_auth_types = [Configuration.OAUTH_SECURITY, Configuration.OPEN_AUTH_SECURITY]

        with self.assertRaises(AgentError) as e:
            check_correct_authentication(allowed_config_auth_types, actual_config_auth_type)
        self.assertEqual("Configuration error", e.exception.name)
        self.assertEqual(
            "Agent expecting Security Type(s) ['OAuth', 'Open Auth (No Authentication)'] "
            "but got Security Type 'RSA' instead",
            e.exception.message,
        )
