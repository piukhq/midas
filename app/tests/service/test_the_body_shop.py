import unittest
from app.agents.exceptions import LoginError
from app.agents.the_body_shop import TheBodyShop
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestTheBodyShop(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = TheBodyShop(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['love-your-body'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestTheBodyShopFail(unittest.TestCase):

    def test_login_bad_email(self):
        m = TheBodyShop(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            "email": "bad@bad.com",
            "password": "Loyalty2016",
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        m = TheBodyShop(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            "email": "Dkmudway@gmail.com",
            "password": "badbadbadbad",
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
