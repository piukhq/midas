import unittest
from app.agents.victoria import Victoria
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS
from app.agents import schemas


class TestVictoria(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = Victoria(*AGENT_CLASS_ARGUMENTS)
        cls.h.attempt_login(CREDENTIALS['victoria'])

    def test_login(self):
        self.assertTrue(self.h.is_login_successful)

    def test_balance(self):
        b = self.h.balance()
        schemas.balance(b)

    def test_transactions(self):
        t = self.h.transactions()
        self.assertIsNotNone(t)
        schemas.transactions(t)


class TestVictoriaFail(unittest.TestCase):

    def test_bad_login(self):
        h = Victoria(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            h.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
