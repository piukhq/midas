import json
import time
from unittest import mock
from unittest.mock import MagicMock

import responses
from azure.keyvault.secrets import SecretClient
from flask import Flask
from flask_testing import TestCase as FlaskTestCase
from soteria.configuration import Configuration
from user_auth_token import UserTokenStore

import settings
from app.encryption import AESCipher, get_aes_key
from app.urls import api

# Merchant details
slug = "iceland-bonus-card"
scheme_account_id = 159779
merchant_url = "http://iceland-endpoint/api/v1/bink/link"
token_endpoint = "http://token-endpoint/token"

# Request from Hermes
encrypted_credentials = (
    AESCipher(get_aes_key("aes-keys"))
    .encrypt(
        json.dumps({"card_number": "6332040030541927282", "last_name": "Jones", "postcode": "kt130bm", "consents": []})
    )
    .decode("utf-8")
)
parameters = {
    "scheme_account_id": f"{scheme_account_id}",
    "credentials": encrypted_credentials,
    "user_set": "40776",
    "status": 1001,
    "journey_type": 1,
}
headers = {"transaction": "ad6d704c-e0c7-11ec-929b-acde48001122", "User-agent": "Hermes on C02DK4ZLMD6M"}

# Europa config for Iceland add journey
europa_config_add = {
    "id": 101,
    "merchant_id": slug,
    "merchant_url": merchant_url,
    "handler_type": Configuration.VALIDATE_HANDLER,
    "integration_service": Configuration.SYNC_INTEGRATION,
    "callback_url": None,
    "retry_limit": 0,
    "log_level": Configuration.DEBUG_LOG_LEVEL,
    "country": "GB",
    "security_credentials": {
        "inbound": {"service": Configuration.OPEN_AUTH_SECURITY, "credentials": []},
        "outbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": "compound_key",
                    "storage_key": "*****",
                }
            ],
        },
    },
}

# Vault storage key
storage_key = (
    '{"data": {"payload": {"client_id": "*****", "client_secret": "*****", "grant_type": "client_credentials", '
    '"resource": "27e76b84-c087-4a98-8d7c-8f4952f443dc"}, "prefix": "Bearer", "url": "' + f"{token_endpoint}" + '"}}'
)

# Iceland merchant endpoints
iceland_token = {
    "token_type": "Bearer",
    "expires_in": "3599",
    "ext_expires_in": "3599",
    "expires_on": "1655229463",
    "not_before": "1655225563",
    "resource": "bc4c1f60-1a60-4aff-b156-c8d496ef1bd8",
    "access_token": "*****",
}
iceland_add_response = {
    "card_number": "6332040030541927282",
    "barcode": "63320400305419272820080",
    "balance": 21.21,
    "unit": "GBP",
    "alt_balance": 0.0,
    "transactions": [
        {"timestamp": "2021-02-04T13:50:26", "reference": "CREDIT", "value": 1.0, "unit": "GBP"},
        {"timestamp": "2020-12-14T18:06:56", "reference": "CREDIT", "value": 1.0, "unit": "GBP"},
        {"timestamp": "2020-07-20T07:44:19", "reference": "CREDIT", "value": 1.15, "unit": "GBP"},
        {"timestamp": "2020-07-18T10:44:18", "reference": "CREDIT", "value": 5.0, "unit": "GBP"},
        {"timestamp": "2020-06-03T01:55:29", "reference": "DEBIT", "value": -2.0, "unit": "GBP"},
    ],
    "message_uid": "08a83617-aef9-4213-88af-994900ce8f99",
    "record_uid": "593r1mq7x2zyjnd05xlw0dpo5eg4vk8l",
    "merchant_scheme_id1": "vv3mdp982zx1knzrjv864qleogj75yr0",
    "merchant_scheme_id2": "536058122",
}


class TestIcelandAdd(FlaskTestCase):
    maxDiff = None

    def create_app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        api.init_app(app)
        return app

    @responses.activate
    def test_add_journey_success(self):
        # Clear Redis for scheme account id
        UserTokenStore(settings.REDIS_URL).delete(scheme_account_id)

        # Mocked endpoints
        # Europa
        responses.add(responses.GET, f"{settings.CONFIG_SERVICE_URL}/configuration", json=europa_config_add, status=200)
        # Iceland
        responses.add(responses.POST, token_endpoint, json=iceland_token, status=200)
        responses.add(responses.POST, merchant_url, json=iceland_add_response, status=200)
        # Atlas
        responses.add(responses.POST, f"{settings.ATLAS_URL}/audit/membership/", body="Data saved.", status=200)
        # Hermes
        responses.add(
            responses.PUT,
            f"{settings.HERMES_URL}/schemes/accounts/{scheme_account_id}/credentials",
            json={"updated": ["card_number", "barcode", "merchant_identifier"]},
            status=200,
        )
        responses.add(responses.POST, f"{settings.HERMES_URL}/schemes/accounts/{scheme_account_id}/status")
        # Hades
        responses.add(responses.POST, f"{settings.HADES_URL}/balance")
        responses.add(responses.POST, f"{settings.HADES_URL}/transactions")

        # Mock get vault secrets
        mock_secret_client = MagicMock()
        mock_secret_client.value = storage_key

        with mock.patch.object(SecretClient, "get_secret", return_value=mock_secret_client):
            # Request from Hermes
            response = self.client.get("/iceland-bonus-card/balance", headers=headers, query_string=parameters)

        # This delay is necessary for threading to finish
        time.sleep(1)

        expected_endpoint_calls = [  # noqa
            {
                "request_url": f"{settings.CONFIG_SERVICE_URL}/configuration"
                f"?merchant_id=iceland-bonus-card&handler_type=2",
                "request_body": None,
            },
            {
                "request_url": token_endpoint,
                "request_body": "grant_type=client_credentials&client_secret=%2A%2A%2A%2A%2A&client_id="
                "%2A%2A%2A%2A%2A&resource=27e76b84-c087-4a98-8d7c-8f4952f443dc",
            },
            {
                "request_url": f"{settings.ATLAS_URL}/audit/membership/",
                "request_body": '{"audit_logs": [{"audit_log_type": "REQUEST", "channel": "", "membership_plan_slug": '
                '"iceland-bonus-card", "handler_type": "VALIDATE", "message_uid": '
                '"1e941f57-69c6-483a-8d98-c531dc794500", "record_uid": '
                '"qm35vl2e897k46o0q4061djrgyq0xpzo", "timestamp": 1655828613, "integration_service": '
                '"SYNC", "payload": {"card_number": "6332040030541927282", "last_name": "Jones", '
                '"postcode": "kt130bm", "message_uid": "1e941f57-69c6-483a-8d98-c531dc794500", '
                '"record_uid": "qm35vl2e897k46o0q4061djrgyq0xpzo", "callback_url": null, '
                '"merchant_scheme_id1": "vv3mdp982zx1knzrjv864qleogj75yr0", "merchant_scheme_id2": '
                "null}}]}",
            },
            {
                "request_url": merchant_url,
                "request_body": '{"card_number": "6332040030541927282", "last_name": "Jones", "postcode": "kt130bm", '
                '"message_uid": "1e941f57-69c6-483a-8d98-c531dc794500", "record_uid": '
                '"qm35vl2e897k46o0q4061djrgyq0xpzo", "callback_url": null, "merchant_scheme_id1": '
                '"vv3mdp982zx1knzrjv864qleogj75yr0", "merchant_scheme_id2": null}',
            },
            {
                "request_url": f"{settings.ATLAS_URL}/audit/membership/",
                "request_body": '{"audit_logs": [{"audit_log_type": "RESPONSE", "channel": "", "membership_plan_slug": '
                '"iceland-bonus-card", "handler_type": "VALIDATE", "message_uid": '
                '"1e941f57-69c6-483a-8d98-c531dc794500", "record_uid": '
                '"qm35vl2e897k46o0q4061djrgyq0xpzo", "timestamp": 1655828613, "integration_service": '
                '"SYNC", "payload": {"card_number": "6332040030541927282", "barcode": '
                '"63320400305419272820080", "balance": 21.21, "unit": "GBP", "alt_balance": 0.0, '
                '"transactions": [{"timestamp": "2021-02-04T13:50:26", "reference": "CREDIT", "value": '
                '1.0, "unit": "GBP"}, {"timestamp": "2020-12-14T18:06:56", "reference": "CREDIT", '
                '"value": 1.0, "unit": "GBP"}, {"timestamp": "2020-07-20T07:44:19", "reference": '
                '"CREDIT", "value": 1.15, "unit": "GBP"}, {"timestamp": "2020-07-18T10:44:18", '
                '"reference": "CREDIT", "value": 5.0, "unit": "GBP"}, {"timestamp": '
                '"2020-06-03T01:55:29", "reference": "DEBIT", "value": -2.0, "unit": "GBP"}], '
                '"message_uid": "08a83617-aef9-4213-88af-994900ce8f99", "record_uid": '
                '"593r1mq7x2zyjnd05xlw0dpo5eg4vk8l", "merchant_scheme_id1": '
                '"vv3mdp982zx1knzrjv864qleogj75yr0", "merchant_scheme_id2": "536058122"}, '
                '"status_code": 200}]}',
            },
            {
                "request_url": f"{settings.HERMES_URL}/schemes/accounts/{scheme_account_id}/credentials",
                "request_body": '{"barcode": "63320400305419272820080", "card_number": "6332040030541927282", '
                '"merchant_identifier": "536058122"}',
            },
            {
                "request_url": f"{settings.HADES_URL}/balance",
                "request_body": '{"points": 21.21, "value": 21.21, "value_label": "\\u00a321.21", "reward_tier": 0, '
                '"scheme_account_id": 159779, "user_set": "40776", "points_label": "21"}',
            },
            {
                "request_url": f"{settings.HADES_URL}/transactions",
                "request_body": '[{"date": "2021-02-04 13:50:26+00:00", "description": "CREDIT", "points": 1.0, '
                '"hash": "22eae37eaed587a0ee4df69a21a8e3a5", "scheme_account_id": 159779, '
                '"user_set": "40776"}, {"date": "2020-12-14 18:06:56+00:00", "description": '
                '"CREDIT", "points": 1.0, "hash": "f4c65a4f7fb4bd13a960a70dd6224043", '
                '"scheme_account_id": 159779, "user_set": "40776"}, {"date": '
                '"2020-07-20 07:44:19+00:00", "description": "CREDIT", "points": 1.15, "hash": '
                '"163387a9f0d74e821413f8a82ceecada", "scheme_account_id": 159779, "user_set": '
                '"40776"}, {"date": "2020-07-18 10:44:18+00:00", "description": "CREDIT", "points": '
                '5.0, "hash": "b071bfdac4e2c2dba674246c15f2258c", "scheme_account_id": 159779, '
                '"user_set": "40776"}, {"date": "2020-06-03 01:55:29+00:00", "description": "DEBIT", '
                '"points": -2.0, "hash": "38f35e95596f8dcc0ab3795a83efade8", "scheme_account_id": '
                '159779, "user_set": "40776"}]',
            },
            {
                "request_url": f"{settings.HERMES_URL}/schemes/accounts/{scheme_account_id}/status",
                "request_body": '{"status": 1, "journey": null, "user_info": {"credentials": {"card_number": '
                '"6332040030541927282", "last_name": "Jones", "postcode": "kt130bm", "consents": [], '
                '"barcode": "63320400305419272820080", "merchant_identifier": "536058122"}, "status": '
                '1001, "user_set": "40776", "journey_type": 1, "scheme_account_id": 159779}}',
            },
        ]

        actual_endpoint_calls = [  # noqa
            {
                "request_url": call.request.url,
                "request_body": call.request.body.decode("utf-8")
                if isinstance(call.request.body, bytes)
                else call.request.body,
            }
            for call in responses.calls._calls
        ]

        # Hermes response
        self.assertEqual(
            {
                "points": 21.21,
                "value": 21.21,
                "value_label": "£21.21",
                "reward_tier": 0,
                "scheme_account_id": scheme_account_id,
                "user_set": "40776",
                "points_label": "21",
            },
            response.json,
        )
        # We would need to do some assertions of expected_endpoint_calls to actual_endpoint_calls
