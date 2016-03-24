import unittest
from app.agents.exceptions import LoginError
from app.agents.gourmet_burger_kitchen import GourmetBurgerKitchen
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestGourmetBurgerKitchen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = GourmetBurgerKitchen(1, 1)
        cls.m.attempt_login(CREDENTIALS['gbk-rewards'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        with self.assertRaises(NotImplementedError) as e:
            self.m.transactions()

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^Free (?:burger|side|milkshake)$|^$')


class TestGourmetBurgerKitchenFail(unittest.TestCase):
    def test_login_fail(self):
        m = GourmetBurgerKitchen(1, 1)
        credentials = {
            'email': 'bad@bad.com',
            'pin': '0000',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
