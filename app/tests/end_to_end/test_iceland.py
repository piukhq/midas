import json
import time
from unittest import mock
from unittest.mock import ANY, MagicMock

import responses
from azure.keyvault.secrets import SecretClient
from flask import Flask
from flask_testing import TestCase as FlaskTestCase
from soteria.configuration import Configuration
from user_auth_token import UserTokenStore

import settings
from app.encryption import AESCipher, get_aes_key
from app.urls import api


class Merchant:
    # Merchant details
    slug = "iceland-bonus-card"
    scheme_account_id = 159779

class EndpointURLS:
    europa_config = f"{settings.CONFIG_SERVICE_URL}/configuration"
    merchant_token = "http://token-endpoint/token"
    atlas = f"{settings.ATLAS_URL}/audit/membership/"
    merchant = "http://iceland-endpoint/api/v1/bink/link"
    hermes_credentials = f"{settings.HERMES_URL}/schemes/accounts/{Merchant.scheme_account_id}/credentials"
    hermes_status = f"{settings.HERMES_URL}/schemes/accounts/{Merchant.scheme_account_id}/status"
    hades_balance = f"{settings.HADES_URL}/balance"
    hades_transactions = f"{settings.HADES_URL}/transactions"


class HermesRequest:
    # Request from Hermes
    encrypted_credentials = (
        AESCipher(get_aes_key("aes-keys"))
        .encrypt(
            json.dumps(
                {"card_number": "6332040030541927282", "last_name": "Jones", "postcode": "kt130bm", "consents": []}
            )
        )
        .decode("utf-8")
    )
    parameters = {
        "scheme_account_id": f"{Merchant.scheme_account_id}",
        "credentials": encrypted_credentials,
        "user_set": "40776",
        "status": 1001,
        "journey_type": 1,
    }
    headers = {"transaction": "ad6d704c-e0c7-11ec-929b-acde48001122", "User-agent": "Hermes on C02DK4ZLMD6M"}
    response = {
                "points": 21.21,
                "value": 21.21,
                "value_label": "£21.21",
                "reward_tier": 0,
                "scheme_account_id": Merchant.scheme_account_id,
                "user_set": "40776",
                "points_label": "21",
            }


class MockedResponses:
    # Europa config for Iceland add journey
    europa_config_add_journey = {
        "id": 101,
        "merchant_id": Merchant.slug,
        "merchant_url": EndpointURLS.merchant,
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
    vault_storage_key = (
        '{"data": {"payload": {"client_id": "*****", "client_secret": "*****", "grant_type": "client_credentials", '
        '"resource": "27e76b84-c087-4a98-8d7c-8f4952f443dc"}, "prefix": "Bearer", "url": "'
        + f"{EndpointURLS.merchant_token}"
        + '"}}'
    )
    # Iceland merchant endpoints
    merchant_token = {
        "token_type": "Bearer",
        "expires_in": "3599",
        "ext_expires_in": "3599",
        "expires_on": "1655229463",
        "not_before": "1655225563",
        "resource": "bc4c1f60-1a60-4aff-b156-c8d496ef1bd8",
        "access_token": "*****",
    }
    merchant_add_journey = {
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


class MockedEndpoints:
    # Europa
    responses.add(responses.GET, EndpointURLS.europa_config, json=MockedResponses.europa_config_add_journey, status=200)
    # Iceland
    responses.add(responses.POST, EndpointURLS.merchant_token, json=MockedResponses.merchant_token, status=200)
    responses.add(responses.POST, EndpointURLS.merchant, json=MockedResponses.merchant_add_journey, status=200)
    # Atlas
    responses.add(responses.POST, EndpointURLS.atlas, body="Data saved.", status=200)
    # Hermes
    responses.add(
        responses.PUT,
        EndpointURLS.hermes_credentials,
        json={"updated": ["card_number", "barcode", "merchant_identifier"]},
        status=200,
    )
    responses.add(responses.POST, EndpointURLS.hermes_status)
    # Hades
    responses.add(responses.POST, EndpointURLS.hades_balance)
    responses.add(responses.POST, EndpointURLS.hades_transactions)


class ExpectedEndpointRequestBodies:
    merchant_token = (
        "grant_type=client_credentials&client_secret=%2A%2A%2A%2A%2A&client_id=%2A%2A%2A%2A%2A"
        "&resource=27e76b84-c087-4a98-8d7c-8f4952f443dc"
    )
    atlas = [
        {
            "audit_logs": [
                {
                    "audit_log_type": "REQUEST",
                    "channel": "",
                    "membership_plan_slug": "iceland-bonus-card",
                    "handler_type": "VALIDATE",
                    "message_uid": ANY,
                    "record_uid": "qm35vl2e897k46o0q4061djrgyq0xpzo",
                    "timestamp": ANY,
                    "integration_service": "SYNC",
                    "payload": {
                        "card_number": "6332040030541927282",
                        "last_name": "Jones",
                        "postcode": "kt130bm",
                        "message_uid": ANY,
                        "record_uid": "qm35vl2e897k46o0q4061djrgyq0xpzo",
                        "callback_url": None,
                        "merchant_scheme_id1": "vv3mdp982zx1knzrjv864qleogj75yr0",
                        "merchant_scheme_id2": None,
                    },
                }
            ]
        },
        {
            "audit_logs": [
                {
                    "audit_log_type": "RESPONSE",
                    "channel": "",
                    "membership_plan_slug": "iceland-bonus-card",
                    "handler_type": "VALIDATE",
                    "message_uid": ANY,
                    "record_uid": "qm35vl2e897k46o0q4061djrgyq0xpzo",
                    "timestamp": ANY,
                    "integration_service": "SYNC",
                    "payload": {
                        "card_number": "6332040030541927282",
                        "barcode": "63320400305419272820080",
                        "balance": 21.21,
                        "unit": "GBP",
                        "alt_balance": 0.0,
                        "transactions": [
                            {
                                "timestamp": "2021-02-04T13:50:26",
                                "reference": "CREDIT",
                                "value": 1.0,
                                "unit": "GBP",
                            },
                            {
                                "timestamp": "2020-12-14T18:06:56",
                                "reference": "CREDIT",
                                "value": 1.0,
                                "unit": "GBP",
                            },
                            {
                                "timestamp": "2020-07-20T07:44:19",
                                "reference": "CREDIT",
                                "value": 1.15,
                                "unit": "GBP",
                            },
                            {
                                "timestamp": "2020-07-18T10:44:18",
                                "reference": "CREDIT",
                                "value": 5.0,
                                "unit": "GBP",
                            },
                            {
                                "timestamp": "2020-06-03T01:55:29",
                                "reference": "DEBIT",
                                "value": -2.0,
                                "unit": "GBP",
                            },
                        ],
                        "message_uid": "08a83617-aef9-4213-88af-994900ce8f99",
                        "record_uid": "593r1mq7x2zyjnd05xlw0dpo5eg4vk8l",
                        "merchant_scheme_id1": "vv3mdp982zx1knzrjv864qleogj75yr0",
                        "merchant_scheme_id2": "536058122",
                    },
                    "status_code": 200,
                }
            ]
        },
    ]
    merchant = {
        "card_number": "6332040030541927282",
        "last_name": "Jones",
        "postcode": "kt130bm",
        "message_uid": ANY,
        "record_uid": "qm35vl2e897k46o0q4061djrgyq0xpzo",
        "callback_url": None,
        "merchant_scheme_id1": "vv3mdp982zx1knzrjv864qleogj75yr0",
        "merchant_scheme_id2": None,
    }
    hermes_credentials = {
        "barcode": "63320400305419272820080",
        "card_number": "6332040030541927282",
        "merchant_identifier": "536058122",
    }
    hermes_status = {
        "status": 1,
        "journey": None,
        "user_info": {
            "credentials": {
                "card_number": "6332040030541927282",
                "last_name": "Jones",
                "postcode": "kt130bm",
                "consents": [],
                "barcode": "63320400305419272820080",
                "merchant_identifier": "536058122",
            },
            "status": 1001,
            "user_set": "40776",
            "journey_type": 1,
            "scheme_account_id": Merchant.scheme_account_id,
        },
    }

    hades_balance = {
        "points": 21.21,
        "value": 21.21,
        "value_label": "£21.21",
        "reward_tier": 0,
        "scheme_account_id": Merchant.scheme_account_id,
        "user_set": "40776",
        "points_label": "21",
    }

    hades_transactions = [
        {
            "date": "2021-02-04 13:50:26+00:00",
            "description": "CREDIT",
            "points": 1.0,
            "hash": "22eae37eaed587a0ee4df69a21a8e3a5",
            "scheme_account_id": Merchant.scheme_account_id,
            "user_set": "40776",
        },
        {
            "date": "2020-12-14 18:06:56+00:00",
            "description": "CREDIT",
            "points": 1.0,
            "hash": "f4c65a4f7fb4bd13a960a70dd6224043",
            "scheme_account_id": Merchant.scheme_account_id,
            "user_set": "40776",
        },
        {
            "date": "2020-07-20 07:44:19+00:00",
            "description": "CREDIT",
            "points": 1.15,
            "hash": "163387a9f0d74e821413f8a82ceecada",
            "scheme_account_id": Merchant.scheme_account_id,
            "user_set": "40776",
        },
        {
            "date": "2020-07-18 10:44:18+00:00",
            "description": "CREDIT",
            "points": 5.0,
            "hash": "b071bfdac4e2c2dba674246c15f2258c",
            "scheme_account_id": Merchant.scheme_account_id,
            "user_set": "40776",
        },
        {
            "date": "2020-06-03 01:55:29+00:00",
            "description": "DEBIT",
            "points": -2.0,
            "hash": "38f35e95596f8dcc0ab3795a83efade8",
            "scheme_account_id": Merchant.scheme_account_id,
            "user_set": "40776",
        },
    ]


class TestIcelandAdd(FlaskTestCase):
    maxDiff = None

    def create_app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        api.init_app(app)
        return app

    @responses.activate
    def test_add_journey_success(self):
        MockedEndpoints()

        # Clear Redis for scheme account id
        UserTokenStore(settings.REDIS_URL).delete(str(Merchant.scheme_account_id))

        # Mock get vault secrets
        mock_secret_client = MagicMock()
        mock_secret_client.value = MockedResponses.vault_storage_key

        with mock.patch.object(SecretClient, "get_secret", return_value=mock_secret_client):
            # Request from Hermes
            response = self.client.get(
                "/iceland-bonus-card/balance", headers=HermesRequest.headers, query_string=HermesRequest.parameters
            )

        # This delay is necessary for threading to finish
        time.sleep(1)

        endpoint_calls = {}
        for call in responses.calls._calls:
            if not endpoint_calls.get(call.request.url):
                endpoint_calls[call.request.url] = [call.request.body]
            else:
                endpoint_calls[call.request.url].append(call.request.body)

        # Hermes response bpdy
        self.assertEqual(
            HermesRequest.response,
            response.json,
        )

        # All endpoint request bodies
        self.assertEqual(
            None, endpoint_calls[EndpointURLS.europa_config + "?merchant_id=iceland-bonus-card&handler_type=2"][0]
        )
        self.assertEqual(
            ExpectedEndpointRequestBodies.merchant_token,
            endpoint_calls[EndpointURLS.merchant_token][0],
        )
        self.assertEqual(
            ExpectedEndpointRequestBodies.atlas,
            [json.loads(body.decode()) for body in endpoint_calls[EndpointURLS.atlas]],
        )
        self.assertEqual(ExpectedEndpointRequestBodies.merchant, json.loads(endpoint_calls[EndpointURLS.merchant][0]))
        self.assertEqual(
            ExpectedEndpointRequestBodies.hermes_credentials,
            json.loads(endpoint_calls[EndpointURLS.hermes_credentials][0]),
        )
        self.assertEqual(
            ExpectedEndpointRequestBodies.hermes_status,
            json.loads(endpoint_calls[EndpointURLS.hermes_status][0]),
        )
        self.assertEqual(
            ExpectedEndpointRequestBodies.hades_balance,
            json.loads(endpoint_calls[EndpointURLS.hades_balance][0]),
        )
        self.assertEqual(
            ExpectedEndpointRequestBodies.hades_transactions,
            json.loads(endpoint_calls[EndpointURLS.hades_transactions][0]),
        )
