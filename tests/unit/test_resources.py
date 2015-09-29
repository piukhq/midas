from flask.ext.testing import TestCase
from tests.service import logins
from app import create_app
from unittest import mock


class TestResources(TestCase):
    def create_app(self):
        return create_app(self, )

    @mock.patch('app.publish.Publish.balance', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_user_balances(self, mock_agent_login, mock_publish_balance):
        mock_agent_login.return_value.balance.return_value = {}
        credentials = logins.encrypt("tesco")
        url = "/tesco/balance?credentials={0}&user_id={1}&scheme_account_id={2}".format(credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_publish_balance.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'user_id': 1, 'scheme_account_id': 2})

    @mock.patch('app.publish.Publish.transactions', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_transactions(self, mock_agent_login, mock_publish_transactions):
        mock_agent_login.return_value.transactions.return_value = []
        credentials = logins.encrypt("superdrug")
        url = "/superdrug/transactions?credentials={0}&scheme_account_id={1}".format(credentials, 3)
        response = self.client.get(url)

        self.assertTrue(mock_publish_transactions.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    @mock.patch('app.publish.Publish.transactions', auto_spec=True)
    @mock.patch('app.publish.Publish.balance', auto_spec=True)
    @mock.patch('app.resources.agent_login', auto_spec=True)
    def test_account_overview(self, mock_agent_login, mock_publish_balance, mock_publish_transactions):
        mock_agent_login.return_value.account_overview.return_value = {"balance": {},
                                                                       "transactions": []}
        credentials = logins.encrypt("boots")
        url = "/boots/account_overview?credentials={0}&user_id={1}&scheme_account_id={2}".format(credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_publish_transactions.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'balance': {'scheme_account_id': 2, 'user_id': 1},
                                         'transactions': []})

    def test_bad_agent(self):
        url = "/bad-agent-key/balance"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)