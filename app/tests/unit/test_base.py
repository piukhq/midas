import httpretty
from http import HTTPStatus
from unittest import TestCase, mock
from app.agents.base import ApiMiner
from app.agents.exceptions import (
    END_SITE_DOWN, IP_BLOCKED, STATUS_LOGIN_FAILED, AgentError, LoginError)


class TestBase(TestCase):
    @mock.patch.object(ApiMiner, 'register')
    def test_attempt_register(self, mocked_register):
        user_info = {'scheme_account_id': 194,
                     'status': '',
                     'channel': 'com.bink.wallet'}
        m = ApiMiner(0, user_info)

        m.attempt_register(credentials={})
        self.assertTrue(mocked_register.called)

    @httpretty.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_agenterror_calls_signals(self, mock_signal):
        """
        Check that correct params are passed to the signals for an unsuccessful (AgentError) request
        """
        # GIVEN
        user_info = {'scheme_account_id': 194,
                     'status': '',
                     'channel': 'com.bink.wallet'}
        m = ApiMiner(0, user_info)
        url = "http://someexcitingplace.com"
        httpretty.register_uri(
            httpretty.GET, url, status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(
                m,
                slug=m.scheme_slug,
                channel=m.channel,
                error=END_SITE_DOWN
            ),
        ]

        # WHEN
        self.assertRaises(
            AgentError,
            m.make_request,
            url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_make_request_fail_with_timeout_calls_signals(self, mock_signal):
        """
        Check that correct params are passed to the signals for an unsuccessful (Timeout) request
        """
        # GIVEN
        user_info = {'scheme_account_id': 194,
                     'status': '',
                     'channel': 'com.bink.wallet'}
        m = ApiMiner(0, user_info)
        url = "http://someexcitingplace.com"
        httpretty.register_uri(
            httpretty.GET, url, status=HTTPStatus.REQUEST_TIMEOUT,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(
                m,
                slug=m.scheme_slug,
                channel=m.channel,
                error=END_SITE_DOWN
            ),
        ]

        # WHEN
        self.assertRaises(
            AgentError,
            m.make_request,
            url,
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
        user_info = {'scheme_account_id': 194,
                     'status': '',
                     'channel': 'com.bink.wallet'}
        m = ApiMiner(0, user_info)
        url = "http://someexcitingplace.com"
        httpretty.register_uri(
            httpretty.GET, url, status=HTTPStatus.UNAUTHORIZED,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(
                m,
                slug=m.scheme_slug,
                channel=m.channel,
                error=STATUS_LOGIN_FAILED
            ),
        ]

        # WHEN
        self.assertRaises(
            LoginError,
            m.make_request,
            url,
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
        user_info = {'scheme_account_id': 194,
                     'status': '',
                     'channel': 'com.bink.wallet'}
        m = ApiMiner(0, user_info)
        url = "http://someexcitingplace.com"
        httpretty.register_uri(
            httpretty.GET, url, status=HTTPStatus.FORBIDDEN,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(
                m,
                slug=m.scheme_slug,
                channel=m.channel,
                error=IP_BLOCKED
            ),
        ]

        # WHEN
        self.assertRaises(
            AgentError,
            m.make_request,
            url,
            method="get",
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)
