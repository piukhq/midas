import unittest
from app.agents.avios_api import Avios
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS
from app.agents import schemas


class TestAviosAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Avios(1, 1)
        cls.b.attempt_login(CREDENTIALS["avios_api"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        self.assertEqual('', balance['value_label'])


class TestAviosFail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = Avios(1, 1)

    def test_login_bad_card_number(self):
        credentials = {
            'card_number': '0000000000000000',
            'date_of_birth': '11/03/1985',
            'last_name': 'AEAKPN',
        }

        with self.assertRaises(LoginError) as e:
            self.a.attempt_login(credentials)

        self.assertEqual(e.exception.code, 403)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_date_of_birth(self):
        credentials = {
            'card_number': '3081471018143650',
            'date_of_birth': '24/09/1984',
            'last_name': 'AEAKPN',
        }

        with self.assertRaises(LoginError) as e:
            self.a.attempt_login(credentials)

        self.assertEqual(e.exception.code, 403)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_last_name(self):
        credentials = {
            'card_number': '3081471018143650',
            'date_of_birth': '11/03/1985',
            'last_name': 'badbadbad',
        }

        with self.assertRaises(LoginError) as e:
            self.a.attempt_login(credentials)

        self.assertEqual(e.exception.code, 403)
        self.assertEqual(e.exception.name, 'Invalid credentials')
