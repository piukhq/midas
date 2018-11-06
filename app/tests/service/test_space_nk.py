import unittest
from app.agents.exceptions import LoginError
from app.agents.space_nk import SpaceNK
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestSpaceNK(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = SpaceNK(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['space-nk'])

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
        m = SpaceNK(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            m.attempt_login({'barcode': '99999999999999999999'})
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
