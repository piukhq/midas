from unittest.mock import mock_open

import builtins
from flask.ext.testing import TestCase

from app.agents.avios import Avios
from app.agents.exceptions import AgentError, RetryLimitError, RETRY_LIMIT_REACHED
from app.resources import agent_login
from app.tests.service import logins
from app import create_app
from unittest import mock
from decimal import Decimal


class TestResources(TestCase):
    def create_app(self):
        return create_app(self, )

    @mock.patch('app.publish.balance', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    def test_user_balances(self, mock_pool, mock_agent_login, mock_publish_balance):
        mock_publish_balance.return_value = {'user_id': 2, 'scheme_account_id': 4}
        credentials = logins.encrypt("tesco-clubcard")
        url = "/tesco-clubcard/balance?credentials={0}&user_id={1}&scheme_account_id={2}".format(credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'user_id': 2, 'scheme_account_id': 4})

    @mock.patch('app.publish.transactions', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_transactions(self, mock_agent_login, mock_publish_transactions):
        mock_publish_transactions.return_value = [{"points": Decimal("10.00")}]
        credentials = logins.encrypt("superdrug")
        url = "/health-beautycard/transactions?credentials={0}&scheme_account_id={1}".format(credentials, 3)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [{'points': 10.0}, ])

    @mock.patch('app.publish.transactions', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_transactions_none(self, mock_agent_login, mock_publish_transactions):
        mock_publish_transactions.return_value = None
        credentials = logins.encrypt("superdrug")
        url = "/health-beautycard/transactions?credentials={0}&scheme_account_id={1}".format(credentials, 3)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, None)

    @mock.patch('app.publish.transactions', auto_spec=True)
    @mock.patch('app.publish.balance', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_account_overview(self, mock_agent_login, mock_publish_balance, mock_publish_transactions):
        mock_agent_login.return_value.account_overview.return_value = {"balance": {},
                                                                       "transactions": []}
        credentials = logins.encrypt("advantage-card")
        url = "/advantage-card/account_overview?credentials={0}&user_id={1}&scheme_account_id={2}".format(
            credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_publish_transactions.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json,  {'balance': {}, 'transactions': []})

    def test_bad_agent(self):
        url = "/bad-agent-key/transaction?credentials=234&scheme_account_id=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_bad_parameters(self):
        url = "/tesco-clubcard/transactions?credentials=234"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {"message": "Missing required query parameter \'scheme_account_id\'"})

    @mock.patch('app.resources.agent_abort', autospec=True)
    @mock.patch('app.resources.retry', autospec=True)
    @mock.patch.object(Avios, 'attempt_login')
    def test_agent_login_retry_limit(self, mock_attempt_login, mock_retry, mock_agent_abort):
        mock_attempt_login.side_effect = RetryLimitError(RETRY_LIMIT_REACHED)
        agent_login(Avios, {}, 5)
        self.assertTrue(mock_retry.max_out_count.called)
        self.assertTrue(mock_agent_abort.called)

    @mock.patch('app.resources.agent_abort', autospec=True)
    @mock.patch('app.resources.retry', autospec=True)
    @mock.patch.object(Avios, 'attempt_login')
    def test_agent_login_inc(self, mock_attempt_login, mock_retry, mock_agent_abort):
        mock_attempt_login.side_effect = AgentError(RETRY_LIMIT_REACHED)
        agent_login(Avios, {}, 5)
        self.assertTrue(mock_retry.inc_count.called)
        self.assertTrue(mock_agent_abort.called)

    @mock.patch.object(builtins, 'open', mock_open(read_data='<xml></xml>'))
    def test_test_results(self):
        url = "/test_results"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'<xml></xml>')
        self.assertEqual(response.content_type, 'text/xml')
