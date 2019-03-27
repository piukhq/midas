import json
import unittest
from unittest.mock import MagicMock, patch

from app.agents.cooperative_merchant_integration import Cooperative
from app.agents import schemas
from app.agents.exceptions import LoginError, UnauthorisedError, VALIDATION, STATUS_LOGIN_FAILED, \
    ACCOUNT_ALREADY_EXISTS, PRE_REGISTERED_CARD, CARD_NOT_REGISTERED, UNKNOWN
from app.configuration import Configuration
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE
from gaia.user_token import UserTokenStore
from settings import REDIS_URL


class TestCooperative(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = Cooperative(*AGENT_CLASS_ARGUMENTS, scheme_slug='test-co-op')
        credentials = CREDENTIALS['test-co-op']

        cls.token_store = UserTokenStore(REDIS_URL)
        for scope in cls.c.journey_to_scope.values():
            cls.token_store.delete(scope)

        cls.c.attempt_login(credentials)

    def test_transactions(self):
        transactions = self.c.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.c.balance()
        schemas.balance(balance)

    def test_auth_token_storage(self):
        update_scope = self.c.journey_to_scope[Configuration.UPDATE_HANDLER]
        data = json.loads(self.token_store.get(update_scope))

        self.assertNotEqual(data.get('token'), None)
        self.assertNotEqual(data.get('timestamp'), None)

    @patch.object(Cooperative, '_get_auth_token')
    @patch.object(Cooperative, '_refresh_auth_token')
    def test_get_auth_headers_gets_token_if_not_in_token_store(self, mock_refresh_token, mock_get_token):
        mock_refresh_token.return_value = {'token': 'refreshed_token', 'timestamp': 1234556789}
        mock_get_token.side_effect = self.token_store.NoSuchToken

        expected_result = {
            'Authorization': 'Bearer refreshed_token',
            'X-API-KEY': Cooperative.API_KEY
        }

        result = self.c._get_auth_headers('check_card')

        self.assertTrue(mock_get_token.called)
        self.assertTrue(mock_refresh_token.called)
        self.assertEqual(result, expected_result)

    @patch.object(Cooperative, '_get_auth_token')
    @patch.object(Cooperative, '_refresh_auth_token')
    def test_get_auth_headers_refreshes_expired_token(self, mock_refresh_token, mock_get_token):
        mock_refresh_token.return_value = {'token': 'refreshed_token', 'timestamp': 1234556789}
        mock_get_token.return_value = {'token': 'stored_token', 'timestamp': 1234556789}

        expected_result = {
            'Authorization': 'Bearer refreshed_token',
            'X-API-KEY': Cooperative.API_KEY
        }

        result = self.c._get_auth_headers('check_card')

        self.assertTrue(mock_get_token.called)
        self.assertTrue(mock_refresh_token.called)
        self.assertEqual(result, expected_result)
        self.assertFalse(result)

    @patch('app.agents.cooperative_merchant_integration.requests.get')
    @patch('app.agents.cooperative_merchant_integration.Configuration')
    @patch.object(Cooperative, '_get_auth_headers')
    def test_card_is_temporary_success(self, mock_get_auth_headers, mock_config, mock_request):
        conf = MagicMock()
        conf.merchant_url = "{card_number}"
        mock_config.return_value = conf
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_resp.json.return_value = {'isTemporary': False}
        mock_request.return_value = mock_resp
        result = self.c._card_is_temporary('123')

        self.assertEqual(result, False)

        mock_resp.json.return_value = {'isTemporary': True}
        mock_request.return_value = mock_resp
        result = self.c._card_is_temporary('123')

        self.assertEqual(result, True)

        self.assertTrue(mock_get_auth_headers.called)
        self.assertTrue(mock_config.called)
        self.assertTrue(mock_request.called)

    @patch('app.agents.cooperative_merchant_integration.requests.get')
    @patch('app.agents.cooperative_merchant_integration.Configuration')
    @patch.object(Cooperative, '_get_auth_headers')
    def test_card_is_temporary_raises_invalid_card_number_on_404(self, mock_get_auth_headers, mock_config,
                                                                 mock_request):
        conf = MagicMock()
        conf.merchant_url = "{card_number}"
        mock_config.return_value = conf
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_resp.json.return_value = {'isTemporary': False}
        mock_request.return_value = mock_resp

        with self.assertRaises(LoginError) as e:
            self.c._card_is_temporary('123')

        self.assertEqual(e.exception.message, 'Invalid card_number')
        self.assertTrue(mock_get_auth_headers.called)
        self.assertTrue(mock_config.called)
        self.assertTrue(mock_request.called)

    @patch.object(Cooperative, 'token_store')
    @patch('app.agents.cooperative_merchant_integration.requests.get')
    @patch('app.agents.cooperative_merchant_integration.Configuration')
    @patch.object(Cooperative, '_get_auth_headers')
    def test_card_is_temporary_raises_unauthorised_error_on_401(self, mock_get_auth_headers, mock_config,
                                                                mock_request, mock_token_store):
        conf = MagicMock()
        conf.merchant_url = "{card_number}"
        mock_config.return_value = conf
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        mock_resp.json.return_value = {'isTemporary': False}
        mock_request.return_value = mock_resp

        with self.assertRaises(UnauthorisedError):
            self.c._card_is_temporary('123')

        self.assertTrue(mock_get_auth_headers.called)
        self.assertTrue(mock_config.called)
        self.assertTrue(mock_request.called)
        self.assertTrue(mock_token_store.delete.called)

    @patch('app.agents.cooperative_merchant_integration.Configuration')
    def test_generate_response_from_error_codes(self, mock_config):
        mock_config.OPEN_AUTH_SECURITY = 1
        mock_response = MagicMock()

        error_mapping = {
            'VALIDATION_FAILED': VALIDATION,
            'VERIFICATION_FAILURE': STATUS_LOGIN_FAILED,
            'DUPLICATE_REGISTRATION': ACCOUNT_ALREADY_EXISTS,
            'INVALID_TEMP_CARD': PRE_REGISTERED_CARD,
            'CARD_NOT_FOUND': CARD_NOT_REGISTERED,
            'ANY UNRECOGNISED ERROR': UNKNOWN
        }

        for error in error_mapping:
            mock_response.text = f'{{"errors": [{{"code": "{error}", "message": ""}}]}}'

            response = json.loads(self.c.generate_response_from_error_codes(mock_response))

            self.assertEqual(response['error_codes'][0]['code'], error_mapping[error])


class TestCooperativeValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = Cooperative(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug='test-co-op')
        cls.credentials = CREDENTIALS['test-co-op']
        cls.credentials.pop('merchant_identifier', None)

    def test_validate(self):
        self.c.attempt_login(self.credentials)
        balance = self.c.balance()
        schemas.balance(balance)

    def test_validate_error_handler_raises_unknown_for_bad_status_codes(self):
        response = MagicMock()
        response.text = ''
        response.headers = {}
        response.history = False

        expected_response_json = (
            '{"error_codes": [{"code": "UNKNOWN", '
            '"description": "An unknown error has occurred with status code 400"}]}'
        )

        response.status_code = 400
        response_json = self.c._validate_error_handler(response)

        self.assertEqual(expected_response_json, response_json)

    def test_validate_error_handler_raises_login_failed_for_unverified_card_number(self):
        response = MagicMock()
        response.text = ''
        response.headers = ''
        response.history = False

        expected_response_json = (
            '{"error_codes": [{"code": "STATUS_LOGIN_FAILED",'
            ' "description": "Invalid credentials"}]}'
        )

        response.status_code = 200
        response_json = self.c._validate_error_handler(response)

        self.assertEqual(expected_response_json, response_json)

    def test_join_error_handler_raises_join_error_for_400_status(self):
        response = MagicMock()
        response.text = ''
        response.headers = ''
        response.history = False

        expected_response_json = (
            '{"error_codes": [{"code": "JOIN_ERROR", "description": "Duplicate registration."}]}'
        )

        response.status_code = 400
        response_json = self.c._join_error_handler(response)

        self.assertEqual(expected_response_json, response_json)


if __name__ == '__main__':
    unittest.main()
