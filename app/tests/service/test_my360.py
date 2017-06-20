import unittest
from app.agents.my360 import My360
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS
from app.my360endpoints import SCHEME_API_DICTIONARY
from app.agents import schemas

# scheme_list = list(SCHEME_API_DICTIONARY) testing with two at the moment
scheme_list = ['the-food-cellar', 'hewetts']


class TestMy360API(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = My360(1, 1, 'the-food-cellar')
        cls.m.attempt_login(CREDENTIALS['the-food-cellar'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)
        self.assertTrue(self.m.is_login_successful())
        self.assertIsNotNone(self.m.scheme_slug)

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
        cls.m = My360(1, 1, 'the-food-cellar')

    def test_login_wrong_barcode(self):
        credentials = dict(CREDENTIALS['the-food-cellar'])
        credentials['barcode'] = 'zzzzzzz'
        with self.assertRaises(LoginError) as e:
            self.m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_long_barcode(self):
        credentials = dict(CREDENTIALS['the-food-cellar'])
        credentials['barcode'] = 'zzzzzzzzzzzzzzzzzzzzzzzzz'
        with self.assertRaises(LoginError) as e:
            self.m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_missing_barcode(self):
        credentials = dict(CREDENTIALS['the-food-cellar'])
        credentials['barcode'] = ''
        with self.assertRaises(ValueError):
            self.m.attempt_login(credentials)
        self.assertEqual(self.m.browser.response.status_code, 404)

    def test_wrong_scheme(self):
        credentials = dict(CREDENTIALS['the-food-cellar'])
        SCHEME_API_DICTIONARY['test_wrong'] = 'zzzzzzz'
        self.m.scheme_slug = 'test_wrong'
        with self.assertRaises(ValueError):
            self.m.attempt_login(credentials)
        self.assertEqual(self.m.browser.response.status_code, 401)

    def test_missing_scheme(self):
        credentials = dict(CREDENTIALS['the-food-cellar'])
        SCHEME_API_DICTIONARY['test_none'] = ''
        self.m.scheme_slug = 'test_none'
        with self.assertRaises(ValueError):
            self.m.attempt_login(credentials)
        self.assertEqual(self.m.browser.response.status_code, 404)
