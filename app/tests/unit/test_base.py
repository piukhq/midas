from decimal import Decimal
from http import HTTPStatus
from unittest import TestCase, mock

import arrow
import httpretty
from app.agents.base import ApiMiner, RoboBrowserMiner
from app.agents.exceptions import (
    END_SITE_DOWN, IP_BLOCKED, STATUS_LOGIN_FAILED, AgentError, LoginError, RetryLimitError)


class TestBase(TestCase):
    @mock.patch.object(RoboBrowserMiner, 'parse_transaction')
    def test_hashed_transaction(self, mocked_parse_transaction):
        transactions = [{
            "date": arrow.get('2013-09-30T15:34:00.000-07:00'),
            "description": "Clothes purchase",
            "points": 44
        }]
        user_info = {'scheme_account_id': 2,
                     'status': ''}

        mocked_parse_transaction.return_value = transactions
        m = RoboBrowserMiner(1, user_info)
        transaction = m.hash_transactions(transactions)

        self.assertEqual(transaction[0]["hash"], "a0c99f1ec24421acb6b12ec82cc07792")

    def test_duplicate_transactions(self):
        transactions = [{
            "date": arrow.get('2013-09-30T15:34:00.000-07:00'),
            "description": "Clothes purchase",
            "points": 44
        }, {
            "date": arrow.get('2013-09-30T15:34:00.000-07:00'),
            "description": "Clothes purchase",
            "points": 44
        }]

        user_info = {'scheme_account_id': 1,
                     'status': ''}

        m = RoboBrowserMiner(1, user_info)
        transactions = m.hash_transactions(transactions)

        hashes = [t['hash'] for t in transactions]
        self.assertEqual(len(hashes), len(set(hashes)))

    def test_attempt_login_exception(self):
        user_info = {'scheme_account_id': 2,
                     'status': ''}
        m = RoboBrowserMiner(3, user_info)
        with self.assertRaises(RetryLimitError) as e:
            m.attempt_login(credentials={})
        self.assertEqual(e.exception.name, "Retry limit reached")

    @mock.patch.object(RoboBrowserMiner, 'login')
    def test_attempt_login(self, mocked_login):
        user_info = {'scheme_account_id': 2,
                     'status': ''}
        m = RoboBrowserMiner(1, user_info)

        m.attempt_login(credentials={})
        self.assertTrue(mocked_login.called)

    def test_check_error(self):
        mock_instance = mock.create_autospec(RoboBrowserMiner)
        browser = mock.MagicMock()
        browser.url = "http://www.test.com/test.aspx?sdf=34"
        mock_instance.browser = browser

        # the method should do nothing when called
        RoboBrowserMiner.check_error(mock_instance, "/HomeSecurityLayer.aspx", ())

    def test_path_check_error_exception(self):
        mock_instance = mock.create_autospec(RoboBrowserMiner)
        browser = mock.MagicMock()
        browser.url = "http://www.test.com/HomeSecurityLayer.aspx"
        mock_instance.browser = browser

        with self.assertRaises(LoginError):
            RoboBrowserMiner.check_error(mock_instance, "/HomeSecurityLayer.aspx",
                                         (("", "INVALID_MFA_INFO", "The details"),))

    def test_default_point_conversion(self):
        user_info = {'scheme_account_id': 1,
                     'status': ''}
        m = RoboBrowserMiner(1, user_info)
        value = m.calculate_point_value(Decimal('100'))
        self.assertEqual(Decimal('0'), value)

    def test_point_conversion(self):
        user_info = {'scheme_account_id': 1,
                     'status': ''}

        m = RoboBrowserMiner(1, user_info)
        m.point_conversion_rate = Decimal('0.5')
        value = m.calculate_point_value(Decimal('25'))
        self.assertEqual(Decimal('12.50'), value)

    def test_format_plural_label(self):
        user_info = {'scheme_account_id': 1,
                     'status': ''}

        m = RoboBrowserMiner(1, user_info)
        self.assertEqual('0 votes', m.format_label(0, 'vote', include_zero_items=True))
        self.assertEqual('1 vote', m.format_label(1, 'vote'))
        self.assertEqual('2 votes', m.format_label(2, 'vote'))

        self.assertEqual('0 classes', m.format_label(0, 'class', 'es', include_zero_items=True))
        self.assertEqual('1 class', m.format_label(1, 'class', 'es'))
        self.assertEqual('2 classes', m.format_label(2, 'class', 'es'))

        self.assertEqual('0 candies', m.format_label(0, 'cand', 'y,ies', include_zero_items=True))
        self.assertEqual('1 candy', m.format_label(1, 'cand', 'y,ies'))
        self.assertEqual('2 candies', m.format_label(2, 'cand', 'y,ies'))

        self.assertEqual('', m.format_label(0, 'vote'))

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


class TestOpenURL(TestCase):
    @httpretty.activate
    def test_open_url_error_status(self):
        httpretty.register_uri(httpretty.GET, "http://foo-api.com/", status=500)
        m_cls = RoboBrowserMiner
        m_cls.proxy = False

        user_info = {'scheme_account_id': 2,
                     'status': ''}

        m = m_cls(1, user_info)
        m.proxy = False
        with self.assertRaises(AgentError):
            m.open_url("http://foo-api.com/")
