import unittest
from app.agents.tesco import Tesco
from urllib.parse import urlsplit
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS
from app.agents.exceptions import LoginError


class TestTesco(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = Tesco(1, 1)
        cls.b.attempt_login(CREDENTIALS["tesco-clubcard"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/Clubcard/MyAccount/Home/Home')

    def test_login_with_card_number(self):
        b = Tesco(1, 1)
        credentials = {
            'email': 'julie.gormley100@gmail.com',
            'password': 'NSHansbrics5',
            'card_number': '634004024051328070'
        }
        b.attempt_login(credentials)
        self.assertEqual(b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(b.browser.url).path, '/Clubcard/MyAccount/Home/Home')

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestTescoFail(unittest.TestCase):

    def test_login_fail(self):
        b = Tesco(1, 1)
        credentials = {
            'card_number': '979999999999999',
            'email': 'magnanimiter@crucem.sustine',
            'password': 'noblesseoblige',
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")

    def test_login_bad_mfa(self):
        b = Tesco(1, 1)
        credentials = {
            'card_number': '979999999999999',
            'email': 'julie.gormley100@gmail.com',
            'password': 'NSHansbrics5',
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid mfa")


if __name__ == '__main__':
    unittest.main()
