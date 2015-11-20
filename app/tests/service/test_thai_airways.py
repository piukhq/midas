import unittest
from app.agents.exceptions import LoginError
from app.agents.thai_airways import ThaiAirways
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestThaiAirways(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = ThaiAirways(1, 1)
        cls.m.attempt_login(CREDENTIALS['thai_airways'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^£\d*\.\d\d$')


class TestThaiAirwaysFail(unittest.TestCase):
    def test_login_fail(self):
        m = ThaiAirways(1, 1)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
