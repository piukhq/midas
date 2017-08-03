import unittest
from app.agents.exceptions import LoginError
from app.agents.rspb import RSPB
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestRSPB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = RSPB(1, 1)
        cls.m.attempt_login(CREDENTIALS['rspb'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestRSPBFail(unittest.TestCase):
    def test_login_fail(self):
        m = RSPB(1, 1)
        credentials = CREDENTIALS['bad']

        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
