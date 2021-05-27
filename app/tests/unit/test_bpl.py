import settings
import json
import httpretty
from http import HTTPStatus
from urllib.parse import urljoin

from app.vouchers import VoucherState, VoucherType, voucher_state_names
from flask_testing import TestCase
from unittest import mock
from unittest.mock import MagicMock
from app.agents.bpl import Trenette

settings.API_AUTH_ENABLED = False
from app.bpl_callback import JoinCallbackBpl # noqa
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

    def setUp(self) -> None:
        with mock.patch("app.agents.bpl.Configuration") as mock_configuration:
            mock_config_object = MagicMock()
            mock_config_object.security_credentials = {
                "outbound": {
                    "credentials": [
                        {
                            "value": {
                                "token": "kasjfaksjha",
                            }
                        }
                    ]
                }
            }
            mock_configuration.return_value = mock_config_object

            MOCK_AGENT_CLASS_ARGUMENTS_TRENETTE = [
                1,
                {
                    "scheme_account_id": 1,
                    "status": 1,
                    "user_set": "1,2",
                    "journey_type": 2,
                    "credentials": {
                        "email": "ncostaE@bink.com",
                        "first_name": "Test",
                        "last_name": "FatFace",
                        "join_date": "2021/02/24",
                        "card_number": "TRNT9276336436",
                        "consents": [{"slug": "email_marketing", "value": True}],
                        "merchant_identifier": "54a259f2-3602-4cc8-8f57-1239de7e5700"
                    },
                    "channel": "com.bink.wallet",
                },
            ]

            self.trenette = Trenette(*MOCK_AGENT_CLASS_ARGUMENTS_TRENETTE, scheme_slug="bpl-trenette")
            self.trenette.base_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/"

    @mock.patch.object(JoinCallbackBpl, 'process_join_callback')
    def test_post(self, mock_process_join_callback):
        url = "join/bpl/bpl-trenette"
        response = self.client.post(url, data=json.dumps(data), headers=headers)
        self.assertTrue(mock_process_join_callback.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'success': True})

    @httpretty.activate
    def test_balance(self):
        url = f"{self.trenette.base_url}{'54a259f2-3602-4cc8-8f57-1239de7e5700'}"
        response_data = {
            "UUID": "54a259f2-3602-4cc8-8f57-7839de7e5700",
            "email": "johnb@bink.com",
            "created_date": 1621266592,
            "status": "active",
            "account_number": "TRNT9288336436",
            "current_balances": [
                {
                    "value": 0.1,
                    "campaign_slug": "mocked-trenette-active-campaign"
                }
            ],
            "transaction_history": [],
            "vouchers": [{"state": voucher_state_names[VoucherState.IN_PROGRESS],
                          "type": VoucherType.STAMPS.value,
                          "value": 0.1,
                          "target_value": None}]
        }
        httpretty.register_uri(
            httpretty.GET,
            url,
            status=HTTPStatus.OK,
            responses=[httpretty.Response(body=json.dumps(response_data))]

        )
        api_url = urljoin(settings.HERMES_URL, "schemes/accounts/1/credentials")
        httpretty.register_uri(
            httpretty.PUT, api_url, status=HTTPStatus.OK,
        )
        balance = self.trenette.balance()
        self.assertEqual(balance["value"], 0.1)
        self.assertEqual(balance["vouchers"][0]["value"], 0.1)

    @mock.patch("app.bpl_callback.collect_credentials", autospec=True)
    def test_requests_retry_session(self, mock_collect_credentials):
        url = "join/bpl/bpl-trenette"
        self.client.post(url, data=json.dumps(data), headers=headers)
        self.assertTrue(mock_collect_credentials.called)
