import unittest
from app.agents.test_agent import TestAgentCI, TestAgentHN, TestAgentIce
from app.agents import schemas
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS
from app.agents.exceptions import LoginError


class TestCI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = TestAgentCI(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '666666',
            'email': 'six@testbink.com'
        }
        cls.b.attempt_login(credentials)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)
        print(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        print(balance)


class TestCIFail(unittest.TestCase):

    def test_login_fail(self):
        b = TestAgentCI(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '000000',
            'email': 'notzero@testbink.com'
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


class TestHN(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = TestAgentHN(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '123456',
            'email': 'sixdigitpoints@testbink.com',
            'password': 'Password01'
        }
        cls.b.attempt_login(credentials)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)
        print(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        print(balance)


class TestHNFail(unittest.TestCase):

    def test_login_fail(self):
        b = TestAgentHN(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '000001',
            'email': 'zero@testbink.com',
            'password': 'Password01'
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


class TestIce(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = TestAgentIce(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '234567',
            'last_name': 'Smith',
            'postcode': 'mp7 1bb'
        }
        cls.b.attempt_login(credentials)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)
        print(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        print(balance)


class TestIceFail(unittest.TestCase):

    def test_login_fail(self):
        b = TestAgentIce(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '000000',
            'last_name': 'notzero',
            'postcode': 'RG0 0aa'
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
