import unittest
from app.agents.avis import Avis
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestAvis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Avis(1, 1)
        cls.d.attempt_login(CREDENTIALS['avis'])

    def test_login(self):
        self.assertEqual(self.d.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.d.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.d.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^£\d*\.\d\d$')


class TestAvisFail(unittest.TestCase):
    def test_login_bad_credentials(self):
        d = Avis(1, 1)
        with self.assertRaises(LoginError) as e:
            d.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')


if __name__ == '__main__':
    unittest.main()
