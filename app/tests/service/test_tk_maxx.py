import unittest

from app.agents import schemas
from app.agents.exceptions import LoginError
from app.agents.tk_maxx import TKMaxx
from app.tests.service.logins import CREDENTIALS


class TestTKMaxx(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = TKMaxx(1, 1)
        cls.h.attempt_login(CREDENTIALS['tkmaxx'])

    def test_login(self):
        self.assertTrue(self.h.is_login_successful)

    def test_balance(self):
        b = self.h.balance()
        schemas.balance(b)

    def test_transactions(self):
        t = self.h.transactions()
        self.assertIsNotNone(t)
        schemas.transactions(t)


class TestTKMaxxFail(unittest.TestCase):

    def test_bad_login(self):
        h = TKMaxx(1, 1)
        with self.assertRaises(LoginError) as e:
            h.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
