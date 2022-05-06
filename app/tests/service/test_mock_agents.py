import unittest

from app.exceptions import StatusLoginFailedError
from app.agents.mock_agents import MockAgentHN, MockAgentIce
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS


class TestHN(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = MockAgentHN(*AGENT_CLASS_ARGUMENTS)
        credentials = {"email": "sixdigitpoints@testbink.com", "password": "pa$$w&rd01!"}
        cls.b.attempt_login(credentials)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)

    def test_balance(self):
        balance = self.b.balance()
        self.assertIsNotNone(balance)
        self.assertTrue(self.b.identifier)


class TestHNFail(unittest.TestCase):
    def test_login_fail(self):
        b = MockAgentHN(*AGENT_CLASS_ARGUMENTS)
        credentials = {"card_number": "000001", "email": "notzero@testbink.com", "password": "Password01"}
        with self.assertRaises(StatusLoginFailedError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


class TestIce(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = MockAgentIce(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            "card_number": "6332040050607087777",
            "last_name": "seven-digits, smith's",
            "postcode": "mp7 1bb",
        }
        cls.b.attempt_login(credentials)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)

    def test_balance(self):
        balance = self.b.balance()
        self.assertIsNotNone(balance)


class TestIceFail(unittest.TestCase):
    def test_login_fail(self):
        b = MockAgentIce(*AGENT_CLASS_ARGUMENTS)
        credentials = {"card_number": "000000", "last_name": "notzero", "postcode": "RG0 0aa"}
        with self.assertRaises(StatusLoginFailedError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == "__main__":
    unittest.main()
