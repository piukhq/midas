import unittest
from urllib.parse import urlsplit
from decimal import Decimal
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.agents.british_airways import BritishAirways
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestBritishAirways(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = BritishAirways(*AGENT_CLASS_ARGUMENTS)
        cls.b.attempt_login(CREDENTIALS["british-airways"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/travel/viewaccount/execclub/_gf/en_gb')

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        self.assertEqual(balance['value'], Decimal('0'))
        self.assertEqual(balance['value_label'], '')


class TestBritishAirwaysFail(unittest.TestCase):

    def test_login_fail(self):
        b = BritishAirways(*AGENT_CLASS_ARGUMENTS)
        bad_cred = {
            'username': "00000000",
            'password': '321321321'
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(bad_cred)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
