from decimal import Decimal
from http import HTTPStatus
from unittest import TestCase, mock

import arrow
import httpretty

from app.agents.base import ApiMiner, create_error_response
from app.agents.exceptions import END_SITE_DOWN, IP_BLOCKED, STATUS_LOGIN_FAILED, AgentError, LoginError
from app.agents.schemas import Transaction


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
        url = "http://someexcitingplace.com"
        httpretty.register_uri(
            httpretty.GET,
            url,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(m, slug=m.scheme_slug, channel=m.channel, error=END_SITE_DOWN),
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
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)
        url = "http://someexcitingplace.com"
        httpretty.register_uri(
            httpretty.GET,
            url,
            status=HTTPStatus.REQUEST_TIMEOUT,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(m, slug=m.scheme_slug, channel=m.channel, error=END_SITE_DOWN),
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
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)
        url = "http://someexcitingplace.com"
        httpretty.register_uri(
            httpretty.GET,
            url,
            status=HTTPStatus.UNAUTHORIZED,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(m, slug=m.scheme_slug, channel=m.channel, error=STATUS_LOGIN_FAILED),
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
        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        m = ApiMiner(0, user_info)
        url = "http://someexcitingplace.com"
        httpretty.register_uri(
            httpretty.GET,
            url,
            status=HTTPStatus.FORBIDDEN,
        )
        expected_calls = [  # The expected call stack for signal, in order
            mock.call("request-fail"),
            mock.call().send(m, slug=m.scheme_slug, channel=m.channel, error=IP_BLOCKED),
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
    @mock.patch.object(ApiMiner, "parse_transaction")
    @mock.patch.object(ApiMiner, "scrape_transactions")
    def test_hash_transactions(self, mock_scrape_transactions, mock_parse_transaction):
        expected_transactions = [
            Transaction(
                date=arrow.now(),
                description="test transaction #1",
                points=Decimal("12.34"),
            ),
            Transaction(
                date=arrow.now(),
                description="test transaction #2",
                points=Decimal("34.56"),
            ),
        ]

        def scrape_transactions() -> list[dict]:
            return [tx._asdict() for tx in expected_transactions]

        def parse_transaction(data: dict) -> Transaction:
            return Transaction(**data)

        mock_scrape_transactions.side_effect = scrape_transactions
        mock_parse_transaction.side_effect = parse_transaction

        user_info = {"scheme_account_id": 194, "status": "", "channel": "com.bink.wallet"}
        agent = ApiMiner(0, user_info)

        transactions = agent.transactions()
        self.assertGreater(len(transactions), 0)
        for transaction in transactions:
            self.assertIsNotNone(transaction.hash)
