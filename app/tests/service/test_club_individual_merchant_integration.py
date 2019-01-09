import unittest
from app.agents.exceptions import LoginError
from app.agents.club_individual_merchant_integration import ClubIndividual
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE


class TestClubIndividual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = ClubIndividual(*AGENT_CLASS_ARGUMENTS, scheme_slug='test-club-individual')
        cls.i.attempt_login(CREDENTIALS['test-club-individual'])

    def test_fetch_balance(self):
        balance = self.i.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.i.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestClubIndividualValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = ClubIndividual(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug='test-club-individual')
        credentials = CREDENTIALS['test-club-individual']
        credentials.pop('merchant_identifier', None)

        cls.i.attempt_login(CREDENTIALS['test-club-individual'])

    def test_validate(self):
        balance = self.i.balance()
        schemas.balance(balance)


class TestClubIndividualFail(unittest.TestCase):
    def test_login_fail(self):
        i = ClubIndividual(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug='test-club-individual')
        credentials = CREDENTIALS['test-club-individual']
        credentials['email'] = 'testloginfail@testbink.com'
        credentials.pop('merchant_identifier', None)

        with self.assertRaises(LoginError) as e:
            i.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
