import json
from collections import OrderedDict
from unittest.mock import MagicMock, ANY
from uuid import uuid4

import requests
from Crypto.PublicKey import RSA as CRYPTO_RSA
from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme
from flask_testing import TestCase as FlaskTestCase
from hvac import Client
from requests import Response

from app import create_app
from app.agents.base import MerchantApi
from unittest import mock, TestCase

from app.agents.exceptions import NOT_SENT, errors, UNKNOWN, LoginError, AgentError, NO_SUCH_RECORD, \
    SERVICE_CONNECTION_ERROR, GENERAL_ERROR, CARD_NOT_REGISTERED, CARD_NUMBER_ERROR, STATUS_LOGIN_FAILED, \
    RegistrationError, CONFIGURATION_ERROR, VALIDATION, UnauthorisedError
from app.back_off_service import BackOffService
from app.configuration import Configuration
from app.resources import agent_register
from app.security.oauth import OAuth
from app.security.open_auth import OpenAuth
from app.security.rsa import RSA
from app.tasks.resend_consents import ConsentStatus
from app.tests.unit.fixtures.rsa_keys import PRIVATE_KEY, PUBLIC_KEY
from app.utils import JourneyTypes, SchemeAccountStatus

mock_configuration = MagicMock()
mock_configuration.scheme_slug = 'id'
mock_configuration.merchant_url = 'stuff'
mock_configuration.integration_service = 'SYNC'
mock_configuration.handler_type = (0, 'UPDATE')
mock_configuration.retry_limit = 2
mock_configuration.callback_url = ''
mock_configuration.log_level = 'DEBUG'
mock_configuration.country = 'GB'

json_data = json.dumps({'message_uid': '123-123-123-123',
                        'record_uid': '7gl82g4y5pvzx1wj5noqrj3dke7m9092',  # hash for a scheme account id of 1
                        'merchant_scheme_id1': '7gl82g4y5pvzx1wj5noqrj3dke7m9092',
                        'channel': 'com.bink.wallet'
                        })


class TestMerchantApi(FlaskTestCase):
    TESTING = True

    user_info = {
        'scheme_account_id': 1,
        'status': '',
        'user_set': '1',
        'journey_type': JourneyTypes.LINK.value,
        'channel': 'com.bink.wallet',
        'credentials': {}
    }

    user_info_user_set = {
        'scheme_account_id': 1,
        'status': '',
        'user_set': '1,2',
        'journey_type': JourneyTypes.LINK.value,
        'channel': 'com.bink.wallet',
        'credentials': {}
    }

    json_data = json_data

    signature = (b'BQCt9fJ25heLp+sm5HRHsMeYfGmjeUb3i/GK5xaxCQwQLa6RX49Pnu/T'
                 b'a2b6Mt4DMYV80rd0sP1Ebfw4cW8cSqhRMisQlvRN3fAzytJO0s8jOHyb'
                 b'lNA5EQo8kmjlC4YoD2a3rYVKKmJv27DpPIYXW17tZr1i5ZMifGPKgzbv'
                 b'vKzcNZeOOT2q5UE+HbGdeuw13SLoBPJkLE028g+XSk+WbDH4SwiybnGY'
                 b'401duxapoRkQUpUIgayoz4b6uVlm4TbiS+vFmULVcLZ0rvhLoC2l0S1c'
                 b'27Ti+F4QntxmTOfcxw6SB+V0PEr8gIk59lHSKqKiDcGRjnOIES084DKeMyuMUQ==').decode('utf8')

    def create_app(self):
        return create_app(self, )

    def setUp(self):
        mock_configuration.integration_service = 'SYNC'
        mock_configuration.security_credentials = {
            'outbound': {
                'service': 0,
                'credentials': [
                    {'storage_key': '', 'value': PRIVATE_KEY, 'credential_type': 'bink_private_key'}
                ]
            },
            'inbound': {
                'service': 0,
                'credentials': [
                    {'storage_key': '', 'value': PRIVATE_KEY, 'credential_type': 'bink_private_key'},
                    {'storage_key': '', 'value': PUBLIC_KEY, 'credential_type': 'merchant_public_key'}
                ]
            }
        }
        self.config = mock_configuration
        self.m = MerchantApi(1, self.user_info)
        self.m_user_set = MerchantApi(1, self.user_info_user_set)
        self.m.config = self.config

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch.object(MerchantApi, '_sync_outbound')
    @mock.patch('app.agents.base.Configuration')
    def test_outbound_handler_updates_json_data_with_merchant_identifiers(self, mock_config, mock_sync_outbound,
                                                                          mock_logger):
        mock_sync_outbound.return_value = json.dumps({"error_codes": [], 'json': 'test'})
        mock_config.return_value = self.config
        mock_config.JOIN_HANDLER = Configuration.JOIN_HANDLER

        self.m.record_uid = '123'
        self.m._outbound_handler({'card_number': '123', 'consents': [{'slug': 'third_party_opt_in',
                                                                      'value': True,
                                                                      'journey_type': JourneyTypes.JOIN.value}]},
                                 'fake-merchant-id',
                                 Configuration.JOIN_HANDLER)

        self.assertTrue(mock_logger.info.called)
        self.assertIn('merchant_scheme_id1', mock_sync_outbound.call_args[0][0])
        self.assertIn('merchant_scheme_id2', mock_sync_outbound.call_args[0][0])

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('app.agents.base.Configuration')
    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_outbound_handler_returns_response_json(self, mock_sync_outbound, mock_config, mock_logger):
        mock_sync_outbound.return_value = json.dumps({"error_codes": [], 'json': 'test'})
        mock_config.return_value = self.config
        mock_config.VALIDATE_HANDLER = Configuration.VALIDATE_HANDLER
        self.m.record_uid = '123'

        resp = self.m._outbound_handler({'consents': [{'slug': 'third_party_opt_in',
                                                       'value': True,
                                                       'journey_type': JourneyTypes.LINK.value}]},
                                        'fake-merchant-id',
                                        Configuration.VALIDATE_HANDLER)

        self.assertTrue(mock_logger.info.called)
        self.assertEqual({"error_codes": [], 'json': 'test'}, resp)

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('app.agents.base.Configuration')
    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_async_outbound_handler_expects_callback(self, mock_sync_outbound, mock_config, mock_logger):
        mock_sync_outbound.return_value = json.dumps({"error_codes": [], 'json': 'test'})
        self.config.integration_service = 'ASYNC'
        mock_config.return_value = self.config
        mock_config.JOIN_HANDLER = Configuration.JOIN_HANDLER
        mock_config.INTEGRATION_CHOICES = Configuration.INTEGRATION_CHOICES
        self.m.record_uid = '123'

        self.m._outbound_handler({'consents': []}, 'fake-merchant-id', Configuration.JOIN_HANDLER)

        self.assertTrue(self.m.expecting_callback)

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('app.agents.base.Configuration')
    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_sync_outbound_handler_doesnt_expect_callback(self, mock_sync_outbound, mock_config, mock_logger):
        mock_sync_outbound.return_value = json.dumps({"error_codes": [], 'json': 'test'})
        mock_config.return_value = self.config
        mock_config.JOIN_HANDLER = Configuration.JOIN_HANDLER
        self.m.record_uid = '123'

        self.m._outbound_handler({'consents': []}, 'fake-merchant-id', Configuration.JOIN_HANDLER)

        self.assertFalse(self.m.expecting_callback)

    @mock.patch.object(MerchantApi, 'attempt_register')
    @mock.patch('app.scheme_account.update_pending_join_account', autospec=True)
    def test_attempt_register_returns_agent_instance(self, mock_update_pending_join_account, mock_register):
        mock_register.return_value = {'message': 'success'}
        self.config.integration_service = 'ASYNC'
        user_info = {
            'metadata': {},
            'scheme_slug': 'test slug',
            'user_id': 'test user id',
            'credentials': {},
            'scheme_account_id': 2,
            'channel': 'com.bink.wallet'
        }

        register_data = agent_register(MerchantApi, user_info, {}, 1)
        agent_instance = register_data['agent']

        self.assertTrue(hasattr(agent_instance, 'expecting_callback'))
        self.assertTrue(mock_register.called)
        self.assertFalse(mock_update_pending_join_account.called)

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_success_response(self, mock_request, mock_back_off, mock_encode, mock_decode):
        mock_encode.return_value = {'json': self.json_data}
        mock_decode.return_value = self.json_data

        response = MagicMock()
        response.json.return_value = json.loads(self.json_data)
        response.content = self.json_data
        response.headers = {'Authorization': 'Signature {}'.format(self.signature)}
        response.status_code = 200
        response.history = None

        mock_request.return_value = response
        mock_back_off.return_value.is_on_cooldown.return_value = False

        resp = self.m._sync_outbound(self.json_data)

        self.assertEqual(resp, self.json_data)

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_audit_logs(self, mock_request, mock_back_off, mock_encode, mock_decode):
        msg_uid = str(uuid4())
        record_uid = 'pym1834v0zrqxnrz5e3wjdglepko5972'

        self.m.message_uid = msg_uid
        self.m.record_uid = record_uid

        mock_json_data = {
            'title': 'Mr',
            'first_name': 'Bonky',
            'last_name': 'Bonk',
            'email': 'kaziz2@binktest.com',
            'postcode': 'SL56RE',
            'address_1': '8',
            'address_2': 'Street',
            'town_city': 'Rapture',
            'county': 'County',
            'record_uid': record_uid,
            'country': 'GB',
            'message_uid': msg_uid,
            'callback_url': 'http://localhost:8000/join/merchant/iceland-bonus-card',
            'marketing_opt_in': True,
            'marketing_opt_in_thirdparty': False,
            'merchant_scheme_id1': 'oydgerxzp4k97w0pql2n0q2lo183j5mv',
            'merchant_scheme_id2': None,
            'dob': '2000-12-12',
            'phone1': '02084444444'
        }
        mock_encode.return_value = {'json': mock_json_data}
        mock_decode.return_value = mock_json_data

        response = MagicMock()
        response.json.return_value = mock_json_data
        response.content = json.dumps(mock_json_data)
        response.headers = {'Authorization': 'Signature {}'.format(self.signature)}
        response.status_code = 200
        response.history = None

        mock_request.return_value = response
        mock_back_off.return_value.is_on_cooldown.return_value = False

        resp = self.m._sync_outbound(mock_json_data)

        self.assertEqual(resp, mock_json_data)

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_logs_for_redirects(self, mock_request, mock_logger, mock_back_off, mock_encode, mock_decode):
        mock_encode.return_value = {'json': self.json_data}
        mock_decode.return_value = self.json_data
        response = requests.Response()
        response.status_code = 200
        response.history = [requests.Response()]
        response.headers['Authorization'] = 'Signature {}'.format(self.signature)

        mock_request.return_value = response
        mock_back_off.return_value.is_on_cooldown.return_value = False

        self.m.record_uid = '123'
        resp = self.m._sync_outbound(self.json_data)

        self.assertTrue(mock_logger.warning.called)
        self.assertEqual(resp, self.json_data)

    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_returns_error_payload_on_system_errors(self, mock_request, mock_back_off, mock_encode):
        mock_encode.return_value = {'json': self.json_data}

        response = requests.Response()
        response.status_code = 503

        mock_request.return_value = response
        mock_back_off.return_value.is_on_cooldown.return_value = False

        expected_resp = {
            "error_codes": [{
                "code": NOT_SENT,
                "description": errors[NOT_SENT]['message']
            }]
        }

        resp = self.m._sync_outbound(self.json_data)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_back_off.return_value.activate_cooldown.called)

    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_general_errors(self, mock_request, mock_backoff, mock_encode):
        mock_encode.return_value = {'json': self.json_data}

        response = requests.Response()
        response.status_code = 500

        mock_request.return_value = response
        mock_backoff.return_value.is_on_cooldown.return_value = False

        expected_resp = {
            "error_codes": [{
                "code": UNKNOWN,
                "description": errors[UNKNOWN]['name'] + " with status code {}".format(response.status_code)
            }]
        }

        resp = self.m._sync_outbound(self.json_data)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_backoff.return_value.activate_cooldown.called)

    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_does_not_send_when_on_cooldown(self, mock_request, mock_back_off, mock_encode):
        mock_encode.return_value = {'json': self.json_data}
        mock_back_off.return_value.is_on_cooldown.return_value = True

        expected_resp = {"error_codes": [{"code": NOT_SENT,
                                          "description": errors[NOT_SENT]['message'] + " id is currently on cooldown"}]}

        resp = self.m._sync_outbound(self.json_data)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertFalse(mock_request.called)
        self.assertFalse(mock_back_off.return_value.activate_cooldown.called)

    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('app.agents.base.MerchantApi._send_request', autospec=True)
    def test_sync_outbound_retry_on_unauthorised_exception(self, mock_send_request, mock_back_off,
                                                           mock_encode):
        mock_encode.return_value = {'json': self.json_data}
        mock_back_off.return_value.is_on_cooldown.return_value = False
        mock_send_request.side_effect = UnauthorisedError

        resp = self.m._sync_outbound(self.json_data)

        expected_resp = {"error_codes": [{"code": VALIDATION, "description": errors[VALIDATION]["name"]}]}

        self.assertEqual(mock_send_request.call_count, 6)
        self.assertEqual(mock_encode.call_count, 6)
        self.assertEqual(resp, json.dumps(expected_resp))

    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('app.agents.base.MerchantApi._send_request', autospec=True)
    def test_sync_outbound_doesnt_retry_on_202(self, mock_send_request, mock_back_off, mock_encode):
        mock_encode.return_value = {'json': self.json_data}
        mock_send_request.return_value = requests.Response(), 202
        mock_back_off.return_value.is_on_cooldown.return_value = False

        self.m._sync_outbound(self.json_data)
        self.assertEqual(1, mock_send_request.call_count)

    @mock.patch('requests.post', autospec=True)
    def test_send_request_raises_exception_on_unauthorised_response(self, mock_request):
        mock_resp = Response()
        mock_resp.status_code = 401
        mock_request.return_value = mock_resp

        self.m.request = {"json": "{}"}

        with self.assertRaises(UnauthorisedError):
            self.m._send_request()

            self.assertTrue(mock_request.called)

    @mock.patch('requests.Session.post')
    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch.object(MerchantApi, 'process_join_response', autospec=True)
    def test_async_inbound_success(self, mock_process_join, mock_logger, mock_session_post):
        mock_process_join.return_value = ''
        self.m.config = self.config
        self.m.record_uid = self.m.scheme_id

        resp = self.m._inbound_handler(json.loads(self.json_data), '')

        self.assertTrue(mock_logger.info.called)
        self.assertTrue(mock_session_post.called)
        self.assertEqual(resp, '')

    @mock.patch('requests.Session.post')
    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch.object(MerchantApi, 'process_join_response', autospec=True)
    def test_async_inbound_logs_errors(self, mock_process_join, mock_logger, mock_session_post):
        mock_process_join.return_value = ''
        self.m.record_uid = self.m.scheme_id
        self.m.config = self.config
        data = json.loads(self.json_data)
        data['error_codes'] = [{
            "code": "GENERAL_ERROR",
            "description": 'An unknown error has occurred'
        }]

        self.m._inbound_handler(data, '')

        self.assertTrue(mock_logger.warning.called)
        self.assertTrue(mock_session_post.called)

    @mock.patch('requests.Session.post')
    @mock.patch('app.agents.base.send_consent_status', autospec=True)
    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('app.scheme_account.requests', autospec=True)
    def test_async_inbound_error_updates_status(self, mock_requests, mock_logger, mock_consents, mock_session_post):
        self.m.record_uid = self.m.scheme_id
        self.m.config = self.config
        self.m.consents_data = []
        data = json.loads(self.json_data)
        data['error_codes'] = [{
            "code": "GENERAL_ERROR",
            "description": 'An unknown error has occurred'
        }]

        with self.assertRaises(AgentError):
            self.m._inbound_handler(data, '')
        self.assertTrue(mock_logger.warning.called)
        self.assertTrue(mock_consents.called)
        self.assertTrue(mock_session_post.called)
        self.assertIn('status', mock_requests.post.call_args[0][0])
        self.assertEqual(SchemeAccountStatus.ENROL_FAILED,
                         json.loads(mock_requests.post.call_args[1]['data'])['status'])

    @mock.patch('requests.Session.post')
    @mock.patch('app.agents.base.send_consent_status', autospec=True)
    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('app.scheme_account.requests', autospec=True)
    def test_async_inbound_error_account_already_exists_updates_status(self, mock_requests, mock_logger, mock_consents,
                                                                       mock_session_post):
        self.m.record_uid = self.m.scheme_id
        self.m.config = self.config
        self.m.consents_data = []
        data = json.loads(self.json_data)
        data['error_codes'] = [{
            "code": "ACCOUNT_ALREADY_EXISTS",
            "description": 'An account with this username/email already exists'
        }]

        with self.assertRaises(AgentError):
            self.m._inbound_handler(data, '')
        self.assertTrue(mock_logger.warning.called)
        self.assertTrue(mock_consents.called)
        self.assertTrue(mock_session_post.called)
        self.assertIn('status', mock_requests.post.call_args[0][0])
        self.assertEqual(SchemeAccountStatus.ACCOUNT_ALREADY_EXISTS,
                         json.loads(mock_requests.post.call_args[1]['data'])['status'])

    @mock.patch.object(MerchantApi, 'consent_confirmation')
    def test_process_join_handles_errors(self, mock_consent_confirmation):
        self.m.record_uid = self.m.scheme_id
        self.m.message_uid = "test_message_uid"
        self.m.result = {
            "message_uid": self.m.message_uid,
            "error_codes": [{
                "code": GENERAL_ERROR,
                "description": errors[GENERAL_ERROR]['message']
            }]
        }

        with self.assertRaises(RegistrationError) as e:
            self.m.process_join_response()

        self.assertEqual(e.exception.message, "General Error such as incorrect user details")
        self.assertTrue(mock_consent_confirmation.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_success_does_not_raise_exceptions(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"error_codes": [], 'card_number': '1234'}

        self.m.login({'card_number': '1234'})

        self.m.login({})
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_iceland_link_fail_no_longer_raises_specific_exception(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            'message_uid': 'test_message_uid',
            'error_codes': [{
                'code': 'GENERAL_ERROR',
                'description': 'An unknown error has occurred'
            }]
        }
        self.m.scheme_slug = 'iceland-bonus-card'
        with self.assertRaises(AgentError) as e:
            self.m.login({'card_number': '1234'})

        self.assertEqual(e.exception.code, 439)
        self.assertEqual(e.exception.code, errors[GENERAL_ERROR]['code'])
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_not_iceland_link_fail_doesnt_raises_specific_exception(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            'message_uid': 'test_message_uid',
            'error_codes': [{
                'code': 'GENERAL_ERROR',
                'description': 'An unknown error has occurred'
            }]
        }
        self.m.scheme_slug = 'not-iceland'
        with self.assertRaises(AgentError) as e:
            self.m.login({'card_number': '1234'})

        self.assertEqual(e.exception.code, errors[GENERAL_ERROR]['code'])
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_iceland_card_not_registered_1(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            'message_uid': 'test_message_uid',
            'error_codes': [{
                'code': 'CARD_NOT_REGISTERED',
                'description': 'Card number not found'
            }]
        }
        self.m.scheme_slug = 'iceland-bonus-card'
        with self.assertRaises(AgentError) as e:
            self.m.login({'card_number': '1234'})

        self.assertEqual(e.exception.code, errors[CARD_NOT_REGISTERED]['code'])
        self.assertEqual(e.exception.code, 438)
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_iceland_card_not_registered_2(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            'message_uid': 'test_message_uid',
            'error_codes': [{
                'code': 'CARD_NOT_REGISTERED',
                'description': 'card_number mandatory'
            }]
        }
        self.m.scheme_slug = 'iceland-bonus-card'
        with self.assertRaises(AgentError) as e:
            self.m.login({'card_number': '1234'})

        self.assertEqual(e.exception.code, errors[CARD_NOT_REGISTERED]['code'])
        self.assertEqual(e.exception.code, 438)
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_iceland_card_number_invalid(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            'message_uid': 'test_message_uid',
            'error_codes': [{
                'code': 'CARD_NUMBER_ERROR',
                'description': 'card_number not valid.'
            }]
        }
        self.m.scheme_slug = 'iceland-bonus-card'
        with self.assertRaises(AgentError) as e:
            self.m.login({'card_number': '1234'})

        self.assertEqual(e.exception.code, errors[CARD_NUMBER_ERROR]['code'])
        self.assertEqual(e.exception.code, 436)
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_iceland_validation(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            'message_uid': 'test_message_uid',
            'error_codes': [{
                'code': 'VALIDATION',
                'description': 'Invalid postcode format'
            }]
        }
        self.m.scheme_slug = 'iceland-bonus-card'
        with self.assertRaises(AgentError) as e:
            self.m.login({'card_number': '1234'})

        self.assertEqual(e.exception.code, errors[STATUS_LOGIN_FAILED]['code'])
        self.assertEqual(e.exception.code, 403)
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_iceland_not_sent(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            'message_uid': 'test_message_uid',
            'error_codes': [{
                'code': 'NOT_SENT',
                'description': 'Message was not sent'
            }]
        }
        self.m.scheme_slug = 'iceland-bonus-card'
        with self.assertRaises(AgentError) as e:
            self.m.login({'card_number': '1234'})

        self.assertEqual(e.exception.code, 535)
        self.assertEqual(e.exception.code, errors[NOT_SENT]['code'])
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_iceland_unknown(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            'message_uid': 'test_message_uid',
            'error_codes': [{
                'code': 'UNKNOWN',
                'description': 'An unknown error has occurred with status code 500'
            }]
        }
        self.m.scheme_slug = 'iceland-bonus-card'
        with self.assertRaises(AgentError) as e:
            self.m.login({'card_number': '1234'})

        self.assertEqual(e.exception.code, 520)
        self.assertEqual(e.exception.code, errors[UNKNOWN]['code'])
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_sets_identifier_on_first_login(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"error_codes": [], 'card_number': '1234', 'merchant_scheme_id2': 'abc'}
        self.m.identifier_type = ['barcode', 'card_number', 'merchant_scheme_id2']
        converted_identifier_type = self.m.merchant_identifier_mapping['merchant_scheme_id2']

        self.m.login({})
        self.assertTrue(mock_outbound_handler.called)
        self.assertEqual(self.m.identifier, {'card_number': '1234', converted_identifier_type: 'abc'})

    @mock.patch.object(MerchantApi, 'process_join_response')
    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_register_success_does_not_raise_exceptions(self, mock_outbound_handler, mock_process_join_response):
        mock_outbound_handler.return_value = {"error_codes": []}
        self.m.config = self.config
        self.m.register({})

        self.assertTrue(mock_outbound_handler.called)
        self.assertTrue(mock_process_join_response.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_handles_error_payload(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            "error_codes": [{
                "code": NO_SUCH_RECORD,
                "description": errors[NO_SUCH_RECORD]['message']
            }]
        }

        with self.assertRaises(LoginError) as e:
            self.m.login({})
        self.assertEqual(e.exception.name, "Account does not exist")

        mock_outbound_handler.return_value = {
            "error_codes": [{
                "code": NOT_SENT,
                "description": errors[NOT_SENT]['message']
            }]
        }

        with self.assertRaises(LoginError) as e:
            self.m.login({})
        self.assertEqual(e.exception.name, "Message was not sent")

    @mock.patch.object(MerchantApi, 'consent_confirmation')
    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_register_handles_error_payload(self, mock_outbound_handler, mock_consent_confirmation):
        self.m.message_uid = "test_message_uid"
        mock_outbound_handler.return_value = {
            "message_uid": self.m.message_uid,
            "error_codes": [{
                "code": GENERAL_ERROR,
                "description": errors[GENERAL_ERROR]['message'],
            }]
        }
        self.m.config = self.config

        with self.assertRaises(RegistrationError) as e:
            self.m.register({})
        self.assertEqual(e.exception.message, errors[GENERAL_ERROR]['message'])
        self.assertTrue(mock_consent_confirmation.called)

    @mock.patch('app.configuration.Configuration.get_security_credentials')
    @mock.patch('requests.get', autospec=True)
    def test_configuration_processes_data_correctly(self, mock_request, mock_get_security_creds):
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {
            'id': 2,
            'merchant_id': 'fake-merchant',
            'merchant_url': '',
            'handler_type': 1,
            'integration_service': 1,
            'callback_url': None,
            'retry_limit': 0,
            'log_level': 2,
            'country': 'GB',
            'security_credentials': self.config.security_credentials
        }

        mock_get_security_creds.return_value = self.config.security_credentials

        expected = {
            'handler_type': (1, 'JOIN'),
            'integration_service': 'ASYNC',
            'log_level': 'WARNING',
            'country': 'GB',
            'retry_limit': 0
        }

        c = Configuration('fake-merchant', Configuration.JOIN_HANDLER)

        config_items = c.__dict__.items()
        for item in expected.items():
            self.assertIn(item, config_items)

    def test_open_auth_encode(self):
        json_data = json.dumps(OrderedDict([('message_uid', '123-123-123-123'),
                                            ('record_uid', '0XzkL39J4q2VolejRejNmGQBW71gPv58')]))

        expected_result = {'json': json.loads(json_data)}
        open_auth = OpenAuth([])
        request_params = open_auth.encode(json_data)

        self.assertDictEqual(request_params, expected_result)

    def test_open_auth_decode(self):
        request_payload = OrderedDict([('message_uid', '123-123-123-123'),
                                       ('record_uid', '0XzkL39J4q2VolejRejNmGQBW71gPv58')])
        open_auth = OpenAuth([])
        request_json = open_auth.decode({}, json.dumps(request_payload))

        self.assertEqual(request_json, json.dumps(request_payload))

    @mock.patch.object(RSA, '_add_timestamp')
    def test_rsa_security_encode(self, mock_add_timestamp):
        json_data = json.dumps(OrderedDict([('message_uid', '123-123-123-123'),
                                            ('record_uid', '0XzkL39J4q2VolejRejNmGQBW71gPv58')]))
        timestamp = 1523356514
        json_with_timestamp = '{}{}'.format(json_data, timestamp)
        mock_add_timestamp.return_value = json_with_timestamp, timestamp
        rsa = RSA(self.config.security_credentials)
        expected_result = {
            'json': json.loads(json_data),
            'headers': {'Authorization': 'Signature {}'.format(self.signature),
                        'X-REQ-TIMESTAMP': timestamp}
        }

        request_params = rsa.encode(json_data)

        self.assertTrue(mock_add_timestamp.called)
        self.assertDictEqual(request_params, expected_result)

    @mock.patch.object(RSA, '_validate_timestamp', autospec=True)
    def test_rsa_security_decode_success(self, mock_validate_time):
        request_payload = OrderedDict([('message_uid', '123-123-123-123'),
                                       ('record_uid', '0XzkL39J4q2VolejRejNmGQBW71gPv58')])

        mock_validate_time.return_value = 'Signature {}'.format(self.signature)

        rsa = RSA(self.config.security_credentials)
        headers = {
            "Authorization": "Signature {}".format(self.signature),
            'X-REQ-TIMESTAMP': 1523356514
        }

        request_json = rsa.decode(headers, json.dumps(request_payload))
        self.assertTrue(mock_validate_time.called)
        self.assertEqual(request_json, json.dumps(request_payload))

    @mock.patch('app.security.base.time.time', autospec=True)
    def test_rsa_security_decode_raises_exception_on_failed_verification(self, mock_time):
        mock_time.return_value = 1523356514
        rsa = RSA(self.config.security_credentials)
        request = requests.Request()
        request.json = json.loads(self.json_data)
        request.headers = {
            "Authorization": "signature badbadbadbbb",
            'X-REQ-TIMESTAMP': 1523356514
        }
        request.content = self.json_data

        with self.assertRaises(AgentError):
            rsa.decode(request.headers, request.json)

    @mock.patch.object(PKCS115_SigScheme, 'verify', autospec=True)
    @mock.patch.object(CRYPTO_RSA, 'importKey', autospec=True)
    @mock.patch('app.security.base.time.time', autospec=True)
    def test_rsa_security_raises_exception_on_expired_timestamp(self, mock_time, mock_import_key, mock_verify):
        mock_time.return_value = 9876543210

        rsa = RSA(self.config.security_credentials)
        headers = {
            "Authorization": "Signature {}".format(self.signature),
            'X-REQ-TIMESTAMP': 12345
        }

        with self.assertRaises(AgentError) as e:
            rsa.decode(headers, json.loads(self.json_data))

        self.assertEqual(e.exception.name, 'Failed validation')
        self.assertFalse(mock_import_key.called)
        self.assertFalse(mock_verify.called)

    @mock.patch.object(RSA, '_validate_timestamp', autospec=True)
    def test_rsa_security_raises_exception_when_public_key_is_not_in_credentials(self, mock_validate_timestamp):
        security_credentials = {
            'outbound': {},
            'inbound': {
                'service': 0,
                'credentials': [{'storage_key': '', 'value': PRIVATE_KEY, 'credential_type': 'bink_private_key'}]
            }
        }

        rsa = RSA(security_credentials)
        headers = {
            "Authorization": "Signature {}".format(self.signature),
            'X-REQ-TIMESTAMP': 12345
        }

        with self.assertRaises(AgentError) as e:
            rsa.decode(headers, json.loads(self.json_data))

        self.assertEqual(e.exception.name, 'Configuration error')
        self.assertTrue(mock_validate_timestamp.called)

    @mock.patch.object(RSA, '_validate_timestamp', autospec=True)
    def test_rsa_security_raises_exception_when_missing_headers(self, mock_validate_timestamp):
        request_payload = OrderedDict([('message_uid', '123-123-123-123'),
                                       ('record_uid', '0XzkL39J4q2VolejRejNmGQBW71gPv58')])

        rsa = RSA(self.config.security_credentials)
        headers = {
            'X-REQ-TIMESTAMP': 12345
        }

        with self.assertRaises(AgentError) as e:
            rsa.decode(headers, json.dumps(request_payload))

        self.assertEqual(e.exception.name, 'Failed validation')

        headers = {
            "Authorization": "Signature {}".format(self.signature),
        }

        with self.assertRaises(AgentError) as e:
            rsa.decode(headers, json.dumps(request_payload))

        self.assertEqual(e.exception.name, 'Failed validation')

        headers = {
            "Authorization": "Signature {}".format(self.signature),
            'X-REQ-TIMESTAMP': 1523356514
        }
        rsa.decode(headers, json.dumps(request_payload))

        self.assertTrue(mock_validate_timestamp.called)

    @mock.patch('app.security.utils.configuration.Configuration')
    def test_authorise_returns_error_when_auth_fails(self, mock_config):
        headers = {'Authorization': 'bad signature', 'X-REQ-TIMESTAMP': 156789765}

        mock_config.return_value = self.config

        response = self.client.post('/join/merchant/iceland-bonus-card', headers=headers)

        self.assertEqual(response.status_code, 401)

    @mock.patch('app.security.utils.configuration.Configuration')
    def test_authorise_returns_error_on_unknown_exception(self, mock_config):
        headers = {'Authorization': 'bad signature', 'X-REQ-TIMESTAMP': 156789765}

        mock_config.side_effect = Exception

        response = self.client.post('/join/merchant/iceland-bonus-card', headers=headers)

        self.assertEqual(response.status_code, 520)

    @mock.patch('requests.get', autospec=True)
    def test_config_service_raises_exception_on_fail_response(self, mock_request):
        # Should error on any status code other than 200 i.e if helios is down or no config found etc.
        mock_request.return_value.status_code = 404

        with self.assertRaises(AgentError) as e:
            Configuration('', 1)

        self.assertEqual(e.exception.code, errors[CONFIGURATION_ERROR]['code'])

    @mock.patch('requests.get', autospec=True)
    def test_config_service_handles_connection_error(self, mock_request):
        mock_request.side_effect = requests.ConnectionError

        with self.assertRaises(AgentError) as e:
            Configuration('', 1)

        self.assertEqual(e.exception.code, errors[SERVICE_CONNECTION_ERROR]['code'])

    @mock.patch('hvac.Client.read')
    def test_vault_connection_error_is_handled(self, mock_client):
        mock_client.side_effect = requests.ConnectionError

        with self.assertRaises(AgentError) as e:
            Configuration.get_security_credentials([{'storage_key': 'value'}])

        self.assertEqual(e.exception.code, errors[SERVICE_CONNECTION_ERROR]['code'])
        self.assertEqual(e.exception.message, 'Error connecting to vault.')

    @mock.patch('hvac.Client.read')
    def test_vault_credentials_not_found_raises_error(self, mock_client):
        # vault returns None type if there is nothing stored for the key provided
        mock_client.side_effect = TypeError

        with self.assertRaises(AgentError) as e:
            Configuration.get_security_credentials([{'storage_key': 'value'}])

        self.assertEqual(e.exception.code, errors[CONFIGURATION_ERROR]['code'])
        self.assertEqual(e.exception.message, 'Could not locate security credentials in vault.')

    @mock.patch.object(Client, 'read')
    @mock.patch('requests.get', autospec=True)
    def test_exception_is_raised_if_credentials_not_in_vault(self, mock_request, mock_vault_client):
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {
            'id': 2,
            'merchant_id': 'fake-merchant',
            'merchant_url': '',
            'handler_type': 1,
            'integration_service': 1,
            'callback_url': None,
            'retry_limit': 0,
            'log_level': 2,
            'country': 'GB',
            'security_credentials': self.config.security_credentials
        }

        mock_vault_client.return_value = None

        with self.assertRaises(AgentError):
            Configuration('', 1)

    @mock.patch('app.resources_callbacks.JoinCallback._collect_credentials')
    @mock.patch('app.resources_callbacks.retry', autospec=True)
    @mock.patch('app.agents.base.thread_pool_executor.submit', autospec=True)
    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch('app.security.utils.configuration.Configuration')
    def test_async_join_callback_returns_success(self, mock_config, mock_decode, mock_thread, mock_retry,
                                                 mock_collect_credentials):
        mock_config.return_value = self.config
        mock_decode.return_value = self.json_data

        headers = {
            "Authorization": "Signature {}".format(self.signature),
        }

        response = self.client.post('/join/merchant/iceland-bonus-card', headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertTrue(mock_thread.called)
        self.assertTrue(mock_retry.get_key.called)
        self.assertTrue(mock_collect_credentials.called)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'success': True})

    @mock.patch('app.resources_callbacks.retry', autospec=True)
    @mock.patch('app.agents.base.thread_pool_executor.submit', autospec=True)
    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch('app.security.utils.configuration.Configuration')
    def test_join_callback_raises_error_with_bad_record_uid(self, mock_config, mock_decode, mock_thread,
                                                            mock_retry):
        mock_config.return_value = self.config
        json_data_with_bad_record_uid = json.dumps({'message_uid': '123-123-123-123',
                                                    'record_uid': 'a',
                                                    'merchant_scheme_id1': 'V8YaqMdl6WEPeZ4XWv91zO7o2GKQgwm5'})
        mock_decode.return_value = json_data_with_bad_record_uid

        headers = {
            "Authorization": "Signature {}".format(self.signature),
        }

        response = self.client.post('/join/merchant/iceland-bonus-card', headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertFalse(mock_thread.called)
        self.assertFalse(mock_retry.get_key.called)

        self.assertEqual(response.status_code, 520)
        self.assertEqual(response.json, {'code': 520, 'message': 'The record_uid provided is not valid',
                                         'name': 'Unknown Error'})

    @mock.patch('app.resources_callbacks.JoinCallback._collect_credentials')
    @mock.patch('app.resources_callbacks.update_pending_join_account', autospec=True)
    @mock.patch('app.resources_callbacks.retry.get_key', autospec=True)
    @mock.patch('app.agents.base.thread_pool_executor.submit', autospec=True)
    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch('app.security.utils.configuration.Configuration')
    def test_join_callback_specific_error(self, mock_config, mock_decode, mock_thread, mock_retry, mock_update_join,
                                          mock_collect_credentials):
        mock_retry.side_effect = AgentError(NO_SUCH_RECORD)
        mock_config.return_value = self.config
        mock_decode.return_value = json_data

        headers = {"Authorization": "Signature {}".format(self.signature)}

        response = self.client.post('/join/merchant/iceland-bonus-card', headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertFalse(mock_thread.called)
        self.assertTrue(mock_retry.called)
        self.assertTrue(mock_update_join.called)
        self.assertTrue(mock_collect_credentials.called)

        self.assertEqual(response.status_code, errors[NO_SUCH_RECORD]['code'])
        self.assertEqual(response.json, errors[NO_SUCH_RECORD])

    @mock.patch('app.resources_callbacks.JoinCallback._collect_credentials')
    @mock.patch('app.resources_callbacks.update_pending_join_account', autospec=True)
    @mock.patch('app.resources_callbacks.retry.get_key', autospec=True)
    @mock.patch('app.agents.base.thread_pool_executor.submit', autospec=True)
    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch('app.security.utils.configuration.Configuration')
    def test_join_callback_unknown_error(self, mock_config, mock_decode, mock_thread, mock_retry,
                                         mock_update_join, mock_credentials):
        mock_retry.side_effect = RuntimeError('test exception')
        mock_config.return_value = self.config
        mock_decode.return_value = json_data

        headers = {"Authorization": "Signature {}".format(self.signature)}

        response = self.client.post('/join/merchant/iceland-bonus-card', headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertFalse(mock_thread.called)
        self.assertTrue(mock_retry.called)
        self.assertTrue(mock_update_join.called)
        self.assertTrue(mock_credentials.called)

        self.assertEqual(response.status_code, 520)
        self.assertEqual(response.json, {'code': 520, 'message': 'test exception', 'name': 'Unknown Error'})

    @mock.patch('requests.sessions.Session.get')
    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch('app.security.utils.configuration.Configuration')
    def test_join_callback_raises_custom_exception_if_collect_credentials_fails(self, mock_config, mock_decode,
                                                                                mock_session_get):
        mock_config.return_value = self.config
        mock_decode.return_value = json_data

        mock_response = Response()
        mock_response.status_code = 404

        # Bad response test
        mock_session_get.return_value = mock_response
        headers = {"Authorization": "Signature {}".format(self.signature)}

        response = self.client.post('/join/merchant/iceland-bonus-card', headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertEqual(response.status_code, errors[SERVICE_CONNECTION_ERROR]['code'])
        self.assertEqual(response.json,
                         {'code': 537,
                          'message': 'There was in issue connecting to an external service.',
                          'name': 'Service connection error'})

        # Connection error test
        mock_session_get.side_effect = requests.ConnectionError
        response = self.client.post('/join/merchant/iceland-bonus-card', headers=headers)

        self.assertEqual(response.status_code, errors[SERVICE_CONNECTION_ERROR]['code'])
        self.assertEqual(response.json,
                         {'code': 537,
                          'message': 'There was in issue connecting to an external service.',
                          'name': 'Service connection error'})

    def test_merchant_scheme_id_conversion(self):
        self.m.identifier_type = ['merchant_scheme_id2', 'barcode']
        data = {
            'merchant_scheme_id2': '123',
            'barcode': '123'
        }
        credentials_to_update = self.m._get_identifiers(data)

        expected_dict = {
            'merchant_identifier': '123',
            'barcode': '123'
        }
        self.assertEqual(credentials_to_update, expected_dict)

    def test_merchant_scheme_id_conversion_with_different_values(self):
        self.m.identifier_type = ['merchant_scheme_id1', 'merchant_scheme_id3']
        data = {
            'merchant_scheme_id1': '123',
            'merchant_scheme_id3': '123'
        }
        self.m.merchant_identifier_mapping = {'merchant_scheme_id3': 'email'}
        credentials_to_update = self.m._get_identifiers(data)

        expected_dict = {
            'merchant_scheme_id1': '123',
            'email': '123'
        }
        self.assertEqual(credentials_to_update, expected_dict)

    def test_get_merchant_ids(self):
        merchant_ids = self.m.get_merchant_ids({})
        self.assertIn('merchant_scheme_id1', merchant_ids)

    def test_get_merchant_ids_user_set(self):
        merchant_ids = self.m_user_set.get_merchant_ids({})
        self.assertIn('merchant_scheme_id1', merchant_ids)

    def test_credential_mapping(self):
        self.m.credential_mapping = {'barcode': 'customer_number', 'date_of_birth': 'dob'}
        credentials = {'barcode': '12345', 'date_of_birth': '01/01/2001'}

        mapped_credentials = self.m.map_credentials_to_request(credentials)
        expected_credentials = {'customer_number': '12345', 'dob': '01/01/2001'}

        self.assertEqual(mapped_credentials, expected_credentials)

    @mock.patch('app.agents.base.publish.status')
    @mock.patch('app.agents.base.update_pending_join_account', autospec=True)
    @mock.patch.object(MerchantApi, '_outbound_handler')
    @mock.patch.object(MerchantApi, 'consent_confirmation')
    def test_consents_confirmation_is_called_on_sync_register(self, mock_consent_confirmation, mock_outbound_handler,
                                                              mock_update_pending_join_account, mock_publish):
        # Confirmation is setting calling the endpoint to update UserConsent status to either SUCCESS or FAILURE
        credentials = {'consents': [{'id': 1, 'slug': 'consent1', 'value': True,
                                     'journey_type': JourneyTypes.JOIN.value},
                                    {'id': 2, 'slug': 'consent2', 'value': False,
                                     'journey_type': JourneyTypes.JOIN.value}]}
        self.m.user_info.update(credentials=credentials)

        self.m.message_uid = ''
        mock_outbound_handler.return_value = {'message_uid': self.m.message_uid}
        self.m.config = self.config

        self.m.register(credentials)

        mock_consent_confirmation.assert_called_with(credentials['consents'], ConsentStatus.SUCCESS)

        self.assertTrue(mock_outbound_handler.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(mock_publish.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    @mock.patch.object(MerchantApi, 'consent_confirmation')
    def test_consents_confirmed_as_pending_on_async_register(self, mock_consent_confirmation, mock_outbound_handler):
        credentials = {'consents': [{'id': 1, 'slug': 'consent1', 'value': True,
                                     'journey_type': JourneyTypes.JOIN.value},
                                    {'id': 2, 'slug': 'consent2', 'value': False,
                                     'journey_type': JourneyTypes.JOIN.value}]}
        self.m.user_info.update(credentials=credentials)

        message_uid = ''
        mock_outbound_handler.return_value = {'message_uid': message_uid}
        self.m.config = self.config
        self.m.config.integration_service = 'ASYNC'

        self.m.register(credentials)

        mock_consent_confirmation.assert_called_with(credentials['consents'], ConsentStatus.PENDING)
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    @mock.patch.object(MerchantApi, 'consent_confirmation')
    def test_consents_confirmed_on_failed_async_register(self, mock_consent_confirmation, mock_outbound_handler):
        credentials = {'consents': [{'id': 1, 'slug': 'consent1', 'value': True,
                                     'journey_type': JourneyTypes.JOIN.value},
                                    {'id': 2, 'slug': 'consent2', 'value': False,
                                     'journey_type': JourneyTypes.JOIN.value}]}
        self.m.user_info.update(credentials=credentials)

        message_uid = ''
        mock_outbound_handler.return_value = {'error_codes': [{'code': 'GENERAL_ERROR'}], 'message_uid': message_uid}
        self.m.config = self.config
        self.m.config.integration_service = 'ASYNC'

        with self.assertRaises(RegistrationError):
            self.m.register(credentials)

        mock_consent_confirmation.assert_called_with(credentials['consents'], ConsentStatus.FAILED)
        self.assertTrue(mock_outbound_handler.called)

    @mock.patch('app.tasks.resend_consents.logger.error')
    @mock.patch('app.tasks.resend_consents.requests.put')
    def test_consents_confirmation_sends_updated_user_consents(self, mock_request, mock_error_logger):
        mock_request.return_value.status_code = 200
        consents_data = [{
            'id': 1,
            'slug': 'consent-slug1',
            'value': True,
            'created_on': '',
            'journey_type': 1
        }, {
            'id': 2,
            'slug': 'consent-slug2',
            'value': False,
            'created_on': '',
            'journey_type': 1
        }]

        self.m.consent_confirmation(consents_data, ConsentStatus.SUCCESS)

        self.assertTrue(mock_request.called)
        self.assertFalse(mock_error_logger.called)
        mock_request.assert_called_with(ANY,
                                        data=json.dumps({"status": ConsentStatus.SUCCESS}),
                                        headers=ANY,
                                        timeout=ANY)

    @mock.patch('app.tasks.resend_consents.logger.error')
    @mock.patch('app.tasks.resend_consents.requests.put')
    def test_consents_confirmation_works_with_empty_consents(self, mock_request, mock_error_logger):
        mock_request.return_value.status_code = 200
        consents_data = []

        self.m.consent_confirmation(consents_data, ConsentStatus.SUCCESS)

        self.assertFalse(mock_request.called)
        self.assertFalse(mock_error_logger.called)

    def test_filter_consents_returns_none_on_empty_consents(self):
        data = {}

        for handler_type in Configuration.HANDLER_TYPE_CHOICES:
            result = self.m._filter_consents(data, handler_type[0])

            self.assertIsNone(result)

        data = {'consents': []}
        for handler_type in Configuration.HANDLER_TYPE_CHOICES:
            result = self.m._filter_consents(data, handler_type[0])

            self.assertIsNone(result)


@mock.patch('redis.StrictRedis.get')
@mock.patch('redis.StrictRedis.set')
class TestBackOffService(TestCase):
    back_off = BackOffService()

    def redis_set(self, key, val):
        self.data[key] = val

    def redis_get(self, key):
        return self.data.get(key)

    def setUp(self):
        self.data = {}

    @mock.patch('app.back_off_service.time.time', autospec=True)
    def test_back_off_service_activate_cooldown_stores_datetime(self, mock_time, mock_set, mock_get):
        mock_set.side_effect = self.redis_set
        mock_get.side_effect = self.redis_get

        mock_time.return_value = 9876543210
        self.back_off.activate_cooldown('merchant-id', 'update', 100)

        date = self.back_off.storage.get('back-off:merchant-id:update')
        self.assertEqual(date, 9876543310)

    @mock.patch('app.back_off_service.time.time', autospec=True)
    def test_back_off_service_is_on_cooldown(self, mock_time, mock_set, mock_get):
        mock_set.side_effect = self.redis_set
        mock_get.side_effect = self.redis_get

        mock_time.return_value = 1100
        self.back_off.storage.set('back-off:merchant-id:update', 1200)
        resp = self.back_off.is_on_cooldown('merchant-id', 'update')

        self.assertTrue(resp)


class TestOAuth(TestCase):

    def setUp(self):
        self.config = mock_configuration
        self.json_data = json_data
        self.token_response = {
            'token_type': 'Bearer',
            'ext_expires_in': '',
            'expires_in': '',
            'not_before': '',
            'expires_on': '',
            'resource': '',
            'access_token': 'some_token'
        }

        self.auth_creds = self.config.security_credentials
        self.auth_creds['outbound']['credentials'] = [{
            "storage_key": "",
            "value": {
                "payload": {
                    "client_id": "",
                    "client_secret": "",
                    "resource": "",
                    "grant_type": ""},
                "url": "",
                "prefix": "Bearer"
            },
            "credential_type": "compound_key",
            "service": 2
        }]

    @mock.patch('requests.post')
    def test_oauth_encode_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = self.token_response
        mock_request.return_value = mock_response

        expected_request = {
            'headers': {'Authorization': 'Bearer some_token'},
            'json': {
                'message_uid': '123-123-123-123',
                'merchant_scheme_id1': '7gl82g4y5pvzx1wj5noqrj3dke7m9092',
                'record_uid': '7gl82g4y5pvzx1wj5noqrj3dke7m9092',
                'channel': 'com.bink.wallet',
            }
        }

        auth = OAuth(self.auth_creds)

        request = auth.encode(self.json_data)

        self.assertTrue(mock_request.called)
        self.assertEqual(request, expected_request)

    @mock.patch('requests.post')
    def test_oath_encode_raises_error_on_connection_error(self, mock_request):
        mock_request.side_effect = requests.ConnectionError
        auth = OAuth(self.auth_creds)

        with self.assertRaises(AgentError) as e:
            auth.encode(self.json_data)

        self.assertEqual(e.exception.name, 'Service connection error')

    @mock.patch('requests.post')
    def test_oauth_encode_raises_error_on_incorrect_credential_setup(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = self.token_response
        mock_request.return_value = mock_response

        missing_creds = self.auth_creds

        required_keys = ["payload", "url", "prefix"]

        keys_dict = {
            "payload": {
                "client_id": "",
                "client_secret": "",
                "resource": "",
                "grant_type": ""
            },
            "url": "",
            "prefix": "Bearer"
        }

        # ensures function raises error if any required keys are missing from the data stored in the vault
        for required_key in required_keys:
            value = keys_dict.copy()
            value.pop(required_key)
            missing_creds['outbound']['credentials'] = [{
                "value": value,
            }]

            auth = OAuth(self.auth_creds)

            with self.assertRaises(AgentError) as e:
                auth.encode(self.json_data)

            self.assertEqual(e.exception.name, 'Configuration error')
