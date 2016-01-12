import unittest
from app.agents.exceptions import LoginError
from app.agents.house_of_fraser import HouseOfFraser
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestHouseOfFraser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = HouseOfFraser(1, 1)
        cls.m.attempt_login(CREDENTIALS['recognition-reward-card'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestHouseOfFraserFail(unittest.TestCase):
    def test_login_fail(self):
        m = HouseOfFraser(1, 1)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
