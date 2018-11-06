import unittest
from app.agents.exceptions import LoginError
from app.agents.club_individual import ClubIndividual
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE


class TestClubIndividual(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.e = ClubIndividual(*AGENT_CLASS_ARGUMENTS, scheme_slug='club-individual')
        cls.e.attempt_login(CREDENTIALS['club-individual'])

    def test_fetch_balance(self):
        balance = self.e.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.e.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestClubIndividualValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = ClubIndividual(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug='club-individual')
        cls.e.attempt_login(CREDENTIALS['club-individual'])

    def test_validate(self):
        balance = self.e.balance()
        schemas.balance(balance)


class TestClubIndividualFail(unittest.TestCase):

    def test_login_fail(self):
        eu = ClubIndividual(*AGENT_CLASS_ARGUMENTS, scheme_slug='club-individual')
        credentials = {
            'card_number': '0000000',
        }
        with self.assertRaises(LoginError) as e:
            eu.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
