import json
from decimal import Decimal
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock

import arrow
import httpretty
from flask_testing import TestCase
from soteria.configuration import Configuration
from tenacity import wait_none

import settings
from app.agents.exceptions import AgentError
from app.agents.schemas import Balance
from app.agents.squaremeal import Squaremeal
from app.api import create_app
from app.scheme_account import JourneyTypes

settings.API_AUTH_ENABLED = False

SECURITY_CREDENTIALS = {
    "outbound": {
        "service": Configuration.OAUTH_SECURITY,
        "credentials": [
            {
                "value": {
                    "url": "http://fake.com",
                    "secondary-key": "12345678",
                    "client-id": "123",
                    "client-secret": "123a6ba",
                    "scope": "dunno",
                },
            }
        ],
    },
}

CREDENTIALS = {
    "first_name": "Fake",
    "last_name": "Name",
    "email": "email@domain.com",
    "password": "pAsSw0rD",
    "consents": [{"id": 11738, "slug": "Subscription", "value": False, "created_on": "1996-09-26T00:00:00"}],
}

RESPONSE_JSON_200 = {
    "Status": True,
    "Message": None,
    "Email": "email@domain.com",
    "UserId": "some_user_id",
    "FirstName": "Fake",
    "LastName": "Name",
    "Name": "Fake Name",
    "MembershipNumber": "123456789",
    "LoyaltyTier": "0",
    "Errors": None,
}


class TestSquaremealJoin(TestCase):
    def create_app(self):
        return create_app(self)

    def setUp(self):
        self.security_credentials = SECURITY_CREDENTIALS
        self.credentials = CREDENTIALS

        with mock.patch("app.agents.squaremeal.Configuration") as mock_configuration:
            mock_config_object = MagicMock()
            mock_config_object.security_credentials = self.security_credentials
            mock_config_object.integration_service = "SYNC"
            mock_configuration.return_value = mock_config_object
            self.squaremeal = Squaremeal(
                retry_count=1,
                user_info={
                    "user_set": "27558",
                    "credentials": self.credentials,
                    "status": 442,
                    "journey_type": JourneyTypes.JOIN,
                    "scheme_account_id": 94532,
                    "channel": "com.bink.wallet",
                },
                scheme_slug="squaremeal",
            )
            self.squaremeal.base_url = "https://sm-uk.azure-api.net/bink-dev/api/v1/account/"
            self.squaremeal._create_account.retry.wait = wait_none()
            self.squaremeal._get_balance.retry.wait = wait_none()

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_create_account_200(self, mock_requests_session, mock_authenticate):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.squaremeal.base_url + "register",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(RESPONSE_JSON_200),
                    status=HTTPStatus.OK,
                )
            ],
        )
        resp_json = self.squaremeal._create_account(credentials=self.credentials)

        self.assertEqual(resp_json, RESPONSE_JSON_200)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.base.BaseAgent.consent_confirmation")
    @mock.patch("app.agents.squaremeal.Squaremeal._create_account")
    def test_join_200(self, mock_create_account, mock_consent_confirmation, mock_requests_session, mock_authenticate):
        mock_create_account.return_value = RESPONSE_JSON_200
        self.squaremeal.user_info["credentials"]["consents"][0]["value"] = True
        httpretty.register_uri(
            httpretty.PUT,
            uri=self.squaremeal.base_url + "update/newsletters/some_user_id",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"Status": True, "Message": "Users mailing prefrences updated successfully", "Errors": None}
                    ),
                    status=HTTPStatus.OK,
                )
            ],
        )
        self.squaremeal.join(self.credentials)

        self.assertEqual(
            self.squaremeal.identifier, {"merchant_identifier": "some_user_id", "card_number": "123456789"}
        )
        self.assertEqual(mock_consent_confirmation.call_count, 1)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_join_401(self, mock_requests_session, mock_authenticate):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.squaremeal.base_url + "register",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({"statusCode": 401, "message": "Unauthorized. Access Denied by Gateway"}),
                    status=401,
                )
            ],
        )

        with self.assertRaises(AgentError) as e:
            self.squaremeal.join(self.credentials)

        self.assertEqual(e.exception.name, "Service connection error")
        self.assertEqual(e.exception.code, 537)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_join_422(self, mock_requests_session, mock_authenticate):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.squaremeal.base_url + "register",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "Message": "Name email@domain.com is already taken. "
                            "Email 'email@domain.com' is already taken."
                        }
                    ),
                    status=422,
                )
            ],
        )

        with self.assertRaises(AgentError) as e:
            self.squaremeal.join(self.credentials)

        self.assertEqual(e.exception.name, "Account already exists")
        self.assertEqual(e.exception.code, 445)

    BALANCE_RESPONSE_200 = {
        "Status": True,
        "Message": "1 records found",
        "MembershipNumber": "123456789",
        "UserId": "some_user_id",
        "LoyaltyTier": 0,
        "TotalPoints": 100,
        "TotalRecords": 1,
        "PointsActivity": [
            {"ConfirmedDate": "2021-10-26T08:57:21", "AwardedPoints": 100, "EarnReason": "First Card Added"}
        ],
        "Errors": None,
    }

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_get_balance_200(self, mock_requests_session, mock_authenticate):
        self.squaremeal.user_info["credentials"]["merchant_identifier"] = "some_merchant_identifier"
        httpretty.register_uri(
            httpretty.GET,
            uri=self.squaremeal.base_url + "points/some_merchant_identifier",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(self.BALANCE_RESPONSE_200),
                    status=HTTPStatus.OK,
                )
            ],
        )
        response = self.squaremeal._get_balance()

        self.assertEqual(response, self.BALANCE_RESPONSE_200)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_get_balance_422(self, mock_requests_session, mock_authenticate):
        self.squaremeal.user_info["credentials"]["merchant_identifier"] = "some_merchant_identifier"
        httpretty.register_uri(
            httpretty.GET,
            uri=self.squaremeal.base_url + "points/some_merchant_identifier",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({"Message": "500,Object reference not set to an instance of an object."}),
                    status=422,
                )
            ],
        )
        with self.assertRaises(AgentError) as e:
            self.squaremeal.balance()

        self.assertEqual(e.exception.name, "Account does not exist")
        self.assertEqual(e.exception.code, 444)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_get_balance_401(self, mock_requests_session, mock_authenticate):
        self.squaremeal.user_info["credentials"]["merchant_identifier"] = "some_merchant_identifier"
        httpretty.register_uri(
            httpretty.GET,
            uri=self.squaremeal.base_url + "points/some_merchant_identifier",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "statusCode": 401,
                            "message": "Access denied due to invalid subscription key. Make sure to "
                            "provide a valid key for an active subscription.",
                        }
                    ),
                    status=401,
                )
            ],
        )
        with self.assertRaises(AgentError) as e:
            self.squaremeal.balance()

        self.assertEqual(e.exception.name, "Service connection error")
        self.assertEqual(e.exception.code, 537)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.squaremeal.Squaremeal._get_balance")
    def test_balance_200(self, mock_get_balance, mock_requests_session, mock_authenticate):
        self.squaremeal.user_info["credentials"]["merchant_identifier"] = "some_merchant_identifier"
        mock_get_balance.return_value = self.BALANCE_RESPONSE_200
        balance = self.squaremeal.balance()

        self.assertEqual(
            balance, Balance(points=Decimal("100"), value=0, value_label="", reward_tier=0, balance=None, vouchers=None)
        )

    def test_get_security_credentials(self):
        self.assertEqual(self.squaremeal.auth_url, "http://fake.com")
        self.assertEqual(self.squaremeal.headers, {"Secondary-Key": "12345678"})

    @mock.patch("app.agents.squaremeal.Squaremeal._store_token")
    @mock.patch("app.agents.squaremeal.Squaremeal.token_store.get", return_value="fake-123")
    @mock.patch("app.agents.squaremeal.Squaremeal._refresh_token", return_value="fake-123")
    def test_authenticate(self, mock_refresh_token, mock_token_store, mock_store_token):
        current_timestamp = (arrow.utcnow().int_timestamp,)
        token = {"timestamp": current_timestamp, "sm_access_token": "fake-123"}
        mock_token_store.return_value = json.dumps(token)
        mock_store_token.return_value = token

        # Ensure all the necessary methods called when token expired
        self.squaremeal.AUTH_TOKEN_TIMEOUT = 0
        self.squaremeal.authenticate()
        self.assertEqual({"Authorization": "Bearer fake-123", "Secondary-Key": "12345678"}, self.squaremeal.headers)
        mock_refresh_token.assert_called()
        mock_store_token.assert_called()

    @mock.patch("app.agents.squaremeal.Squaremeal._store_token")
    @mock.patch("app.agents.squaremeal.Squaremeal.token_store.get", return_value="fake-123")
    @mock.patch("app.agents.squaremeal.Squaremeal._refresh_token", return_value="fake-123")
    def test_open_auth(self, mock_refresh_token, mock_token_store, mock_store_token):
        self.squaremeal.config.security_credentials["outbound"]["service"] = Configuration.OPEN_AUTH_SECURITY

        self.squaremeal.authenticate()
        self.assertEqual(0, mock_refresh_token.call_count)
        self.assertEqual(0, mock_token_store.call_count)
        self.assertEqual(0, mock_store_token.call_count)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal._get_balance")
    def test_transaction_history_success(self, mock_get_balance):
        self.squaremeal.user_info["credentials"]["merchant_identifier"] = "some_merchant_identifier"
        mock_get_balance.return_value = self.BALANCE_RESPONSE_200
        # balance needs to be called to retrieve the transaction data
        self.squaremeal.balance()

        transactions = self.squaremeal.transaction_history()

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].points, 100)
        self.assertEqual(transactions[0].description, "First Card Added")


class TestSquaremealLogin(TestCase):
    def create_app(self):
        return create_app(self)

    def setUp(self):
        self.security_credentials = SECURITY_CREDENTIALS
        self.credentials = CREDENTIALS

        with mock.patch("app.agents.squaremeal.Configuration") as mock_configuration:
            mock_config_object = MagicMock()
            mock_config_object.security_credentials = self.security_credentials
            mock_configuration.return_value = mock_config_object
            self.squaremeal = Squaremeal(
                retry_count=1,
                user_info={
                    "user_set": "27558",
                    "credentials": self.credentials,
                    "status": 442,
                    "journey_type": JourneyTypes.ADD,
                    "scheme_account_id": 94532,
                },
                scheme_slug="squaremeal",
            )
            self.squaremeal.base_url = "https://sm-uk.azure-api.net/bink-dev/api/v1/account/"
            self.squaremeal._login.retry.wait = wait_none()

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_200_response(self, mock_requests_session, mock_authenticate):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.squaremeal.base_url + "login",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(RESPONSE_JSON_200),
                    status=HTTPStatus.OK,
                )
            ],
        )

        resp_json = self.squaremeal._login(credentials=self.credentials)

        self.assertEqual(resp_json, RESPONSE_JSON_200)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.squaremeal.Squaremeal._login")
    def test_login_200(self, mock_login, mock_requests_session, mock_authenticate):
        mock_login.return_value = RESPONSE_JSON_200
        self.squaremeal.login(self.credentials)

        self.assertEqual(
            self.squaremeal.identifier, {"merchant_identifier": "some_user_id", "card_number": "123456789"}
        )

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_error_422(self, mock_requests_session, mock_authenticate):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.squaremeal.base_url + "login",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({"Message": "User is not found for that email address"}),
                    status=422,
                )
            ],
        )

        with self.assertRaises(AgentError) as e:
            self.squaremeal.login(self.credentials)

        self.assertEqual(e.exception.name, "Invalid credentials")
        self.assertEqual(e.exception.code, 403)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_error_401(self, mock_requests_session, mock_authenticate):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.squaremeal.base_url + "login",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({"statusCode": 401, "message": "Unauthorized. Access Denied by Gateway"}),
                    status=401,
                )
            ],
        )

        with self.assertRaises(AgentError) as e:
            self.squaremeal.login(self.credentials)

        self.assertEqual(e.exception.name, "Service connection error")
        self.assertEqual(e.exception.code, 537)

    @httpretty.activate
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_error_500(self, mock_requests_session, mock_authenticate):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.squaremeal.base_url + "login",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body="<html>\\n  <head>\\n    <title>Internal Server Error</title>\\n  </head>\\n  <body>\\n    "
                    "<h1><p>Internal Server Error</p></h1>\\n    \\n  </body>\\n</html>\\n",
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            ],
        )

        with self.assertRaises(AgentError):
            self.squaremeal.login(self.credentials)

        self.assertTrue("pAsSw0rD" not in str(mock_requests_session.call_args_list))
