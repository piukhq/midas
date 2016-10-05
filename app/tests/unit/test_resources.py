import builtins
from unittest.mock import mock_open
from flask.ext.testing import TestCase
from app.agents.avios import Avios
from app.agents.exceptions import AgentError, RetryLimitError, RETRY_LIMIT_REACHED, LoginError, STATUS_LOGIN_FAILED,\
    errors
from app.resources import agent_login
from app.tests.service import logins
from app import create_app, AgentException
from unittest import mock
from decimal import Decimal
from app import publish


class TestResources(TestCase):
    TESTING = True

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

    @mock.patch('app.publish.balance', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    def test_balance_none_exception(self, mock_pool, mock_agent_login, mock_publish_balance):
        mock_publish_balance.return_value = None
        credentials = logins.encrypt("tesco-clubcard")
        url = "/tesco-clubcard/balance?credentials={0}&user_id={1}&scheme_account_id={2}".format(credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json)

    @mock.patch('app.publish.balance', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    def test_balance_unknown_error(self, mock_pool, mock_agent_login, mock_publish_balance):
        mock_publish_balance.side_effect = Exception('test error')
        credentials = logins.encrypt("tesco-clubcard")
        url = "/tesco-clubcard/balance?credentials={0}&user_id={1}&scheme_account_id={2}".format(credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 520)
        self.assertEqual(response.json['name'], 'Unknown Error')
        self.assertEqual(response.json['message'], 'test error')
        self.assertEqual(response.json['code'], 520)

    @mock.patch('app.publish.transactions', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    def test_transactions(self, mock_pool, mock_agent_login, mock_publish_transactions):
        mock_publish_transactions.return_value = [{"points": Decimal("10.00")}]
        credentials = logins.encrypt("superdrug")
        url = "/health-beautycard/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(
            credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [{'points': 10.0}, ])

    @mock.patch('app.publish.transactions', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    def test_transactions_none_exception(self, mock_pool, mock_agent_login, mock_publish_transactions):
        mock_publish_transactions.return_value = None
        credentials = logins.encrypt("superdrug")
        url = "/health-beautycard/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(
            credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json)

    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    @mock.patch('app.publish.transactions', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_transactions_unknown_error(self, mock_agent_login, mock_publish_transactions, mock_pool):
        mock_publish_transactions.side_effect = Exception('test error')
        credentials = logins.encrypt("superdrug")
        url = "/health-beautycard/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(
            credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 520)
        self.assertEqual(response.json['name'], 'Unknown Error')
        self.assertEqual(response.json['message'], 'test error')
        self.assertEqual(response.json['code'], 520)

    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    @mock.patch('app.publish.transactions', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_transactions_login_error(self, mock_agent_login, mock_publish_transactions, mock_pool):
        mock_publish_transactions.side_effect = LoginError(STATUS_LOGIN_FAILED)
        credentials = logins.encrypt("superdrug")
        url = "/health-beautycard/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(
            credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json['name'], errors[STATUS_LOGIN_FAILED]['name'])
        self.assertEqual(response.json['message'], errors[STATUS_LOGIN_FAILED]['message'])
        self.assertEqual(response.json['code'], errors[STATUS_LOGIN_FAILED]['code'])

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
        self.assertEqual(response.json, {'balance': {}, 'transactions': []})

    def test_bad_agent(self):
        url = "/bad-agent-key/transactions?credentials=234&scheme_account_id=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    def test_bad_agent_updates_status(self, mock_submit):
        url = '/bad-agent-key/balance?credentials=234&scheme_account_id=1&user_id=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        mock_submit.assert_called_with(publish.status, 1, 10, None)

    def test_bad_parameters(self):
        url = "/tesco-clubcard/transactions?credentials=234"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {"message": "Missing required query parameter \'scheme_account_id\'"})

    @mock.patch('app.resources.retry', autospec=True)
    @mock.patch.object(Avios, 'attempt_login')
    def test_agent_login_retry_limit(self, mock_attempt_login, mock_retry):
        mock_attempt_login.side_effect = RetryLimitError(RETRY_LIMIT_REACHED)
        with self.assertRaises(AgentException):
            agent_login(Avios, {}, 5)
        self.assertTrue(mock_retry.max_out_count.called)

    @mock.patch('app.resources.retry', autospec=True)
    @mock.patch.object(Avios, 'attempt_login')
    def test_agent_login_inc(self, mock_attempt_login, mock_retry):
        mock_attempt_login.side_effect = AgentError(RETRY_LIMIT_REACHED)
        with self.assertRaises(AgentException) as e:
            agent_login(Avios, {}, 5)
        self.assertTrue(mock_retry.inc_count.called)
        self.assertEqual(e.exception.args[0].message, 'You have reached your maximum amount '
                                                      'of login tries please wait 15 minutes.')
        self.assertEqual(e.exception.args[0].code, 429)
        self.assertEqual(e.exception.args[0].name, 'Retry limit reached')

    @mock.patch.object(builtins, 'open', mock_open(read_data='<xml></xml>'))
    def test_test_results(self):
        url = "/test_results"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'<xml></xml>')
        self.assertEqual(response.content_type, 'text/xml')

    def test_tier2_agent_questions(self):
        resp = self.client.post('/agent_questions', data={
            'scheme_slug': 'advantage-card',
            'username': 'test-username',
            'password': 'test-password',
        })

        self.assertEqual(resp.status_code, 200)
        self.assertIn('username', resp.json)
        self.assertIn('password', resp.json)
        self.assertEqual(resp.json['username'], 'test-username')
        self.assertEqual(resp.json['password'], 'test-password')
