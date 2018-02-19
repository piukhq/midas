import unittest
from app.agents.exceptions import LoginError
from app.agents.space_nk import SpaceNK
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestSpaceNK(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = SpaceNK(1, 1)
        cls.m.attempt_login(CREDENTIALS['space_nk'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestSpaceNKFail(unittest.TestCase):

    def test_login_fail(self):
        m = SpaceNK(1, 1)
        with self.assertRaises(LoginError) as e:
            m.attempt_login({'barcode': '99999999999999999999'})
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
