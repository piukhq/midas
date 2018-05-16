import json
from collections import OrderedDict
from unittest.mock import MagicMock

import requests
from Crypto.PublicKey import RSA as CRYPTO_RSA
from Crypto.Signature.PKCS1_v1_5 import PKCS115_SigScheme
from flask.ext.testing import TestCase as FlaskTestCase

from app import create_app
from app.agents.base import MerchantApi
from unittest import mock, TestCase

from app.agents.exceptions import NOT_SENT, errors, UNKNOWN, LoginError, AgentError
from app.back_off_service import BackOffService
from app.configuration import Configuration
from app.security.rsa import RSA


class TestMerchantApi(FlaskTestCase):
    TESTING = True

    user_info = {'scheme_account_id': 1,
                 'status': '',
                 'user_id': 1}

    m = MerchantApi(1, user_info)
    json_data = json.dumps({'message_uid': '123-123-123-123',
                            'record_uid': '0XzkL39J4q2VolejRejNmGQBW71gPv58',    # hash for a scheme account id of 1
                            'merchant_scheme_id1': '0XzkL39J4q2VolejRejNmGQBW71gPv58'})

    signature = (b'Tr7N44RTxiKtOeLIoqFCPk6oQOA4ektTmZb/ddhc3uWJy5YD0Qrx5WqDs'
                 b'4TiP7JrI/fbYBD4gCRC/mYmlaXQ02OanYIVlkQTF97H4KMX41QCZixYyl'
                 b'fFfeMBlj65NV2XUSBwpZiq+0pHrcZON2gmrvr7QanOsO9wv/Pf/3Moub3'
                 b'Jt7qSsSG9o/XAHFrGhy6RQH4jlXbgwQMeI+3cEKf7CquE//tW6+RXVWW4'
                 b'/T7zjEo9R2yw0uBZU5tr6nyYTkJq1DBRFowMq2ZoArZ8t7gGi8vVxlkfM'
                 b'mPoyb2MALwk1lCQyyxJSaOxiWm6DSH5R2zpxeDeInnK8pR81aCU9PPhQw==').decode('utf8')

    test_private_key = (
        '-----BEGIN RSA PRIVATE KEY-----\n'
        'MIIEpAIBAAKCAQEAsw2VXAHRqPaCDVYI6Lug3Uq9Quik7m3sI8BkzqdCkBmakPZ5\n'
        'cssbc4EsxETTA9V0V1KDMUy6vGUSaN8pbg4MPDZOzUlJyOcBAhaKWpUH4Bw0OlBt\n'
        'KPVewN51n8NZHvwqh39f5rwVNVB5T2haTOsuG0Q7roH5TPYs75F87bELwRLCnWyX\n'
        'o69f6o6fH7N+M2CN11S1UKT7ZkqaL2fm3LWuf8GWAkOrvrZp6js3kKCCuztI+JxP\n'
        '93Aa3411aVH1jt0Wgyex+ekdAO2ykGq2tbs9vGi//6ZweZey+B1+2LrCum1+Wula\n'
        'f1lGLNF5Bo6fHuXXw63fhx54PQe8pMWc5LW93wIDAQABAoIBAQCEdnQc0SuueE/W\n'
        'VePZaZWkoPpLWZlK2v9ro5XwXEUeHhL/U5idmC0C0nmv6crCd1POljiAbGdpoMxx\n'
        '0UbxKGtc0ECUFrgDbQKN7OcGBGMDJVpuGbnoJz6mKO2T+A0ioyNDgrQMGvEFtDdK\n'
        'y8SiSwqdGWmdvIIWsbiks1lc7zHm7yAUWSp/XYgsw73+xsU+3wRlrEGsUoiTlb5J\n'
        'ZAGXBd95Gix7FQeX04WDP47xtdaydz2G/dhqsN8w78peMDPMNd/LPKMpAHYCT/5b\n'
        'wri0nfzVjNMHULCZU4KoopO8De0M1aik5GwWOdnFx6z/VkW/drXltfc9MKOJKXP7\n'
        'WI5wSCHhAoGBAOmt8z7y5RYuhIum8+e1hsQPb0ah55xcGSK8Vb066xx1XFxlgWB+\n'
        'Xiv+Ga7nQvJm3johLPuIFp0eQKrJ3a+KH+L6biM20S7K5hfxi3qdrHOBd8qKoRWS\n'
        'cbR1V40TYxXTvWYYUa2jnKPsB0msm+3l0jwNLZhygbhwDtw1cNhed2ebAoGBAMQn\n'
        '4UPHU1HE7nUI09eY11eUURuB69TRIoZNO3VVII83RHro7qHyKWk0W2RevjrE8ir2\n'
        'S4ivFYQU5lca6QmcsPj7iGtFbeVImuTWwDTaahCFcfV/pV0L6xxU/7TowKivABHe\n'
        'SUVwZJU+sPPcSSHZRa1uP7/6XD5oZEnysm1Vx6ENAoGBAKQiw/XWRKVE/WLeXPnH\n'
        'Hqb+NGoHdRj1883bPdoR1W0C3mIkBjER8fGypLWeyP5c1QE9pkvzNfccdc3Axw7y\n'
        '1RzoTI49hcb5S49L4W257JShPtQsdaMiXu2jcmCsWm/Nb36T3GM7xd25/xB3xnre\n'
        'b8Iwe3NWEtnLFBUHEIFaMUK7AoGAHoqHDGKQmn6rEhXZxgvKG5zANCQ6b9xQH9EO\n'
        'nOowM5xLUUfLP/PQdszsHeiSfdwESKQohpOcKgCHDLDn79MxytJ/HxSkU7rGQzMc\n'
        'oh4PvZrJb4v8V0xvwu2JEsXamWkF/cI6blFdl883BgEacea+bo5n5qA4lI70bn8X\n'
        'QObGOlECgYAURWOAKLd7RzgNrBorqof4ZZxdNXgOGq9jb4FE+bWI48EvTVGBmt7u\n'
        '9pHA57UX0Nf1UQ/i3dKAvm5GICDUuWHvUnnb3m+pbx0w91YSXR9t8TVNdJ2dMhNu\n'
        'ZSEUFQWbkQLUGtorzjqGssXHxKVa+9riPpztJNDl+8oHhu28wu4WyQ==\n'
        '-----END RSA PRIVATE KEY-----\n'
    )

    test_public_key = ('ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCzDZVcAdGo9oINVgjou6DdSr1C6KTubewj'
                       'wGTOp0KQGZqQ9nlyyxtzgSzERNMD1XRXUoMxTLq8ZRJo3yluDgw8Nk7NSUnI5wECFopalQfg'
                       'HDQ6UG0o9V7A3nWfw1ke/CqHf1/mvBU1UHlPaFpM6y4bRDuugflM9izvkXztsQvBEsKdbJej'
                       'r1/qjp8fs34zYI3XVLVQpPtmSpovZ+bcta5/wZYCQ6u+tmnqOzeQoIK7O0j4nE/3cBrfjXVp'
                       'UfWO3RaDJ7H56R0A7bKQara1uz28aL//pnB5l7L4HX7YusK6bX5a6Vp/WUYs0XkGjp8e5dfD'
                       'rd+HHng9B7ykxZzktb3f kaziz@Kashims-iMac.local')

    config = MagicMock()
    config.scheme_slug = 'id'
    config.merchant_url = 'stuff'
    config.integration_service = 'SYNC'
    config.security_service = 'RSA'
    config.security_credentials = [{'type': '', 'storage_key': ''}]
    config.handler_type = 'UPDATE'
    config.retry_limit = 2
    config.callback_url = ''
    config.log_level = 'DEBUG'

    def create_app(self):
        return create_app(self, )

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('app.agents.base.Configuration')
    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_outbound_handler_returns_response_json(self, mock_sync_outbound, mock_config, mock_logger):
        mock_sync_outbound.return_value = json.dumps({"errors": [], 'json': 'test'})
        mock_config.return_value = self.config
        self.m.record_uid = '123'

        resp = self.m._outbound_handler({}, 'fake-merchant-id', 'update')

        self.assertTrue(mock_logger.info.called)
        self.assertEqual({"errors": [], 'json': 'test'}, resp)

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

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_returns_error_payload_on_system_errors(self, mock_request, mock_back_off,  mock_encode,
                                                                  mock_decode):
        mock_encode.return_value = {'json': self.json_data}
        mock_decode.return_value = json.dumps(self.json_data)

        response = requests.Response()
        response.status_code = 503

        mock_request.return_value = response
        mock_back_off.return_value.is_on_cooldown.return_value = False

        expected_resp = {
            "errors": [errors[NOT_SENT]['message']],
            "code": errors[NOT_SENT]['code']
        }

        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_back_off.return_value.activate_cooldown.called)

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_general_errors(self, mock_request, mock_backoff, mock_encode, mock_decode):
        mock_encode.return_value = {'json': self.json_data}
        mock_decode.return_value = json.dumps(self.json_data)

        response = requests.Response()
        response.status_code = 500

        mock_request.return_value = response
        mock_backoff.return_value.is_on_cooldown.return_value = False

        expected_resp = {"errors": [errors[UNKNOWN]['name'] + " with status code {}".format(response.status_code)],
                         "code": errors[UNKNOWN]['code']}
        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_backoff.return_value.activate_cooldown.called)

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_does_not_send_when_on_cooldown(self, mock_request, mock_back_off, mock_encode, mock_decode):
        mock_encode.return_value = {'json': self.json_data}
        mock_decode.return_value = json.dumps(self.json_data)
        mock_back_off.return_value.is_on_cooldown.return_value = True
        expected_resp = {"errors": [errors[NOT_SENT]['message']],
                         "code": errors[NOT_SENT]['code']}
        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertFalse(mock_request.called)
        self.assertFalse(mock_back_off.return_value.activate_cooldown.called)

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch.object(MerchantApi, 'process_join_response', autospec=True)
    def test_async_inbound_success(self, mock_process_join, mock_logger):
        mock_process_join.return_value = ''
        self.m.record_uid = self.m.scheme_id

        resp = self.m._inbound_handler(self.json_data, '', self.config.handler_type)

        self.assertTrue(mock_logger.info.called)
        self.assertEqual(resp, '')

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch.object(MerchantApi, 'process_join_response', autospec=True)
    def test_async_inbound_logs_errors(self, mock_process_join, mock_logger):
        mock_process_join.return_value = ''
        self.m.record_uid = self.m.scheme_id
        data = json.loads(self.json_data)
        data['errors'] = ['some error']
        data['code'] = 'some error code'

        self.m._inbound_handler(json.dumps(data), '', self.config.handler_type)

        self.assertTrue(mock_logger.error.called)

    def test_process_join_handles_errors(self):
        self.m.record_uid = self.m.scheme_id
        self.m.result = {'errors': ['some error'],
                         'code': 'GENERAL_ERROR'}

        with self.assertRaises(AgentError) as e:
            self.m.process_join_response()

        self.assertEqual(e.exception.name, "An unknown error has occurred")

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_success_does_not_raise_exceptions(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"errors": [], 'card_number': '1234'}

        self.m.login({'card_number': '1234'})

        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_sets_identifier_on_first_login(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"errors": [], 'card_number': '1234'}

        self.m.login({})

        self.assertTrue(mock_outbound_handler.called)
        self.assertEqual(self.m.identifier, {'card_number': '1234'})

    @mock.patch.object(MerchantApi, 'process_join_response')
    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_register_success_does_not_raise_exceptions(self, mock_outbound_handler, mock_process_join_response):
        mock_outbound_handler.return_value = {"errors": []}

        self.m.register({})

        self.assertTrue(mock_outbound_handler.called)
        self.assertTrue(mock_process_join_response.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_handles_error_payload(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"errors": ['Account does not exist'],
                                              "code": "NO_SUCH_RECORD"}

        with self.assertRaises(LoginError) as e:
            self.m.login({})
        self.assertEqual(e.exception.name, "Account does not exist")

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_register_handles_error_payload(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {
            "errors": [
                "some unknown error"
            ],
            "code": "GENERAL_ERROR"
        }

        with self.assertRaises(LoginError) as e:
            self.m.register({})
        self.assertEqual(e.exception.name, 'An unknown error has occurred')

    @mock.patch('app.configuration.get_security_credentials')
    @mock.patch('requests.get', autospec=True)
    def test_configuration_processes_data_correctly(self, mock_request, mock_get_security_creds):
        mock_request.return_value.content = json.dumps({
            'id': 2,
            'merchant_id': 'fake-merchant',
            'merchant_url': '',
            'handler_type': 1,
            'integration_service': 1,
            'callback_url': None,
            'security_service': 0,
            'retry_limit': 0,
            'log_level': 2,
            'security_credentials': [
                {'type': 'public_key',
                 'storage_key': '123456'}
            ]}).encode()

        mock_get_security_creds.return_value = {
            'type': 'public_key',
            'storage_key': '123456',
            'value': 'asdfghjkl'
        }

        expected = {
            'handler_type': (1, 'JOIN'),
            'integration_service': 'ASYNC',
            'security_service': 'RSA',
            'log_level': 'WARNING',
        }

        c = Configuration('fake-merchant', Configuration.JOIN_HANDLER)

        config_items = c.__dict__.items()
        for item in expected.items():
            self.assertIn(item, config_items)

    @mock.patch.object(RSA, '_add_timestamp')
    def test_rsa_security_encode(self, mock_add_timestamp):
        json_data = json.dumps(OrderedDict([('message_uid', '123-123-123-123'),
                                            ('record_uid', '0XzkL39J4q2VolejRejNmGQBW71gPv58')]))
        timestamp = 1523356514
        json_with_timestamp = '{}timestamp={}'.format(json_data, timestamp)
        mock_add_timestamp.return_value = json_with_timestamp, timestamp
        rsa = RSA([{'type': 'bink_private_key', 'value': self.test_private_key}])
        expected_result = {
            'json': json.loads(json_data),
            'headers': {'Authorization': 'Signature {}timestamp={}'.format(self.signature, timestamp)}
        }

        request_params = rsa.encode(json_data)

        self.assertTrue(mock_add_timestamp.called)
        self.maxDiff = None
        self.assertDictEqual(request_params, expected_result)

    @mock.patch.object(RSA, '_validate_timestamp', autospec=True)
    def test_rsa_security_decode_success(self, mock_validate_time):
        request_payload = OrderedDict([('message_uid', '123-123-123-123'),
                                       ('record_uid', '0XzkL39J4q2VolejRejNmGQBW71gPv58')])

        mock_validate_time.return_value = 'Signature {}'.format(self.signature)

        rsa = RSA([{'type': 'merchant_public_key', 'value': self.test_public_key}])
        header = 'Signature {}timestamp=1523356514'.format(self.signature)

        request_json = rsa.decode(header, json.dumps(request_payload))

        self.assertTrue(mock_validate_time.called)
        self.assertEqual(request_json, json.dumps(request_payload))

    @mock.patch('app.security.base.time.time', autospec=True)
    def test_rsa_security_decode_raises_exception_on_fail(self, mock_time):
        mock_time.return_value = 1523356514
        rsa = RSA([{'type': 'merchant_public_key', 'value': self.test_public_key}])
        request = requests.Request()
        request.json = json.loads(self.json_data)
        request.headers['AUTHORIZATION'] = 'bad signature'
        request.content = self.json_data

        with self.assertRaises(AgentError):
            rsa.decode(request.headers['AUTHORIZATION'], request.json)

    @mock.patch.object(PKCS115_SigScheme, 'verify', autospec=True)
    @mock.patch.object(CRYPTO_RSA, 'importKey', autospec=True)
    @mock.patch('app.security.base.time.time', autospec=True)
    def test_security_raises_exception_on_expired_timestamp(self, mock_time, mock_import_key, mock_verify):
        mock_time.return_value = 9876543210

        rsa = RSA([{'type': 'merchant_public_key', 'value': self.test_public_key}])
        auth_header = 'Signature {}timestamp=12345'.format(self.signature)

        with self.assertRaises(AgentError) as e:
            rsa.decode(auth_header, json.loads(self.json_data))

        self.assertEqual(e.exception.name, 'Failed validation')
        self.assertFalse(mock_import_key.called)
        self.assertFalse(mock_verify.called)

    @mock.patch('app.resources_callbacks.retry', autospec=True)
    @mock.patch('app.agents.base.thread_pool_executor.submit', autospec=True)
    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch('app.security.configuration.Configuration')
    def test_async_join_callback_returns_success(self, mock_config, mock_decode, mock_thread, mock_retry):
        mock_config.return_value = self.config
        mock_decode.return_value = self.json_data

        headers = {
            "Authorization": "Signature {}".format(self.signature)
        }

        response = self.client.post('/join/merchant/iceland', headers=headers)

        self.assertTrue(mock_config.called)
        self.assertTrue(mock_decode.called)
        self.assertTrue(mock_thread.called)
        self.assertTrue(mock_retry.get_key.called)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'success': True})


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
