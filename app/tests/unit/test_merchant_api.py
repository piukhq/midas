import json
from unittest import mock
from unittest.mock import MagicMock

import requests
from flask.ext.testing import TestCase

from app import create_app
from app.agents.base import MerchantApi
from app.agents.exceptions import NOT_SENT, errors, UNKNOWN, LoginError, AgentError
from app.configuration import Configuration
from app.security.rsa import RSA


class TestMerchantApi(TestCase):
    TESTING = True

    m = MerchantApi(1, 1)
    json_data = json.dumps({
        'message_uid': '123-123-123-123',
        'record_uid': '0XzkL39J4q2VolejRejNmGQBW71gPv58'    # hash for a scheme account id of 1
        })

    signature = b'qOmitDJLhyZnBFZGRHm4Nz0hiRl/FKXv8y1f5r3aX/Fdu6ayTaVeY3OzSwbgbT03p1YSM09yHdcyX' \
                b'ACGIWt/Bet6mmeyEUOZgLkv3PVS3et/dvftM4ZnnmTu/Nu7KjJNkBZnhLB8DPRQ7tTWsI0TbCDgxU' \
                b'onLBibMXQfvHp9fq6KCcdXzgKC+O5Bzk+15g7G+crNnDW65ce56MJhIDBzeiXis4tqiy5K6jMnIhj' \
                b'oRWPxlGsBXe2v37NUlmL3qQk0QsIWn8jcS5cRXahPBwKtwn10KcYpEKm89Xse5iqJO1Vx0cj4vHoe' \
                b'RXW7DMtkcfPv79ZcCn6oHsL7+7jsMD+QNQ=='

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
    config.merchant_id = 'id'
    config.merchant_url = 'stuff'
    config.integration_service = 'Sync'
    config.security_service = 'RSA'
    config.security_credentials = [{'type': '', 'storage_key': ''}]
    config.handler_type = 'update'
    config.retry_limit = 2
    config.callback_url = ''
    config.log_level = Configuration.DEBUG_LOG_LEVEL

    def create_app(self):
        return create_app(self, )

    @mock.patch('app.agents.base.Configuration')
    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_outbound_handler_returns_reponse_json(self, mock_sync_outbound, mock_config):
        mock_sync_outbound.return_value = json.dumps({"error_codes": [], 'json': 'test'})
        mock_config.return_value.callback_url = ''
        mock_config.return_value.integration_service = 'Sync'
        mock_config.return_value.log_level = 'DEBUG'
        self.m.record_uid = '123'

        resp = self.m._outbound_handler({}, 'fake-merchant-id', 'update')

        self.assertEqual({"error_codes": [], 'json': 'test'}, resp)

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_success_response(self, mock_request, mock_encode, mock_decode):
        mock_encode.return_value = {'json': self.json_data}
        mock_decode.return_value = json.dumps(self.json_data)

        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(self.json_data)

        mock_request.return_value = response

        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(response._content, resp)

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_logs_for_redirects(self, mock_request, mock_logger,  mock_encode, mock_decode):
        mock_encode.return_value = {'json': self.json_data}
        mock_decode.return_value = json.dumps(self.json_data)

        response = requests.Response()
        response.status_code = 200
        response.history = [requests.Response()]
        response._content = json.dumps(self.json_data)

        mock_request.return_value = response

        self.m.record_uid = '123'
        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertTrue(mock_logger.warning.called)
        self.assertEqual(response._content, resp)

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
        mock_back_off.is_on_cooldown.return_value = False

        expected_resp = {"error_codes": [{"code": errors[NOT_SENT]['code'],
                                          "description": errors[NOT_SENT]['message']}]}

        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_back_off.activate_cooldown.called)

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
        mock_backoff.is_on_cooldown.return_value = False

        expected_resp = {"error_codes": [{"code": errors[UNKNOWN]['code'],
                                          "description": errors[UNKNOWN]['name'] + " with status code {}"
                                          .format(response.status_code)}]}
        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_backoff.activate_cooldown.called)

    @mock.patch.object(RSA, 'decode', autospec=True)
    @mock.patch.object(RSA, 'encode', autospec=True)
    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_does_not_send_when_on_cooldown(self, mock_request, mock_back_off, mock_encode, mock_decode):
        mock_encode.return_value = {'json': self.json_data}
        mock_decode.return_value = json.dumps(self.json_data)

        mock_back_off.is_on_cooldown.return_value = True
        expected_resp = {"error_codes": [{"code": errors[NOT_SENT]['code'],
                                          "description": errors[NOT_SENT]['message']}]}
        resp = self.m._sync_outbound(self.json_data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertFalse(mock_request.called)
        self.assertFalse(mock_back_off.activate_cooldown.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_success_does_not_raise_exceptions(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"error_codes": []}

        self.m.login({})

        self.assertTrue(mock_outbound_handler.called)

    @mock.patch.object(MerchantApi, 'process_join_response')
    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_register_success_does_not_raise_exceptions(self, mock_outbound_handler, mock_process_join_response):
        mock_outbound_handler.return_value = {"error_codes": []}

        self.m.register({})

        self.assertTrue(mock_outbound_handler.called)
        self.assertTrue(mock_process_join_response.called)

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_login_handles_error_payload(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"error_codes": [{"code": 535, "description": "NO_SUCH_RECORD"}]}

        with self.assertRaises(LoginError) as e:
            self.m.login({})
        self.assertEqual(e.exception.name, "Account does not exist")

    @mock.patch.object(MerchantApi, '_outbound_handler')
    def test_register_handles_error_payload(self, mock_outbound_handler):
        mock_outbound_handler.return_value = {"error_codes": [{"code": 520, "description": "GENERAL_ERROR"}]}

        with self.assertRaises(LoginError) as e:
            self.m.register({})
        self.assertEqual(e.exception.name, "An unknown error has occurred")

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

    def test_rsa_security_encode(self):
        rsa = RSA([{'type': 'bink_private_key', 'value': self.test_private_key}])

        request_params = rsa.encode(self.json_data)

        self.assertEqual(request_params, {'json': self.json_data, 'headers': {'Authorization': self.signature}})

    def test_rsa_security_decode_success(self):
        rsa = RSA([{'type': 'merchant_public_key', 'value': self.test_private_key}])
        request = requests.Request()
        request.json = self.json_data
        request.headers['AUTHORIZATION'] = self.signature
        request.content = self.json_data

        request_json = rsa.decode(request)

        self.assertEqual(request_json, self.json_data)

    def test_rsa_security_decode_raises_exception_on_fail(self):
        rsa = RSA([{'type': 'merchant_public_key', 'value': self.test_private_key}])
        request = requests.Request()
        request.json = self.json_data
        request.headers['AUTHORIZATION'] = 'bad signature'
        request.content = self.json_data

        with self.assertRaises(AgentError):
            rsa.decode(request)
