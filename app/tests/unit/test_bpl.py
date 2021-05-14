import settings
from flask_testing import TestCase
from unittest import mock

settings.API_AUTH_ENABLED = False
from app.bpl_callback import JoinCallbackBpl  # noqa
from app import create_app  # noqa


data = {"UUID": "7e54d768-033e-40fa-999a-76c21bdd9c42",
        "email": "ncostaa@bink.com",
        "account_number": 56789,
        "third_party_identifier": "8v5zjgey0xd7k618x43wmpo2139lq4r8"
        }

headers = {'Content-type': 'application/json'}


class TestBplCallback(TestCase):

    def create_app(self):
        return create_app(self)

    @mock.patch.object(JoinCallbackBpl, 'update_hermes')
    @mock.patch.object(JoinCallbackBpl, 'json_data')
    def test_post(self, mock_json_data, mock_update_hermes):
        mock_json_data.return_value = data
        url = "join/bpl/bpl-trenette"
        response = self.client.post(url, data=data, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'success': True})
