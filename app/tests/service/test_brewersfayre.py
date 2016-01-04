import unittest
from app.agents.exceptions import LoginError
from app.agents.brewersfayre import BrewersFayre
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestBrewersFayre(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = BrewersFayre(1, 1)
        cls.t.attempt_login(CREDENTIALS['bonus-club'])

    def test_login(self):
        self.assertEqual(self.t.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.t.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.t.balance()
        schemas.balance(balance)


class TestBrewersFayreFail(unittest.TestCase):
    def test_login_fail(self):
        t = BrewersFayre(1, 1)
        with self.assertRaises(LoginError) as e:
            t.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
