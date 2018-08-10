import json
from collections import OrderedDict
from unittest.mock import MagicMock

import requests
from Crypto.PublicKey import RSA as CRYPTO_RSA
from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme
from flask.ext.testing import TestCase as FlaskTestCase
from hvac import Client

from app import create_app
from app.agents.base import MerchantApi
from unittest import mock, TestCase

from app.agents.exceptions import NOT_SENT, errors, UNKNOWN, LoginError, AgentError, NO_SUCH_RECORD
from app.back_off_service import BackOffService
from app.configuration import Configuration
from app.security.oauth import OAuth
from app.security.open_auth import OpenAuth
from app.security.rsa import RSA
from app.tests.unit.fixtures.rsa_keys import PRIVATE_KEY, PUBLIC_KEY
from app.utils import JourneyTypes


mock_config = MagicMock()
mock_config.scheme_slug = 'id'
mock_config.merchant_url = 'stuff'
mock_config.integration_service = 'SYNC'
mock_config.handler_type = 'UPDATE'
mock_config.retry_limit = 2
mock_config.callback_url = ''
mock_config.log_level = 'DEBUG'
mock_config.country = 'GB'

json_data = json.dumps({'message_uid': '123-123-123-123',
                        'record_uid': 'V8YaqMdl6WEPeZ4XWv91zO7o2GKQgwm5',  # hash for a scheme account id of 1
                        'merchant_scheme_id1': 'V8YaqMdl6WEPeZ4XWv91zO7o2GKQgwm5'})


class TestMerchantApi(FlaskTestCase):
    TESTING = True

    user_info = {'scheme_account_id': 1,
                 'status': '',
                 'user_id': 1,
                 'journey_type': JourneyTypes.LINK.value}

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
        mock_config.security_credentials = {
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
        self.config = mock_config
        self.m = MerchantApi(1, self.user_info)

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('app.agents.base.Configuration')
    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_outbound_handler_updates_json_data_with_merchant_identifiers(self, mock_sync_outbound, mock_config,
                                                                          mock_logger):
        mock_sync_outbound.return_value = json.dumps({"error_codes": [], 'json': 'test'})
        mock_config.return_value = self.config
        self.m.record_uid = '123'
        self.m._outbound_handler({'card_number': '123', 'consents': [{'slug': 'third_party_opt_in', 'value': True}]},
                                 'fake-merchant-id',
                                 'update')

        self.assertTrue(mock_logger.info.called)
        self.assertIn('merchant_scheme_id1', mock_sync_outbound.call_args[0][0])
        self.assertIn('merchant_scheme_id2', mock_sync_outbound.call_args[0][0])

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('app.agents.base.Configuration')
    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_outbound_handler_returns_response_json(self, mock_sync_outbound, mock_config, mock_logger):
        mock_sync_outbound.return_value = json.dumps({"error_codes": [], 'json': 'test'})
        mock_config.return_value = self.config
        self.m.record_uid = '123'

        resp = self.m._outbound_handler({'consents': [{'slug': 'third_party_opt_in', 'value': True}]},
                                        'fake-merchant-id',
                                        'update')

        self.assertTrue(mock_logger.info.called)
        self.assertEqual({"error_codes": [], 'json': 'test'}, resp)

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
        response.headers = {'Authorization': 'Signature {}'.format(self.signature),
                            }
        response.status_code = 200
        response.history = None

        mock_request.return_value = response
        mock_back_off.return_value.is_on_cooldown.return_value = False

        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(resp, self.json_data)

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
        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertTrue(mock_logger.warning.called)
        self.assertEqual(resp, self.json_data)

    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_returns_error_payload_on_system_errors(self, mock_request, mock_back_off,  mock_encode):
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

        resp = self.m._sync_outbound(self.json_data, self.config)

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

        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_backoff.return_value.activate_cooldown.called)

    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_does_not_send_when_on_cooldown(self, mock_request, mock_back_off, mock_encode):
        mock_encode.return_value = {'json': self.json_data}
        mock_back_off.return_value.is_on_cooldown.return_value = True

        expected_resp = {"error_codes": [{"code": NOT_SENT, "description": errors[NOT_SENT]['message']}]}

        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertFalse(mock_request.called)
        self.assertFalse(mock_back_off.return_value.activate_cooldown.called)

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch.object(MerchantApi, 'process_join_response', autospec=True)
    def test_async_inbound_success(self, mock_process_join, mock_logger):
        mock_process_join.return_value = ''
        self.m.config = self.config
        self.m.record_uid = self.m.scheme_id

        resp = self.m._inbound_handler(json.loads(self.json_data), '')

        self.assertTrue(mock_logger.info.called)
        self.assertEqual(resp, '')

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch.object(MerchantApi, 'process_join_response', autospec=True)
    def test_async_inbound_logs_errors(self, mock_process_join, mock_logger):
        mock_process_join.return_value = ''
        self.m.record_uid = self.m.scheme_id
        self.m.config = self.config
        data = json.loads(self.json_data)
        data['error_codes'] = [{
                "code": "GENERAL_ERROR",
                "description": 'An unknown error has occurred'
            }]

        self.m._inbound_handler(data, '')

        self.assertTrue(mock_logger.error.called)

    def test_process_join_handles_errors(self):
        self.m.record_uid = self.m.scheme_id
        self.m.result = {
            "error_codes": [{
                "code": "GENERAL_ERROR",
                "description": 'An unknown error has occurred'
            }]
        }

        with self.assertRaises(AgentError) as e:
            self.m.process_join_response()

        self.assertEqual(e.exception.name, "An unknown error has occurred")

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_success_does_not_raise_exceptions(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"error_codes": [], 'card_number': '1234'}

        self.m.login({'card_number': '1234'})

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

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_register_handles_error_payload(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            "error_codes": [{
                "code": "GENERAL_ERROR",
                "description": 'An unknown error has occurred'
            }]
        }
        self.m.config = self.config

        with self.assertRaises(LoginError) as e:
            self.m.register({})
        self.assertEqual(e.exception.name, 'An unknown error has occurred')

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

        response = self.client.post('/join/merchant/test-iceland', headers=headers)

        self.assertEqual(response.status_code, 401)

    @mock.patch('app.security.utils.configuration.Configuration')
    def test_authorise_returns_error_on_unknown_exception(self, mock_config):
        headers = {'Authorization': 'bad signature', 'X-REQ-TIMESTAMP': 156789765}

        mock_config.side_effect = Exception

        response = self.client.post('/join/merchant/test-iceland', headers=headers)

        self.assertEqual(response.status_code, 520)

    @mock.patch('requests.get', autospec=True)
    def test_config_service_raises_exception_on_fail(self, mock_request):
        # Should error on any status code other than 200 i.e if helios is down or no config found etc.
        mock_request.return_value.status_code = 404

        with self.assertRaises(AgentError):
            Configuration('', 1)

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

    @mock.patch('app.resources_callbacks.retry', autospec=True)
    @mock.patch('app.agents.base.thread_pool_executor.submit', autospec=True)
    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch('app.security.utils.configuration.Configuration')
    def test_async_join_callback_returns_success(self, mock_config, mock_decode, mock_thread, mock_retry):
        mock_config.return_value = self.config
        mock_decode.return_value = self.json_data

        headers = {
            "Authorization": "Signature {}".format(self.signature),
        }

        response = self.client.post('/join/merchant/test-iceland', headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertTrue(mock_thread.called)
        self.assertTrue(mock_retry.get_key.called)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'success': True})

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

    def test_credential_mapping(self):
        self.m.credential_mapping = {'barcode': 'customer_number', 'date_of_birth': 'dob'}
        json_credentials = json.dumps({'barcode': '12345', 'date_of_birth': '01/01/2001'})

        mapped_credentials = self.m.map_credentials_to_request(json_credentials)
        expected_credentials = json.dumps({'customer_number': '12345', 'dob': '01/01/2001'})

        self.assertEqual(mapped_credentials, expected_credentials)


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
        self.config = mock_config
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
                'merchant_scheme_id1': 'V8YaqMdl6WEPeZ4XWv91zO7o2GKQgwm5',
                'record_uid': 'V8YaqMdl6WEPeZ4XWv91zO7o2GKQgwm5'
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
