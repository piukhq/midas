import unittest
from app.agents.exceptions import LoginError
from app.agents.air_asia import AirAsia
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestAirAsia(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = AirAsia(1, 1)
        cls.m.attempt_login(CREDENTIALS['big-rewards'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestAirAsiaFail(unittest.TestCase):

    def test_login_fail(self):
        m = AirAsia(1, 1)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
