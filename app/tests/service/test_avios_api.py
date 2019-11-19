import unittest
from app.agents.avios_api import Avios
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS
from app.agents import schemas


class TestAviosAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = Avios(*AGENT_CLASS_ARGUMENTS)
        cls.b.attempt_login(CREDENTIALS['avios'])

    def test_login(self):
        self.assertEqual(self.b.response.status_code, 200)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        self.assertEqual('', balance['value_label'])

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestAviosFakeLogin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.a = Avios(*AGENT_CLASS_ARGUMENTS)

    def test_missing_card_number(self):
        credentials = {
            'last_name': CREDENTIALS['avios']['last_name'],
        }

        self.a.attempt_login(credentials)

        self.assertTrue(self.a.faking_login)

        # confirm that no actual scraping is done now that we're faking logins
        self.assertEqual(self.a.balance().get('points'), 0)


class TestAviosFail(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.a = Avios(*AGENT_CLASS_ARGUMENTS)

    def test_login_bad_card_number(self):
        credentials = CREDENTIALS['avios']
        credentials['card_number'] = '0000000000000000'

        with self.assertRaises(LoginError) as e:
            self.a.attempt_login(credentials)

        self.assertEqual(e.exception.code, 403)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_last_name(self):
        credentials = CREDENTIALS['avios']
        credentials['last_name'] = 'badbadbad'

        with self.assertRaises(LoginError) as e:
            self.a.attempt_login(credentials)

        self.assertEqual(e.exception.code, 403)
        self.assertEqual(e.exception.name, 'Invalid credentials')
