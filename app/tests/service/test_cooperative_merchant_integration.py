import json
import unittest
from app.agents.cooperative_merchant_integration import Cooperative
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE
from gaia.user_token import UserTokenStore
from settings import REDIS_URL


class TestCooperative(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = Cooperative(*AGENT_CLASS_ARGUMENTS, scheme_slug='test-co-op')
        cls.c.attempt_login(CREDENTIALS['the-co-operative-membership'])
        cls.token_store = UserTokenStore(REDIS_URL)

    def test_transactions(self):
        transactions = self.c.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.c.balance()
        schemas.balance(balance)

    def test_auth_token_storage(self):
        data = json.loads(self.token_store.get(1))

        self.assertNotEqual(data.get('token'), None)
        self.assertNotEqual(data.get('timestamp'), None)

    def tearDownClass(cls):
        cls.token_store.delete(1)


class TestCooperativeValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = Cooperative(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug='the-co-operative-membership')
        credentials = CREDENTIALS['the-co-operative-membership']
        credentials.pop('merchant_identifier', None)

        cls.i.attempt_login(CREDENTIALS['the-co-operative-membership'])

    def test_validate(self):
        balance = self.i.balance()
        schemas.balance(balance)


if __name__ == '__main__':
    unittest.main()
