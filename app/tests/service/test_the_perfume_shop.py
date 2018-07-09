import unittest
from app.agents.exceptions import LoginError
from app.agents.the_perfume_shop import ThePerfumeShop
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestThePerfumeShop(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = ThePerfumeShop(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['the-perfume-shop'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestThePerfumeShopFail(unittest.TestCase):

    def test_login_fail(self):
        m = ThePerfumeShop(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
