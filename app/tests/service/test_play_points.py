import unittest
from app.agents.play_points import PlayPoints
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS
from app.agents import schemas


class TestPlayPoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = PlayPoints(1, 1)
        cls.h.attempt_login(CREDENTIALS['play-points'])

    def test_login(self):
        self.assertTrue(self.h.is_login_successful)

    def test_balance(self):
        b = self.h.balance()
        schemas.balance(b)

    def test_transactions(self):
        t = self.h.transactions()
        self.assertIsNotNone(t)
        schemas.transactions(t)


class TestPlayPointsFail(unittest.TestCase):

    def test_bad_login(self):
        h = PlayPoints(1, 1)
        credentials = {
            "username": "bad",
            "password": "0000"
        }
        with self.assertRaises(LoginError) as e:
            h.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
