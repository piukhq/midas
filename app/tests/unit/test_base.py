
from http import HTTPStatus
from unittest import TestCase, mock
from urllib.parse import urljoin

import httpretty
from soteria.configuration import Configuration

from app.agents.base import ApiMiner, check_correct_authentication, create_error_response
from app.agents.exceptions import END_SITE_DOWN, IP_BLOCKED, STATUS_LOGIN_FAILED, AgentError, LoginError


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
