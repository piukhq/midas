import json
from unittest import mock
from unittest.mock import MagicMock
import responses

from azure.keyvault.secrets import SecretClient

import settings
from app.encryption import AESCipher, get_aes_key
from app.urls import api
from flask import Flask
from flask_testing import TestCase as FlaskTestCase

encrypted_credentials = (
    AESCipher(get_aes_key("aes-keys"))
    .encrypt(
        json.dumps({"card_number": "6332040030541927282", "last_name": "Gouws", "postcode": "kt130bz", "consents": []})
    )
    .decode("utf-8")
)

europa_config_add = {
    "id": 101,
    "merchant_id": "iceland-bonus-card",
    "merchant_url": "http://127.0.0.1:6502/mock/api/v1/bink/link",
    "handler_type": 2,
    "integration_service": 0,
    "callback_url": None,
    "retry_limit": 0,
    "log_level": 0,
    "country": "GB",
    "security_credentials": {
        "inbound": {"service": 1, "credentials": []},
        "outbound": {
            "service": 2,
            "credentials": [
                {
                    "credential_type": "compound_key",
                    "storage_key": "887a96f3cebfa598b459bafc39653c9bc5cd5597a7b00eb55b9011380cc7d719",
                }
            ],
        },
    },
}

iceland_token = {
    "token_type": "Bearer",
    "expires_in": "3599",
    "ext_expires_in": "3599",
    "expires_on": "1655229463",
    "not_before": "1655225563",
    "resource": "bc4c1f60-1a60-4aff-b156-c8d496ef1bd8",
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6ImpTMVhvMU9XRGpfNTJ2YndHTmd2UU8yVnpNYyIsImtpZCI6ImpTMVhvMU9XRGpfNTJ2YndHTmd2UU8yVnpNYyJ9.eyJhdWQiOiJiYzRjMWY2MC0xYTYwLTRhZmYtYjE1Ni1jOGQ0OTZlZjFiZDgiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC82MTYwYTlhZC01MDk1LTQzOWEtOGRhOS0yMWVhMDJhM2Y2NTEvIiwiaWF0IjoxNjU1MjI1NTYzLCJuYmYiOjE2NTUyMjU1NjMsImV4cCI6MTY1NTIyOTQ2MywiYWlvIjoiRTJaZ1lMaFI2dmE3OWZ4RHZ1blRaN0Y5YnY1VENRQT0iLCJhcHBpZCI6ImJjNGMxZjYwLTFhNjAtNGFmZi1iMTU2LWM4ZDQ5NmVmMWJkOCIsImFwcGlkYWNyIjoiMSIsImlkcCI6Imh0dHBzOi8vc3RzLndpbmRvd3MubmV0LzYxNjBhOWFkLTUwOTUtNDM5YS04ZGE5LTIxZWEwMmEzZjY1MS8iLCJvaWQiOiI3YmMzOWMzNi1mYTc5LTQyMjktODA1Yi05MmMwNmY0MWExMTEiLCJyaCI6IjAuQVFJQXJhbGdZWlZRbWtPTnFTSHFBcVAyVVdBZlRMeGdHdjlLc1ZiSTFKYnZHOWdDQUFBLiIsInN1YiI6IjdiYzM5YzM2LWZhNzktNDIyOS04MDViLTkyYzA2ZjQxYTExMSIsInRpZCI6IjYxNjBhOWFkLTUwOTUtNDM5YS04ZGE5LTIxZWEwMmEzZjY1MSIsInV0aSI6IkdRX1k5Tkk1eVV1dEt6cjZEUnNlQUEiLCJ2ZXIiOiIxLjAifQ.BOFlPPcwilJZ0o89px8DeCzXiBOJH8lf6-r3J2NCKspSCAJkpaLmFILJVIEIvEI9aMnIeB-hIGQgWMPqgNqg9fI7KEdM8sOi-zdswHYhyPpsRceQtT2aDjl5581r6BQ6obwRtrb7BwS_4ZoFqIssb51frjSpvfX3TuYgiY27DN6dF_ghMpcy3AC2oUgxXTR3UZuRM_bs4QTzjTWjQStsr6FvEHac6rCwJFYNpdwqSKYDtDyS9qT15plfZRri8PFKKUqp2ASRh0iCTw1O5EhIZEnyddjywnFg-824fvMsquxR50AHmBmkuqucZ8APdgkSgR8wsGI5V0Z0mBUxiJJ97Q",
}

storage_key = '{"data": {"payload": {"client_id": "27e76b84-c087-4a98-8d7c-8f4952f443dc", "client_secret": "WtVzP+E9jWu0abA299vN/Zw/EaH4u03xGMXst7lfZCs=", "grant_type": "client_credentials", "resource": "27e76b84-c087-4a98-8d7c-8f4952f443dc"}, "prefix": "Bearer", "url": "http://api-reflector/mock/token"}}'

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
    def create_app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        api.init_app(app)
        return app

    @responses.activate
    def test_add_journey_success(self):
        # Mocked endpoints
        europa_config_endpoint = responses.add(
            responses.GET, f"{settings.CONFIG_SERVICE_URL}/configuration", json=europa_config_add, status=200
        )
        iceland_token_endpoint = responses.add(
            responses.POST, "http://api-reflector/mock/token", json=iceland_token, status=200
        )
        iceland_link_endpoint = responses.add(
            responses.POST, "http://127.0.0.1:6502/mock/api/v1/bink/link", json=iceland_add_response, status=200
        )
        hermes_credentials_endpoint = responses.add(
            responses.PUT,
            f"{settings.HERMES_URL}/schemes/accounts/159779/credentials",
            json={"updated": ["card_number", "barcode", "merchant_identifier"]},
            status=200,
        )
        hades_balance_endpoint = responses.add(responses.POST, f"{settings.HADES_URL}/balance")
        hades_transactions_endpoint = responses.add(responses.POST, f"{settings.HADES_URL}/transactions")
        hermes_status_endpoint = responses.add(responses.POST, f"{settings.HERMES_URL}/schemes/accounts/159779/status")

        # Mock get vault secrets
        mock_secret_client = MagicMock()
        mock_secret_client.value = storage_key

        # Request from Hermes
        parameters = {
            "scheme_account_id": 159779,
            "credentials": encrypted_credentials,
            "user_set": "40776",
            "status": 1001,
            "journey_type": 1,
        }
        headers = {"transaction": "ad6d704c-e0c7-11ec-929b-acde48001122", "User-agent": "Hermes on C02DK4ZLMD6M"}
        with mock.patch.object(SecretClient, "get_secret", return_value=mock_secret_client):
            response = self.client.get("/iceland-bonus-card/balance", headers=headers, query_string=parameters)

        self.assertEqual(
            {
                "points": 21.21,
                "value": 21.21,
                "value_label": "£21.21",
                "reward_tier": 0,
                "scheme_account_id": 159779,
                "user_set": "40776",
                "points_label": "21",
            },
            response.json,
        )
        self.assertEqual(1, europa_config_endpoint.call_count)
        self.assertEqual(1, iceland_token_endpoint.call_count)
        self.assertEqual(1, iceland_link_endpoint.call_count)
        self.assertEqual(1, hermes_credentials_endpoint.call_count)
        self.assertEqual(1, hades_balance_endpoint.call_count)
        self.assertEqual(1, hades_transactions_endpoint.call_count)
        self.assertEqual(1, hermes_status_endpoint.call_count)
        self.assertEqual(7, len(responses.calls))
