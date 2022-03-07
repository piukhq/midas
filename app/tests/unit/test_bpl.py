import datetime
import json
from decimal import Decimal
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock
from urllib.parse import urljoin

import arrow
import httpretty
from flask_testing import TestCase

import settings
from app.agents.bpl import Bpl
from app.vouchers import VoucherState, VoucherType, voucher_state_names

settings.API_AUTH_ENABLED = False
from app.api import create_app  # noqa
from app.bpl_callback import JoinCallbackBpl  # noqa

data = {
    "UUID": "7e54d768-033e-40fa-999a-76c21bdd9c42",
    "email": "ncostaa@bink.com",
    "account_number": 56789,
    "third_party_identifier": "8v5zjgey0xd7k618x43wmpo2139lq4r8",
}

headers = {"Content-type": "application/json"}


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

            self.bpl = Bpl(
                retry_count=1,
                user_info={
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
                        "merchant_identifier": "54a259f2-3602-4cc8-8f57-1239de7e5700",
                    },
                    "channel": "com.bink.wallet",
                },
                scheme_slug="bpl-trenette",
            )
            self.bpl.base_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/"

    @mock.patch.object(JoinCallbackBpl, "process_join_callback")
    def test_post(self, mock_process_join_callback):
        url = "join/bpl/bpl-trenette"
        response = self.client.post(url, data=json.dumps(data), headers=headers)
        self.assertTrue(mock_process_join_callback.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"success": True})

    @httpretty.activate
    def test_balance(self):
        url = f"{self.bpl.base_url}54a259f2-3602-4cc8-8f57-1239de7e5700"
        response_data = {
            "UUID": "54a259f2-3602-4cc8-8f57-7839de7e5700",
            "email": "johnb@bink.com",
            "created_date": 1621266592,
            "status": "active",
            "account_number": "TRNT9288336436",
            "current_balances": [{"value": 0.1, "campaign_slug": "mocked-trenette-active-campaign"}],
            "transaction_history": [],
            "pending_rewards": [],
            "rewards": [
                {
                    "status": voucher_state_names[VoucherState.IN_PROGRESS],
                    "type": VoucherType.STAMPS.value,
                    "issued_date": 1629385871,
                    "expiry_date": 1629385871,
                    "code": "somecode",
                    "value": 0.1,
                    "target_value": 0.1,
                }
            ],
        }
        httpretty.register_uri(
            httpretty.GET, url, status=HTTPStatus.OK, responses=[httpretty.Response(body=json.dumps(response_data))]
        )
        api_url = urljoin(settings.HERMES_URL, "schemes/accounts/1/credentials")
        httpretty.register_uri(
            httpretty.PUT,
            api_url,
            status=HTTPStatus.OK,
        )
        balance = self.bpl.balance()
        self.assertEqual(balance.value, Decimal("0.1"))
        self.assertEqual(balance.vouchers[0].value, Decimal("0.1"))

    @httpretty.activate
    def test_vouchers(self):
        url = f"{self.bpl.base_url}54a259f2-3602-4cc8-8f57-1239de7e5700"
        response_data = {
            "UUID": "54a259f2-3602-4cc8-8f57-7839de7e5700",
            "email": "johnb@bink.com",
            "created_date": 1621266592,
            "status": "active",
            "account_number": "TRNT9288336436",
            "current_balances": [{"value": 0.1, "campaign_slug": "mocked-trenette-active-campaign"}],
            "transaction_history": [],
            "pending_rewards": [
                {
                    "created_date": arrow.get(datetime.date(2013, 5, 5)).int_timestamp,
                    "conversion_date": arrow.get(datetime.date(2021, 3, 16)).int_timestamp,
                },
                {
                    "created_date": arrow.get(datetime.date(2013, 5, 5)).int_timestamp,
                    "conversion_date": arrow.get(datetime.date(2022, 3, 7)).int_timestamp,
                },
            ],
            "rewards": [
                {
                    "status": voucher_state_names[VoucherState.IN_PROGRESS],
                    "type": VoucherType.STAMPS.value,
                    "issued_date": 1629385871,
                    "expiry_date": 1629385871,
                    "code": "somecode",
                },
            ],
        }
        httpretty.register_uri(
            httpretty.GET, url, status=HTTPStatus.OK, responses=[httpretty.Response(body=json.dumps(response_data))]
        )
        api_url = urljoin(settings.HERMES_URL, "schemes/accounts/1/credentials")
        httpretty.register_uri(
            httpretty.PUT,
            api_url,
            status=HTTPStatus.OK,
        )
        balance = self.bpl.balance()
        self.assertEqual(balance.vouchers[1].value, None)
        self.assertEqual(4, len(balance.vouchers))
        # Test voucher code format for pending vouchers
        self.assertEqual("Due:16thMar 2021", balance.vouchers[2].code)
        self.assertEqual("Due: 7thMar 2022", balance.vouchers[3].code)

    @mock.patch("app.bpl_callback.update_hermes", autospec=True)
    @mock.patch("app.bpl_callback.collect_credentials", autospec=True)
    def test_requests_retry_session(self, mock_collect_credentials, mock_update_hermes):
        url = "join/bpl/bpl-trenette"
        self.client.post(url, data=json.dumps(data), headers=headers)
        self.assertTrue(mock_collect_credentials.called)
        self.assertTrue(mock_update_hermes.called)

    @mock.patch("app.agents.base.ApiMiner.make_request")
    @mock.patch("app.agents.base.BaseMiner.consent_confirmation")
    def test_marketing_prefs(self, mock_consent_confirmation, mock_make_request):
        consents = {"consents": [{"key": "Consent 1", "value": "true"}]}
        bpl_payload = {
            "credentials": consents,
            "marketing_preferences": [{"key": "marketing_pref", "value": "true"}],
            "callback_url": self.bpl.callback_url,
            "third_party_identifier": "7gl82g4y5pvzx1wj5noqrj3dke7m9092",
        }
        self.bpl.join(consents)
        mock_make_request.assert_called_with(
            f"{self.bpl.base_url}enrolment", method="post", audit=True, json=bpl_payload
        )
