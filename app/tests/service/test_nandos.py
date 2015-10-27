import unittest
from app.agents.exceptions import LoginError
from app.agents.nandos import Nandos
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestNandos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = Nandos(1, 1, False)
        cls.n.attempt_login(CREDENTIALS['nandos'])

    def test_login(self):
        self.assertEqual(self.n.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.n.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.n.balance()
        schemas.balance(balance)


class TestNandosFail(unittest.TestCase):
    def test_login_fail(self):
        n = Nandos(1, 1, False)
        with self.assertRaises(LoginError) as e:
            n.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
