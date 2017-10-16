import unittest
from app.agents.exceptions import LoginError
from app.agents.club_individual import ClubIndividual
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestClubIndividual(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.e = ClubIndividual(1, 1)
        cls.e.attempt_login(CREDENTIALS['club_individual'])

    def test_login(self):
        self.assertTrue(self.e.is_login_successful)

    def test_balance(self):
        balance = self.e.balance()
        schemas.balance(balance)


class TestClubIndividualFail(unittest.TestCase):

    def test_login_fail(self):
        eu = ClubIndividual(1, 1)
        credentials = {
            'card_number': '0000000',
        }
        with self.assertRaises(LoginError) as e:
            eu.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
