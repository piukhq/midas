import json

import requests

from app.agents.base import MerchantApi
from unittest import mock, TestCase

from app.agents.exceptions import NOT_SENT, errors, GENERAL_ERROR


class TestMerchantApi(TestCase):
    def setUp(self):
        self.m = MerchantApi(1, 1)
        self.data = json.dumps({})
        self.config = {
            'merchant_id': 'id',
            'merchant_url': '',
            'security_service': 'RSA',
            'security_credentials': 'creds',
            'handler_type': 'join',
            'retry_limit': 2,
        }

    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_outbound_handler_returns_reponse_json(self, mock_sync_outbound):
        mock_sync_outbound.return_value = json.dumps({"stuff": 'more stuff'})

        resp = self.m._outbound_handler({}, 1, 'update')

        self.assertEqual({"stuff": 'more stuff'}, resp)

    @mock.patch('requests.post', autospec=True)
    @mock.patch('requests.Response.json', autospec=True)
    def test_sync_outbound_success_response(self, mock_json, mock_request):
        response = requests.Response()
        response.status_code = 200
        response_json = json.dumps({"stuff": "more stuff"})

        mock_request.return_value = response
        mock_json.return_value = response_json

        resp = self.m._sync_outbound(self.data, self.config)

        self.assertEqual(response_json, resp)

    @mock.patch('app.agents.base.logger', autospec=True)
    @mock.patch('requests.post', autospec=True)
    @mock.patch('requests.Response.json', autospec=True)
    def test_sync_outbound_logs_for_redirects(self, mock_json, mock_request, mock_logger):
        response = requests.Response()
        response.status_code = 200
        response.history = [requests.Response()]
        response_json = json.dumps({"stuff": "more stuff"})

        mock_request.return_value = response
        mock_json.return_value = response_json

        resp = self.m._sync_outbound(self.data, self.config)

        self.assertTrue(mock_logger.warning.called)
        self.assertEqual(response_json, resp)

    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_returns_error_payload_on_system_errors(self, mock_request, mock_back_off):
        response = requests.Response()
        response.status_code = 503

        mock_request.return_value = response
        mock_back_off.is_on_cooldown.return_value = False

        resp = self.m._sync_outbound(self.data, self.config)

        self.assertEqual(json.dumps({'status_code': errors[NOT_SENT]['code']}), resp)
        self.assertTrue(mock_back_off.activate_cooldown.called)

    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_general_errors(self, mock_request, mock_backoff):
        response = requests.Response()
        response.status_code = 500

        mock_request.return_value = response
        mock_backoff.is_on_cooldown.return_value = False

        resp = self.m._sync_outbound(self.data, self.config)

        self.assertEqual(json.dumps({'status_code': errors[GENERAL_ERROR]['code'],
                                     'description': 'An Unknown error has occurred with status code {}'
                                    .format(response.status_code)}), resp)
        self.assertTrue(mock_backoff.activate_cooldown.called)

    @mock.patch('app.agents.base.BackOffService', autospec=True)
    @mock.patch('requests.post', autospec=True)
    def test_sync_outbound_does_not_send_when_on_cooldown(self, mock_request, mock_back_off):
        mock_back_off.is_on_cooldown.return_value = True

        resp = self.m._sync_outbound(self.data, self.config)

        self.assertEqual(json.dumps({'status_code': errors[NOT_SENT]['code']}), resp)
        self.assertFalse(mock_request.called)
        self.assertFalse(mock_back_off.activate_cooldown.called)
