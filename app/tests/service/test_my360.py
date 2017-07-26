import unittest

from app.agents.my360 import My360
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS
from app.my360endpoints import SCHEME_API_DICTIONARY
from app.agents import schemas
from decimal import Decimal


class StandardLoginTestsMixin(object):

    @classmethod
    def setUpClass(cls):
        cls.m = My360(1, 1, '')

    def setUp(self):
        self.m.scheme_slug = self.SCHEME_NAME
        self.m.attempt_login(self.SAVED_CREDENTIALS)

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


class StandardLoginFailTestsMixin(object):

    @classmethod
    def setUpClass(cls):
        cls.m = My360(1, 1, '')

    def setUp(self):
        self.m.scheme_slug = self.SCHEME_NAME
        self.credentials = dict(self.SAVED_CREDENTIALS)
        self.credential_type = next(iter(self.credentials))

    def test_login_wrong_barcode(self):
        self.credentials['barcode'] = 'zzzzzzz'
        with self.assertRaises(LoginError) as e:
            self.m.attempt_login(self.credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_long_barcode(self):
        self.credentials['barcode'] = 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'
        with self.assertRaises(LoginError):
            self.m.attempt_login(self.credentials)
        self.assertEqual(self.m.browser.response.status_code, 500)

    def test_wrong_scheme(self):
        SCHEME_API_DICTIONARY['test_wrong'] = 'zzzzzzz'
        self.m.scheme_slug = 'test_wrong'
        with self.assertRaises(LoginError):
            self.m.attempt_login(self.credentials)

    def test_missing_scheme(self):
        SCHEME_API_DICTIONARY['test_none'] = ''
        self.m.scheme_slug = 'test_none'
        with self.assertRaises(ValueError):
            self.m.attempt_login(self.credentials)
        self.assertEqual(self.m.browser.response.status_code, 404)


# Test three my360 agents
class My360LoginUserIDFoodCellarTest(StandardLoginTestsMixin, unittest.TestCase):
    SCHEME_NAME = 'the-food-cellar'
    SAVED_CREDENTIALS = CREDENTIALS['the-food-cellar']


class My360LoginFailUserIDFoodCellarTest(StandardLoginFailTestsMixin, unittest.TestCase):
    SCHEME_NAME = 'the-food-cellar'
    SAVED_CREDENTIALS = CREDENTIALS['the-food-cellar']


class My360LoginUserEmailCafeCopiaTest(StandardLoginTestsMixin, unittest.TestCase):
    SCHEME_NAME = 'cafe-copia'
    SAVED_CREDENTIALS = CREDENTIALS['cafe-copia']


class My360LoginFailUserEmailCafeCopiaTest(StandardLoginFailTestsMixin, unittest.TestCase):
    SCHEME_NAME = 'cafe-copia'
    SAVED_CREDENTIALS = CREDENTIALS['cafe-copia']


class My360LoginUserEmailFitStuffTest(StandardLoginTestsMixin, unittest.TestCase):
    SCHEME_NAME = 'fit-stuff'
    SAVED_CREDENTIALS = CREDENTIALS['fit-stuff']


class My360LoginFailUserEmailFitStuffTest(StandardLoginFailTestsMixin, unittest.TestCase):
    SCHEME_NAME = 'fit-stuff'
    SAVED_CREDENTIALS = CREDENTIALS['fit-stuff']
