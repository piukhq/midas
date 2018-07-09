import unittest
from app.agents.krisflyer import Krisflyer
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS
from app.agents import schemas


class TestKrisflyer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = Krisflyer(*AGENT_CLASS_ARGUMENTS)
        cls.h.attempt_login(CREDENTIALS['krisflyer'])

    def test_login(self):
        self.assertTrue(self.h.is_login_successful)

    def test_balance(self):
        b = self.h.balance()
        schemas.balance(b)

    def test_transactions(self):
        t = self.h.transactions()
        self.assertIsNotNone(t)
        schemas.transactions(t)


class TestKrisflyerFail(unittest.TestCase):

    def test_bad_login(self):
        h = Krisflyer(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '1111111111',
            'pin': '000000',
        }
        with self.assertRaises(LoginError) as e:
            h.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
