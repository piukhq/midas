import unittest
from app.agents.exceptions import LoginError
from app.agents.merchant_api_generic import MerchantAPIGeneric
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE


class TestIceland(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS, scheme_slug='iceland-bonus-card')
        cls.i.attempt_login(CREDENTIALS['iceland-bonus-card'])

    def test_fetch_balance(self):
        balance = self.i.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.i.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestMerchantAPIGenericValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug='iceland-bonus-card')
        cls.i.attempt_login(CREDENTIALS['iceland-bonus-card'])

    def test_validate(self):
        balance = self.i.balance()
        schemas.balance(balance)


class TestMerchantAPIGenericFail(unittest.TestCase):
    # merchant api framework doesnt have an invalid credentials error code so it raises an unknown exception
    def test_login_fail(self):
        i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug='iceland-bonus-card')
        credentials = CREDENTIALS['iceland-bonus-card']
        credentials['last_name'] = 'midastest'
        with self.assertRaises(LoginError) as e:
            i.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'An unknown error has occurred')


if __name__ == '__main__':
    unittest.main()
