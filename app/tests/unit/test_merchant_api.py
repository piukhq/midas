import json

import requests

from app.agents.base import MerchantApi
from unittest import mock, TestCase

from app.agents.exceptions import NOT_SENT, errors, UNKNOWN, LoginError


class TestMerchantApi(TestCase):
    def setUp(self):
        self.m = MerchantApi(1, 1)
        self.data = json.dumps({'message_uid': '123-123-123-123'})
        self.config = {
            'log_level': 'DEBUG',
            'merchant_id': 'fake-merchant',
            'merchant_url': '',
            'security_service': 'RSA',
            'security_credentials': 'creds',
            'handler_type': 'join',
            'integration_service': 'sync',
            'retry_limit': 2,
        }

    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_outbound_handler_returns_reponse_json(self, mock_sync_outbound):
        mock_sync_outbound.return_value = json.dumps({"error_codes": [], 'json': 'test'})

        self.m.record_uid = '123'
        resp = self.m._outbound_handler({}, 1, 'update')

        self.assertEqual({"error_codes": [], 'json': 'test'}, resp)

    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_success_response(self, mock_request):
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"stuff": "more stuff"})

        mock_request.return_value = response

        resp = self.m._sync_outbound(self.data, self.config)

        self.assertEqual(response._content, resp)

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_logs_for_redirects(self, mock_request, mock_logger):
        response = requests.Response()
        response.status_code = 200
        response.history = [requests.Response()]
        response._content = json.dumps({"stuff": "more stuff"})

        mock_request.return_value = response

        self.m.record_uid = '123'
        resp = self.m._sync_outbound(self.data, self.config)

        self.assertTrue(mock_logger.warning.called)
        self.assertEqual(response._content, resp)

    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_returns_error_payload_on_system_errors(self, mock_request, mock_back_off):
        response = requests.Response()
        response.status_code = 503

        mock_request.return_value = response
        mock_back_off.is_on_cooldown.return_value = False

        expected_resp = {"error_codes": [{"code": errors[NOT_SENT]['code'],
                                          "description": errors[NOT_SENT]['message']}]}

        resp = self.m._sync_outbound(self.data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_back_off.activate_cooldown.called)

    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_general_errors(self, mock_request, mock_backoff):
        response = requests.Response()
        response.status_code = 500

        mock_request.return_value = response
        mock_backoff.is_on_cooldown.return_value = False

        expected_resp = {"error_codes": [{"code": errors[UNKNOWN]['code'],
                                          "description": errors[UNKNOWN]['name'] + " with status code {}"
                                          .format(response.status_code)}]}
        resp = self.m._sync_outbound(self.data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertTrue(mock_backoff.activate_cooldown.called)

    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_does_not_send_when_on_cooldown(self, mock_request, mock_back_off):
        mock_back_off.is_on_cooldown.return_value = True
        expected_resp = {"error_codes": [{"code": errors[NOT_SENT]['code'],
                                          "description": errors[NOT_SENT]['message']}]}
        resp = self.m._sync_outbound(self.data, self.config)

        self.assertEqual(json.dumps(expected_resp), resp)
        self.assertFalse(mock_request.called)
        self.assertFalse(mock_back_off.activate_cooldown.called)

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
            self.m.login({})
        self.assertEqual(e.exception.name, "An unknown error has occurred")
