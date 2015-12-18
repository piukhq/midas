import unittest
from app.agents.exceptions import LoginError
from app.agents.starbucks import Starbucks
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestStarbucks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Starbucks(1, 1)
        cls.s.attempt_login(CREDENTIALS['starbucks'])

    def test_balance(self):
        balance = self.s.balance()
        schemas.balance(balance)
        self.assertTrue(balance['points'] >= 0 and balance['points'] <= 15)
        self.assertRegex(balance['value_label'], '^\d+ more stars until a free coffee$')


class TestStarbucksFail(unittest.TestCase):
    def test_login_fail(self):
        s = Starbucks(1, 1)
        credentials = {
            'username': 'bad@bad.com',
            'password': '321321321321',
        }
        with self.assertRaises(LoginError) as e:
            s.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
