import unittest
from urllib.parse import urlsplit
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.agents.british_airways import BritishAirways
from app.tests.service.logins import CREDENTIALS


class TestBritishAirways(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = BritishAirways(1, 1)
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
        self.assertRegex(balance['value_label'], '^£\d*\.\d\d$')


class TestBritishAirwaysFail(unittest.TestCase):
    def test_login_fail(self):
        b = BritishAirways(1, 1)
        bad_cred = {
            'card_number': "00000000",
            'password': '321321321'
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(bad_cred)
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
