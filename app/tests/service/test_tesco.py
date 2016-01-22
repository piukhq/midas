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
        self.assertEqual(urlsplit(self.b.browser.url).path, '/Clubcard/MyAccount/Home.aspx')

    def test_login_with_card_number(self):
        b = Tesco(1, 1)
        credentials = {
            'email': 'julie.gormley100@gmail.com',
            'password': 'NSHansbrics5',
            'card_number': '634004024051328070'
        }
        b.attempt_login(credentials)
        self.assertEqual(b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(b.browser.url).path, '/Clubcard/MyAccount/Home.aspx')

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestTescoUtil(unittest.TestCase):
    def test_get_card_number(self):
        t = Tesco(1, 1)
        card_number = t.get_card_number('9794024051328070')
        self.assertEqual('634004024051328070', card_number)


class TestTescoFail(unittest.TestCase):
    def test_login_fail(self):
        b = Tesco(1, 1)
        credentials = {
            'barcode': '979999999999999',
            'email': 'magnanimiter@crucem.sustine',
            'password': 'noblesseoblige',
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")

    def test_login_mfa_fail(self):
        b = Tesco(1, 1)
        credentials = CREDENTIALS["tesco-clubcard"]
        credentials['barcode'] = '979999999999999'

        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid mfa")


if __name__ == '__main__':
    unittest.main()
