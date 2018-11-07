import unittest
from app.agents.exceptions import LoginError
from app.agents.superdrug import Superdrug
from urllib.parse import urlsplit
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestSuperDrug(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Superdrug(*AGENT_CLASS_ARGUMENTS)
        cls.b.attempt_login(CREDENTIALS["health-beautycard"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertNotEqual(urlsplit(self.b.browser.url).query, 'loginError=true')

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestSuperDrugFail(unittest.TestCase):
    def test_login_fail(self):
        b = Superdrug(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
