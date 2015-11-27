import unittest
from app.agents.exceptions import LoginError
from app.agents.flying_blue import FlyingBlue
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestFlyingBlue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = FlyingBlue(1, 1)
        cls.m.attempt_login(CREDENTIALS['klm-flying-blue'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestFlyingBlueFail(unittest.TestCase):
    def test_login_bad_username(self):
        m = FlyingBlue(1, 1)
        credentials = {
            'card_number': '0000000000',
            'pin': '0000',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        m = FlyingBlue(1, 1)
        credentials = CREDENTIALS['klm-flying-blue'].copy()
        credentials['pin'] = '0000'

        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
