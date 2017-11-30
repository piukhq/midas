import builtins
from unittest.mock import mock_open
from flask.ext.testing import TestCase
from app.agents.avios import Avios
from app.agents.harvey_nichols import HarveyNichols
from app.agents.exceptions import AgentError, RetryLimitError, RETRY_LIMIT_REACHED, LoginError, STATUS_LOGIN_FAILED,\
    errors, RegistrationError, NO_SUCH_RECORD
from app.resources import agent_login, registration, agent_register
from app.tests.service import logins
from app.encryption import AESCipher
from app import create_app, AgentException
from settings import AES_KEY
from unittest import mock
from decimal import Decimal
from app import publish

import json


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
    @mock.patch.object(Avios, 'identifier')
    def test_agent_login_inc(self, mock_identifier, mock_attempt_login, mock_retry):
        mock_identifier.value = None
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

    @mock.patch('app.resources.thread_pool_executor.submit', autospec=True)
    def test_register_view(self, mock_pool):
        credentials = logins.encrypt("harvey-nichols")
        url = "/harvey-nichols/register"
        data = {
            "scheme_account_id": 2,
            "user_id": 4,
            "credentials": credentials
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")

        self.assertTrue(mock_pool.called)
        self.assertEqual(response.json, {'message': 'success'})

    @mock.patch.object(HarveyNichols, 'register')
    @mock.patch('app.agents.base.put', autospec=True)
    def test_agent_register_success(self, mock_put, mock_register):
        mock_register.return_value = {'message': 'success'}
        scheme_slug = "harvey-nichols"
        scheme_account_id = 2

        agent_register(HarveyNichols, {}, scheme_account_id, scheme_slug, 1)

        self.assertTrue(mock_register.called)
        self.assertFalse(mock_put.called)

    @mock.patch.object(HarveyNichols, 'register')
    @mock.patch('app.agents.base.put', autospec=False)
    def test_agent_register_fail(self, mock_put, mock_register):
        mock_register.side_effect = RegistrationError(STATUS_LOGIN_FAILED)
        scheme_slug = "harvey-nichols"
        scheme_account_id = 2

        agent_register(HarveyNichols, {}, scheme_account_id, scheme_slug, 1)

        self.assertTrue(mock_register.called)
        self.assertTrue(mock_put.called)

    @mock.patch('app.publish.balance', auto_spec=True)
    @mock.patch('app.publish.status', auto_spec=True)
    @mock.patch('app.resources.publish_transactions', auto_spec=True)
    @mock.patch('app.resources.agent_register', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_registration(self, mock_publish_balance, mock_publish_status, mock_publish_transaction,
                          mock_agent_register, mock_agent_login):
        scheme_slug = "harvey-nichols"
        credentials = logins.encrypt(scheme_slug)
        scheme_account_id = 2
        user_id = 4

        result = registration(scheme_slug, scheme_account_id, credentials, user_id, tid=None)

        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_publish_transaction.called)
        self.assertTrue(mock_publish_status.called)
        self.assertTrue(mock_agent_register.called)
        self.assertTrue(mock_agent_login.called)
        self.assertEqual(result, True)

    @mock.patch('app.resources.retry', autospec=True)
    @mock.patch.object(HarveyNichols, 'attempt_login')
    def test_agent_login_success(self, mock_login, mock_retry):
        mock_login.return_value = {'message': 'success'}

        agent_login(HarveyNichols, {}, 2, "harvey-nichols")
        self.assertTrue(mock_login.called)

    @mock.patch('app.resources.retry', autospec=True)
    @mock.patch.object(HarveyNichols, 'attempt_login')
    def test_agent_login_system_fail_(self, mock_login, mock_retry):
        mock_login.side_effect = AgentError(NO_SUCH_RECORD)

        with self.assertRaises(AgentError):
            agent_login(HarveyNichols, {}, 2, "harvey-nichols", from_register=True)
        self.assertTrue(mock_login.called)

    @mock.patch('app.resources.retry', autospec=True)
    @mock.patch.object(HarveyNichols, 'attempt_login')
    def test_agent_login_user_fail_(self, mock_login, mock_retry):
        mock_login.side_effect = AgentError(STATUS_LOGIN_FAILED)

        with self.assertRaises(AgentException):
            agent_login(HarveyNichols, {}, 2, "harvey-nichols")
        self.assertTrue(mock_login.called)

    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    @mock.patch('app.publish.balance', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=False)
    def test_balance_updates_hermes_if_agent_sets_identifier(self, mock_login, mock_publish_balance, mock_pool):
        mock_login.return_value = mock.MagicMock()
        mock_login().identifier = True
        credentials = {
            "username": "la@loyaltyangels.com",
            "password": "YSHansbrics6",
        }
        aes = AESCipher(AES_KEY.encode())
        credentials = aes.encrypt(json.dumps(credentials)).decode()

        url = "/harvey-nichols/balance?credentials={0}&user_id={1}&scheme_account_id={2}".format(credentials, 1, 2)
        self.client.get(url)

        self.assertTrue(mock_login.called)
        self.assertTrue(mock_login().update_scheme_account.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_pool.called)

    @mock.patch('app.resources.thread_pool_executor.submit', auto_spec=True)
    @mock.patch('app.publish.balance', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=False)
    def test_balance_does_not_update_hermes_if_agent_does_not_set_identifier(self, mock_login, mock_publish_balance,
                                                                             mock_pool):
        mock_login.return_value = mock.MagicMock()
        mock_login().identifier = None
        credentials = {
            "username": "la@loyaltyangels.com",
            "password": "YSHansbrics6",
        }
        aes = AESCipher(AES_KEY.encode())
        credentials = aes.encrypt(json.dumps(credentials)).decode()

        url = "/harvey-nichols/balance?credentials={0}&user_id={1}&scheme_account_id={2}".format(credentials, 1, 2)
        self.client.get(url)

        self.assertTrue(mock_login.called)
        self.assertFalse(mock_login().update_scheme_account.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_pool.called)
