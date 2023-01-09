import json
from http import HTTPStatus
from unittest import TestCase, mock
from urllib.parse import urljoin

import arrow
import httpretty
from soteria.configuration import Configuration

from app.agents.base import BaseAgent, create_error_response
from app.exceptions import EndSiteDownError, GeneralError, IPBlockedError, StatusLoginFailedError, UnknownError
from app.scheme_account import JourneyTypes


class TestBase(TestCase):
    def test_create_error_response(self):
        response_json = create_error_response("NOT_SENT", "This is a test error")

        self.assertIn("NOT_SENT", response_json)

    @mock.patch("app.agents.base.Configuration")
    @mock.patch.object(BaseAgent, "join")
    def test_attempt_join(self, mocked_join, mock_config):
        user_info = {
            "scheme_account_id": 194,
            "status": "",
            "channel": "com.bink.wallet",
            "journey_type": JourneyTypes.JOIN,
            "credentials": {},
        }
        m = BaseAgent(0, user_info, Configuration.JOIN_HANDLER)

        m.attempt_join()
        self.assertTrue(mocked_join.called)

    @httpretty.activate
    @mock.patch("app.agents.base.Configuration")
    @mock.patch("app.requests_retry.Retry")
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_agenterror_calls_signals(self, mock_signal, mock_retry, mock_config):
        """
        Check that correct params are passed to the signals for an unsuccessful (AgentError) request
        """
        # GIVEN
        user_info = {
            "scheme_account_id": 194,
            "status": "",
            "channel": "com.bink.wallet",
            "journey_type": JourneyTypes.LINK.value,
        }
        m = BaseAgent(0, user_info, Configuration.JOIN_HANDLER)
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
                error=EndSiteDownError,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            EndSiteDownError,
            m.make_request,
            api_url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.Configuration")
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_loginerror_calls_signals(self, mock_signal, mock_config):
        """
        Check that correct params are passed to the signals for an unsuccessful (LoginError) request
        """
        # GIVEN
        user_info = {
            "scheme_account_id": 194,
            "status": "",
            "channel": "com.bink.wallet",
            "journey_type": JourneyTypes.LINK.value,
        }
        m = BaseAgent(0, user_info, Configuration.JOIN_HANDLER)
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
                error=StatusLoginFailedError,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(StatusLoginFailedError, m.make_request, api_url, method="get")

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.Configuration")
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_timeout_calls_signals(self, mock_signal, mock_config):
        """
        Check that correct params are passed to the signals for an unsuccessful (Timeout) request
        """
        # GIVEN
        user_info = {
            "scheme_account_id": 194,
            "status": "",
            "channel": "com.bink.wallet",
            "journey_type": JourneyTypes.LINK.value,
        }
        m = BaseAgent(0, user_info, Configuration.JOIN_HANDLER)
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
                error=EndSiteDownError,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            EndSiteDownError,
            m.make_request,
            api_url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.Configuration")
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_unauthorized_calls_signals(self, mock_signal, mock_config):
        """
        Check that correct params are passed to the signals for an unsuccessful (unauthorized) request
        """
        # GIVEN
        user_info = {
            "scheme_account_id": 194,
            "status": "",
            "channel": "com.bink.wallet",
            "journey_type": JourneyTypes.LINK.value,
        }
        m = BaseAgent(0, user_info, Configuration.JOIN_HANDLER)
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
                error=StatusLoginFailedError,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            StatusLoginFailedError,
            m.make_request,
            api_url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.Configuration")
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_forbidden_calls_signals(self, mock_signal, mock_config):
        """
        Check that correct params are passed to the signals for an unsuccessful (forbidden) request
        """
        # GIVEN
        user_info = {
            "scheme_account_id": 194,
            "status": "",
            "channel": "com.bink.wallet",
            "journey_type": JourneyTypes.LINK.value,
        }
        m = BaseAgent(0, user_info, Configuration.JOIN_HANDLER)
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
                error=IPBlockedError,
                slug=m.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            IPBlockedError,
            m.make_request,
            api_url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @mock.patch("app.agents.base.Configuration")
    def test_handle_errors_raises_exception(self, mock_config):
        agent = BaseAgent(
            retry_count=0,
            user_info={
                "scheme_account_id": 194,
                "status": "",
                "channel": "com.bink.wallet",
                "journey_type": JourneyTypes.LINK.value,
            },
            config_handler_type=Configuration.JOIN_HANDLER,
        )
        agent.errors = {
            GeneralError: "GENERAL_ERROR",
        }
        with self.assertRaises(GeneralError) as e:
            agent.handle_error_codes(error_code="GENERAL_ERROR")
        self.assertEqual("General error", e.exception.name)
        self.assertEqual(439, e.exception.code)

    @mock.patch("app.agents.base.Configuration")
    def test_handle_errors_raises_exception_if_not_in_agent_self_errors(self, mock_config):
        agent = BaseAgent(
            retry_count=0,
            user_info={
                "scheme_account_id": 194,
                "status": "",
                "channel": "com.bink.wallet",
                "journey_type": JourneyTypes.LINK.value,
            },
            config_handler_type=Configuration.JOIN_HANDLER,
        )
        agent.errors = {
            GeneralError: "GENERAL_ERROR",
        }
        with self.assertRaises(UnknownError) as e:
            agent.handle_error_codes(error_code="VALIDATION")
        self.assertEqual("Unknown error", e.exception.name)
        self.assertEqual(520, e.exception.code)

    @mock.patch("app.agents.base.Configuration")
    def test_token_store_legacy_token_with_timestamp_as_list(self, mock_config):
        """
        Some old Iceland tokens stored in the redis cache contained a timestamp value in a list
        This test checks that we can obtain the timestamp from the list without raising a TypeError
        """
        base_agent = BaseAgent(
            retry_count=0,
            user_info={
                "scheme_account_id": 194,
                "status": "",
                "channel": "com.bink.wallet",
                "journey_type": JourneyTypes.LINK.value,
            },
            config_handler_type=Configuration.UPDATE_HANDLER,
        )
        current_timestamp = arrow.utcnow().int_timestamp

        cached_token = {"iceland_bonus_card_access_token": "abcde12345fghij",
                        "timestamp": [arrow.utcnow().int_timestamp]}

        result = base_agent._token_is_valid(cached_token, current_timestamp)

        self.assertTrue(result)

    @mock.patch("app.agents.base.Configuration")
    def test_token_is_valid_success(self, mock_config):
        base_agent = BaseAgent(
            retry_count=0,
            user_info={
                "scheme_account_id": 194,
                "status": "",
                "channel": "com.bink.wallet",
                "journey_type": JourneyTypes.LINK.value,
            },
            config_handler_type=Configuration.UPDATE_HANDLER,
        )
        base_agent.oauth_token_timeout = 3599
        current_timestamp = arrow.utcnow().int_timestamp
        cached_token = {"iceland_bonus_card_access_token": "abcde12345fghij",
                        "timestamp": arrow.utcnow().int_timestamp+100}

        result = base_agent._token_is_valid(cached_token, current_timestamp)

        self.assertTrue(result)
