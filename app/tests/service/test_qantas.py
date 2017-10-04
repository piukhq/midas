import unittest

from app.agents.exceptions import LoginError
from app.agents.qantas import Qantas
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestQantas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Qantas(1, 1)
        cls.m.attempt_login(CREDENTIALS['qantas'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 201)
        content = self.m.browser.response.json()
        self.assertEqual(content['auth']['status'], 'AUTHENTICATED')

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestQantasFail(unittest.TestCase):

    def test_login_wrong_pin_fail(self):
        miner = Qantas(1, 1)
        credentials = {
            "card_number": CREDENTIALS['qantas']['card_number'],
            "last_name": CREDENTIALS['qantas']['last_name'],
            "pin": '9999',
        }
        with self.assertRaises(LoginError) as e:
            miner.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
