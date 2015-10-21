import unittest
from app.agents.exceptions import LoginError
from app.agents.esprit import Esprit
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestEsprit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = Esprit(1, 1)
        cls.e.attempt_login(CREDENTIALS['esprit'])

    def test_login(self):
        self.assertEqual(self.e.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.e.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.e.balance()
        schemas.balance(balance)


class TestEspritFail(unittest.TestCase):
    def test_login_fail(self):
        es = Esprit(1, 1)
        with self.assertRaises(LoginError) as e:
            es.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
