import unittest
from unittest import mock
from app.agents.avios_api import Avios
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS
from app.agents import schemas


class TestAviosAPI(unittest.TestCase):

    @classmethod
    @mock.patch('app.agents.avios_api.sentry')
    def setUpClass(cls, mock_sentry):
        cls.b = Avios(1, 1)
        cls.b.attempt_login(CREDENTIALS["avios_api"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        self.assertEqual('', balance['value_label'])


class TestAviosFakeLogin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.a = Avios(1, 1)

    @mock.patch('app.agents.avios_api.sentry')
    def test_missing_card_number(self, mock_sentry):
        credentials = {
            CREDENTIALS["avios_api"]["last_name"],
        }

        self.a.attempt_login(credentials)

        mock_sentry.captureMessage.assert_called_with(
            'No card_number in Avios agent! Check the card_number_regex on Hermes.')
        self.assertTrue(self.a.faking_login)

        # confirm that no actual scraping is done now that we're faking logins
        self.assertEqual(self.a.balance().get('points'), 0)


class TestAviosFail(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.a = Avios(1, 1)

    @mock.patch('app.agents.avios_api.sentry')
    def test_login_bad_card_number(self, mock_sentry):
        credentials = CREDENTIALS["avios_api"]
        credentials['card_number'] = '0000000000000000'

        with self.assertRaises(LoginError) as e:
            self.a.attempt_login(credentials)

        self.assertEqual(e.exception.code, 403)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    @mock.patch('app.agents.avios_api.sentry')
    def test_login_bad_last_name(self, mock_sentry):
        credentials = CREDENTIALS["avios_api"]
        credentials['last_name'] = 'badbadbad'

        with self.assertRaises(LoginError) as e:
            self.a.attempt_login(credentials)

        self.assertEqual(e.exception.code, 403)
        self.assertEqual(e.exception.name, 'Invalid credentials')
