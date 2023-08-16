import json
import unittest
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock, call

import httpretty
from soteria.configuration import Configuration

import settings
from app.agents.slimchickens import SlimChickens
from app.exceptions import AccountAlreadyExistsError, BaseError, WeakPassword
from app.scheme_account import JourneyTypes

settings.API_AUTH_ENABLED = False

TIME_FORMAT = "YYYY-MM-DD HH:mm:ss"

OUTBOUND_SECURITY_CREDENTIALS = {
    "outbound": {
        "service": Configuration.OAUTH_SECURITY,
        "credentials": [
            {
                "value": {
                    "username": "MichaelBink",
                    "password": "91PPn95Dae5BdYS$7R",
                },
            }
        ],
    },
}

CREDENTIALS = {
    "username": "janedoe@test.com",
    "firstName": "Jane",
    "lastName": "Doe",
    "email": "janedoe@test.com",
    "password": "fakepass?",
    "dob": "1979-05-10T00:00:00Z",
    "attributes": {"optin2": "true"},
    "channels": [{"channelKey": "1eceec21734546b6b7d9a0f4a307c94b"}],
}

RESPONSE_JSON_200 = {
    "consumer": {
        "username": "jane@test.com",
        "userKey": "3bc1819c196a4996ba8c991efa91ffeb",
        "lastName": "Doe",
        "firstName": "Jane",
        "email": "jane@test.com",
        "password": None,
        "phoneNumber": None,
        "account": {
            "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
            "name": "Eagle Eye UAT",
            "description": None,
            "userListUri": None,
            "channelListUri": None,
            "uri": None,
            "imageUrl": None,
            "category": None,
            "subCategory": None,
            "contactName": None,
            "contactPhone": None,
            "contactEmail": None,
            "accountNumber": None,
            "products": None,
            "socialmediaProviders": None,
            "accountGroups": None,
            "address": None,
            "doNotReplyEmail": None,
            "deviceOwnershipThreshold": None,
            "generateKeys": False,
            "keysGeneratedOn": None,
            "stock": False,
            "beaconIdentifier": None,
            "monthsToRetain": None,
        },
        "device": None,
        "uri": "https://podifi-demo.2ergo.com/api/core/consumer/3bc1819c196a4996ba8c991efa91ffeb",
        "roles": ["ROLE_CONSUMER"],
        "identifiNotification": None,
        "postcode": None,
        "sex": "UNKNOWN",
        "monthYearOfBirth": "05/1979",
        "dob": "1979-05-10T00:00:00Z",
        "imageUrl": None,
        "membershipNo": None,
        "marketingPushEnabled": True,
        "consumerOptIns": None,
        "attributes": {"optin2": "true"},
        "socialLoginId": None,
        "airWalletId": "161000720",
        "inviteId": None,
        "channels": [
            {
                "name": "Eagle Eye UAT (Slim Chickens)",
                "description": "Eagle Eye UAT (Slim Chickens and Bink)",
                "channelKey": "1eceec21734546b6b7d9a0f4a307c94b",
                "account": None,
                "uri": "https://podifi-demo.2ergo.com/api/core/channel/1eceec21734546b6b7d9a0f4a307c94b",
                "facebookApplicationId": None,
                "googleClientId": None,
                "googleClientSecret": None,
                "appleClientSecret": None,
                "appleKeyId": None,
                "appleTeamId": None,
                "heroImageAspectRatio": "32:15",
                "channelConfiguration": None,
                "beaconMessage": None,
                "integrationPartner": "AIR_WALLET",
                "useBlackouts": False,
                "integrationUsername": None,
                "integrationPassword": None,
                "tagKey": None,
                "siteGroupKey": None,
                "integrationUnitId": None,
                "refresh": False,
                "jwtSecret": None,
                "identitySuffix": None,
                "facebookAppSecret": None,
                "azureTenant": None,
                "azureApplicationId": None,
                "azureUserFlow": None,
                "airCampaignSync": False,
            }
        ],
        "passbookUrl": None,
        "createdDate": "2023-08-01T14:27:02Z",
        "lastActive": "2023-08-03T15:27:59Z",
        "smsVerified": False,
        "emailVerified": False,
        "airConsumerId": None,
        "rateApp": False,
        "blocked": False,
        "azureJwt": None,
        "deleteImage": False,
        "addresses": None,
        "segmentation": None,
        "externalId": None,
        "membershipNumber": None,
        "gender": None,
        "dateOfBirth": 295142400000,
        "mobile": None,
        "monthOfBirth": "05/1979",
        "fullname": "Jane Doe",
    }
}


class TestSlimChicken(unittest.TestCase):
    def setUp(self):
        self.outbound_security_credentials = OUTBOUND_SECURITY_CREDENTIALS
        self.credentials = CREDENTIALS

        with mock.patch("app.agents.base.Configuration") as mock_configuration:
            mock_config_object = MagicMock()
            mock_config_object.security_credentials = self.outbound_security_credentials
            mock_config_object.integration_service = "SYNC"
            mock_configuration.return_value = mock_config_object
            self.slim_chickens = SlimChickens(
                retry_count=1,
                user_info={
                    "user_set": "27558",
                    "credentials": self.credentials,
                    "status": 442,
                    "journey_type": JourneyTypes.JOIN,
                    "scheme_account_id": 94531,
                    "channel": "com.bink.wallet",
                },
                scheme_slug="slim-chickens",
            )
            self.slim_chickens.base_url = "https://demoapi.podifi.com/"
            self.slim_chickens.max_retries = 0

    def test_authenticate(self):
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "janedoe@test.com",
            "password": "fakepass?",
            "dob": "1979-05-10T00:00:00Z",
            "attributes": {"optin2": "true"},
        }
        self.slim_chickens._authenticate(username="testeruser", password="test-pass")
        auth_header = self.slim_chickens.headers["Authorization"]
        self.assertTrue(auth_header.startswith("Basic "))

    @httpretty.activate
    def test_join_account_already_exists(self):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"
        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.CONFLICT,
            responses=[
                httpretty.Response(
                    body=json.dumps({"errors": {"1055": "Password is required"}}),
                    status=HTTPStatus.CONFLICT,
                )
            ],
        )
        self.slim_chickens.username = "testuser"
        self.slim_chickens.password = "password1"
        self.slim_chickens.channel_key = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.url = url
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "janedoe@test.com",
            "password": "fakepass?",
            "dob": "1979-05-10T00:00:00Z",
            "attributes": {"optin2": "true"},
        }
        self.slim_chickens.outbound_security["channel_key"] = "testing-key"
        resp = self.slim_chickens._account_already_exists()

        self.assertEqual(resp, False)

    @httpretty.activate
    def test_join_account_already_exists_error(self):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"
        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(RESPONSE_JSON_200),
                    status=HTTPStatus.OK,
                )
            ],
        )
        self.slim_chickens.username = "testuser"
        self.slim_chickens.password = "password1"
        self.slim_chickens.channel_key = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.url = url
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "janedoe@test.com",
            "password": "fakepass?",
            "dob": "1979-05-10T00:00:00Z",
            "attributes": {"optin2": "true"},
        }
        self.slim_chickens.outbound_security["channel_key"] = "testing-key"
        resp = self.slim_chickens._account_already_exists()
        self.assertEqual(resp, True)

    @httpretty.activate
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_create_account_happy_path(self, mock_signal):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"

        def custom_response(request, uri, headers):
            if custom_response.counter == 0:
                custom_response.counter += 1
                return (HTTPStatus.CONFLICT, headers, json.dumps({"errors": {"1055": "Password is required"}}))
            else:
                return (HTTPStatus.OK, headers, json.dumps(RESPONSE_JSON_200))

        custom_response.counter = 0

        httpretty.register_uri(httpretty.POST, uri=url, body=custom_response)
        self.slim_chickens.outbound_security["user_name"] = "testuser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "janedoe@test.com",
            "password": "bink7171?",
            "date_of_birth": "1979-05-10T00:00:00Z",
            "consents": [{"id": 71629, "slug": "optin2", "value": True, "created_on": "2023-08-14", "journey_type": 0}],
        }
        resp = self.slim_chickens.join()
        self.assertEqual(resp, None)
        self.assertEqual(self.slim_chickens.credentials["merchant_identifier"], RESPONSE_JSON_200["consumer"]["email"])
        expected_calls = [  # The expected call stack for signal, in order
            call("join-success"),
            call().send(self.slim_chickens, channel=self.slim_chickens.channel, slug=self.slim_chickens.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    def test_create_account_error_account_holder_exists(self):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"

        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(RESPONSE_JSON_200),
                    status=HTTPStatus.OK,
                )
            ],
        )
        self.slim_chickens.outbound_security["user_name"] = "testuser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "janedoe@test.com",
            "password": "bink7171?",
            "date_of_birth": "1979-05-10T00:00:00Z",
            "consents": [{"id": 71629, "slug": "optin2", "value": True, "created_on": "2023-08-14", "journey_type": 0}],
        }
        with self.assertRaises(AccountAlreadyExistsError) as e:
            self.slim_chickens.join()

        self.assertEqual(e.exception.name, "Account already exists")
        self.assertEqual(e.exception.code, 445)

    @httpretty.activate
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_create_account_unknown_error(self, mock_signal):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"

        def custom_response(request, uri, headers):
            if custom_response.counter == 0:
                custom_response.counter += 1
                return (HTTPStatus.CONFLICT, headers, json.dumps({"errors": {"1055": "Password is required"}}))
            else:
                return (HTTPStatus.BAD_REQUEST, headers, json.dumps({"errors": {"0003": "Invalid JSON"}}))

        custom_response.counter = 0

        httpretty.register_uri(httpretty.POST, uri=url, body=custom_response)
        self.slim_chickens.outbound_security["user_name"] = "testuser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "janedoe@test.com",
            "password": "bink7171?",
            "date_of_birth": "1979-05-10T00:00:00Z",
            "consents": [{"id": 71629, "slug": "optin2", "value": True, "created_on": "2023-08-14", "journey_type": 0}],
        }
        with self.assertRaises(BaseError):
            self.slim_chickens.join()
        expected_calls = [  # The expected call stack for signal, in order
            call("join-fail"),
            call().send(self.slim_chickens, channel=self.slim_chickens.channel, slug=self.slim_chickens.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_create_account_eror_checking_if_account_exists(self, mock_signal):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"

        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.BAD_REQUEST,
            responses=[
                httpretty.Response(
                    body=json.dumps({"errors": {"0003": "Invalid JSON"}}),
                    status=HTTPStatus.BAD_REQUEST,
                )
            ],
        )
        self.slim_chickens.outbound_security["user_name"] = "testuser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "janedoe@test.com",
            "password": "bink7171?",
            "date_of_birth": "1979-05-10T00:00:00Z",
            "consents": [{"id": 71629, "slug": "optin2", "value": True, "created_on": "2023-08-14", "journey_type": 0}],
        }
        with self.assertRaises(BaseError):
            self.slim_chickens.join()
        expected_calls = [  # The expected call stack for signal, in order
            call("join-fail"),
            call().send(self.slim_chickens, channel=self.slim_chickens.channel, slug=self.slim_chickens.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_create_account_weak_password_error(self, mock_signal):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"

        def custom_response(request, uri, headers):
            if custom_response.counter == 0:
                custom_response.counter += 1
                return (HTTPStatus.CONFLICT, headers, json.dumps({"errors": {"1055": "Password is required"}}))
            else:
                return (HTTPStatus.CONFLICT, headers, json.dumps({"errors": {"1154": "Password is too weak"}}))

        custom_response.counter = 0

        httpretty.register_uri(httpretty.POST, uri=url, body=custom_response)
        self.slim_chickens.outbound_security["user_name"] = "testuser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "janedoe@test.com",
            "password": "bink7171?",
            "date_of_birth": "1979-05-10T00:00:00Z",
            "consents": [{"id": 71629, "slug": "optin2", "value": True, "created_on": "2023-08-14", "journey_type": 0}],
        }
        with self.assertRaises(WeakPassword) as e:
            self.slim_chickens.join()
        expected_calls = [  # The expected call stack for signal, in order
            call("join-fail"),
            call().send(self.slim_chickens, channel=self.slim_chickens.channel, slug=self.slim_chickens.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)
        self.assertEqual(e.exception.name, "Join password too weak")
        self.assertEqual(e.exception.code, 905)
