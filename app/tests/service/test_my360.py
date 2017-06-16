import unittest
from unittest import mock
from app.agents.my360 import My360
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS
from app.agents import schemas


# TODO: make tests run for all schemes, new test class for checking right scheme?
class TestMy360API(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = My360(1, 1)
        cls.m.attempt_login(CREDENTIALS['food-cellar'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)
        self.assertTrue(self.m.is_login_successful())

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertEqual('', balance['value_label'])

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestMy360Fail(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = My360(1, 1)

    def test_login_wrong_barcode(self):
        credentials = dict(CREDENTIALS['food-cellar'])
        credentials['barcode'] = 'zzzzzzz'
        with self.assertRaises(LoginError) as e:
            self.m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_long_barcode(self):
        credentials = dict(CREDENTIALS['food-cellar'])
        credentials['barcode'] = 'zzzzzzzzzzzzzzzzzzzzzzzzz'
        with self.assertRaises(LoginError) as e:
            self.m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_missing_barcode(self):
        credentials = dict(CREDENTIALS['food-cellar'])
        credentials['barcode'] = ''
        with self.assertRaises(ValueError):
            self.m.attempt_login(credentials)
        self.assertEqual(self.m.browser.response.status_code, 404)

    def test_wrong_scheme(self):
        credentials = dict(CREDENTIALS['food-cellar'])
        credentials['scheme_identifier'] = 'zzzzzzz'
        with self.assertRaises(ValueError) as e:
            self.m.attempt_login(credentials)
        self.assertEqual(self.m.browser.response.status_code, 401)

    def test_missing_scheme(self):
        credentials = dict(CREDENTIALS['food-cellar'])
        credentials['scheme_identifier'] = ''
        with self.assertRaises(ValueError):
            self.m.attempt_login(credentials)
        self.assertEqual(self.m.browser.response.status_code, 404)
