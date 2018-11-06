import unittest
from app.agents.exceptions import LoginError
from app.agents.gourmet_burger_kitchen import GourmetBurgerKitchen
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestGourmetBurgerKitchen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = GourmetBurgerKitchen(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['gbk-rewards'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^Free (?:burger|side|milkshake)$|^$')


class TestGourmetBurgerKitchenFail(unittest.TestCase):

    def test_login_fail(self):
        m = GourmetBurgerKitchen(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'email': 'bad@bad.com',
            'pin': '0000',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
