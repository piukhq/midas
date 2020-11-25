import json
import string
import unittest
from decimal import Decimal
from http import HTTPStatus
from typing import Dict
from unittest.mock import patch
from urllib.parse import urljoin

import arrow
import httpretty
import pytest
from app.agents import schemas
from app.agents.acteol import Wasabi
from app.agents.exceptions import STATUS_LOGIN_FAILED, AgentError, LoginError
from app.vouchers import VoucherState, VoucherType, voucher_state_names
from tenacity import Retrying, stop_after_attempt
from settings import HERMES_URL


class TestWasabi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with unittest.mock.patch("app.agents.acteol.Configuration"):
            cls.mock_token = {
                "acteol_access_token": "abcde12345fghij",
                "timestamp": 123456789,
            }

            MOCK_AGENT_CLASS_ARGUMENTS = [
                1,
                {
                    "scheme_account_id": 1,
                    "status": 1,
                    "user_set": "1,2",
                    "journey_type": None,
                    "credentials": {},
                    "channel": "com.bink.wallet",
                },
            ]
            cls.wasabi = Wasabi(*MOCK_AGENT_CLASS_ARGUMENTS, scheme_slug="wasabi-club")
            cls.wasabi.base_url = "https://wasabiuat.wasabiworld.co.uk/"

    @patch("app.agents.acteol.Acteol._token_is_valid")
    @patch("app.agents.acteol.Acteol._refresh_access_token")
    @patch("app.agents.acteol.Acteol._store_token")
    def test_refreshes_token(
        self, mock_store_token, mock_refresh_access_token, mock_token_is_valid,
    ):
        """
        The token is invalid and should be refreshed.
        """
        # GIVEN
        mock_token_is_valid.return_value = False

        # WHEN
        with unittest.mock.patch.object(
            self.wasabi.token_store, "get", return_value=json.dumps(self.mock_token)
        ):
            self.wasabi.authenticate()

            # THEN
            assert mock_refresh_access_token.called_once()
            assert mock_store_token.called_once_with(self.mock_token)

    @patch("app.agents.acteol.Acteol._token_is_valid")
    @patch("app.agents.acteol.Acteol._refresh_access_token")
    @patch("app.agents.acteol.Acteol._store_token")
    def test_does_not_refresh_token(
        self, mock_store_token, mock_refresh_access_token, mock_token_is_valid
    ):
        """
        The token is valid and should not be refreshed.
        """
        # GIVEN
        mock_token_is_valid.return_value = True

        # WHEN
        with unittest.mock.patch.object(
            self.wasabi.token_store, "get", return_value=json.dumps(self.mock_token)
        ):
            token = self.wasabi.authenticate()

            # THEN
            assert not mock_refresh_access_token.called
            assert not mock_store_token.called
            assert token == self.mock_token

    def test_token_is_valid_false_for_just_expired(self):
        """
        Test that _token_is_valid() returns false when we have exactly reached the expiry
        """

        # GIVEN
        mock_current_timestamp = 75700
        mock_auth_token_timeout = 75600  # 21 hours, our cutoff point, is 75600 seconds
        self.wasabi.AUTH_TOKEN_TIMEOUT = mock_auth_token_timeout
        mock_token = {
            "acteol_access_token": "abcde12345fghij",
            "timestamp": 100,  # an easy number to work with to get 75600
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(
            token=mock_token, current_timestamp=mock_current_timestamp
        )

        # THEN
        assert is_valid is False

    def test_token_is_valid_false_for_expired(self):
        """
        Test that _token_is_valid() returns false when we have a token past its expiry
        """

        # GIVEN
        mock_current_timestamp = 10000
        mock_auth_token_timeout = 1  # Expire tokens after 1 second
        self.wasabi.AUTH_TOKEN_TIMEOUT = mock_auth_token_timeout
        mock_token = {
            "acteol_access_token": "abcde12345fghij",
            "timestamp": 10,  # an easy number to work with to exceed the timout setting
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(
            token=mock_token, current_timestamp=mock_current_timestamp
        )

        # THEN
        assert is_valid is False

    def test_token_is_valid_true_for_valid(self):
        """
        Test that _token_is_valid() returns true when the token is well within validity
        """

        # GIVEN
        mock_current_timestamp = 1000
        mock_auth_token_timeout = 900  # Expire tokens after 15 minutes
        self.wasabi.AUTH_TOKEN_TIMEOUT = mock_auth_token_timeout
        mock_token = {
            "acteol_access_token": "abcde12345fghij",
            "timestamp": 450,  # an easy number to work with to stay within validity range
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(
            token=mock_token, current_timestamp=mock_current_timestamp
        )

        # THEN
        assert is_valid is True

    def test_store_token(self):
        """
        Test that _store_token() calls the token store set method and returns an expected dict
        """
        # GIVEN
        mock_acteol_access_token = "abcde12345fghij"
        mock_current_timestamp = 123456789
        expected_token = {
            "acteol_access_token": mock_acteol_access_token,
            "timestamp": mock_current_timestamp,
        }

        # WHEN
        with unittest.mock.patch.object(
            self.wasabi.token_store, "set", return_value=True
        ):
            token = self.wasabi._store_token(
                acteol_access_token=mock_acteol_access_token,
                current_timestamp=mock_current_timestamp,
            )

            # THEN
            assert self.wasabi.token_store.set.called_once_with(
                self.wasabi.scheme_id, json.dumps(expected_token)
            )
            assert token == expected_token

    def test_make_headers(self):
        """
        Test that _make_headers returns a valid HTTP request authorization header
        """
        # GIVEN
        mock_acteol_access_token = "abcde12345fghij"
        expected_header = {"Authorization": f"Bearer {mock_acteol_access_token}"}

        # WHEN
        header = self.wasabi._make_headers(token=mock_acteol_access_token)

        # THEN
        assert header == expected_header

    def test_create_origin_id(self):
        """
        Test that _create_origin_id returns a hex string
        """
        # GIVEN
        user_email = "testperson@bink.com"
        origin_root = "Bink-Wasabi"

        # WHEN
        origin_id = self.wasabi._create_origin_id(
            user_email=user_email, origin_root=origin_root
        )

        # THEN
        assert all(c in string.hexdigits for c in origin_id)

    @httpretty.activate
    def test_account_already_exists(self):
        """
        Check if account already exists in Acteol
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(
            self.wasabi.base_url, f"api/Contact/FindByOriginID?OriginID={origin_id}"
        )
        httpretty.register_uri(
            httpretty.GET, api_url, status=HTTPStatus.OK,
        )

        # WHEN
        account_already_exists = self.wasabi._account_already_exists(
            origin_id=origin_id
        )

        # THEN
        assert account_already_exists
        querystring = httpretty.last_request().querystring
        assert querystring["OriginID"][0] == origin_id

    @httpretty.activate
    def test_account_already_exists_timeout(self):
        """
        Check if account already exists in Acteol, API request times out
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(
            self.wasabi.base_url, f"api/Contact/FindByOriginID?OriginID={origin_id}"
        )
        httpretty.register_uri(
            httpretty.GET, api_url, status=HTTPStatus.GATEWAY_TIMEOUT,
        )
        # Force fast-as-possible retries so we don't have slow running tests
        self.wasabi._account_already_exists.retry.sleep = unittest.mock.Mock()

        # WHEN
        with pytest.raises(AgentError):
            self.wasabi._account_already_exists(origin_id=origin_id)

    @httpretty.activate
    def test_account_does_not_exist(self):
        """
        Check for account not existing: an empty but OK response
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(
            self.wasabi.base_url, f"api/Contact/FindByOriginID?OriginID={origin_id}"
        )
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body="[]")],
            status=HTTPStatus.OK,
        )

        # WHEN
        account_already_exists = self.wasabi._account_already_exists(
            origin_id=origin_id
        )

        # THEN
        assert not account_already_exists

    @httpretty.activate
    def test_create_account(self):
        """
        Test creating an account
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, "api/Contact/PostContact")
        expected_ctcid = "54321"
        httpretty.register_uri(
            httpretty.POST,
            api_url,
            responses=[httpretty.Response(body=json.dumps({"CtcID": expected_ctcid}))],
            status=HTTPStatus.OK,
        )
        credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
        }

        # WHEN
        ctcid = self.wasabi._create_account(
            origin_id=origin_id, credentials=credentials
        )

        # THEN
        assert ctcid == expected_ctcid

    @httpretty.activate
    def test_create_account_raises(self):
        """
        Test creating an account raises an exception from base class's make_request()
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, "api/Contact/PostContact")
        httpretty.register_uri(httpretty.POST, api_url, status=HTTPStatus.BAD_REQUEST)
        credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
        }
        # Force fast-as-possible retries so we don't have slow running tests
        self.wasabi._create_account.retry.sleep = unittest.mock.Mock()

        # WHEN
        with pytest.raises(AgentError):
            self.wasabi._create_account(origin_id=origin_id, credentials=credentials)

    @httpretty.activate
    def test_add_member_number(self):
        """
        Test adding member number to Acteol
        """
        # GIVEN
        ctcid = "54321"
        expected_member_number = "987654321"
        api_url = urljoin(
            self.wasabi.base_url, f"api/Contact/AddMemberNumber?CtcID={ctcid}"
        )
        response_data = {
            "Response": True,
            "MemberNumber": expected_member_number,
            "Error": "",
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )

        # WHEN
        member_number = self.wasabi._add_member_number(ctcid=ctcid)

        # THEN
        assert member_number == expected_member_number

    @httpretty.activate
    def test_get_customer_details(self):
        """
        Test getting the customer details from Acteol
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(
            self.wasabi.base_url,
            (
                "api/Loyalty/GetCustomerDetailsByExternalCustomerID"
                f"?externalcustomerid={origin_id}&partnerid=BinkPlatform"
            ),
        )

        expected_email = "doesnotexist@bink.com"
        expected_customer_id = 142163
        expected_current_member_number = "1048183413"
        customer_details = {
            "Firstname": "David",
            "Lastname": "Testperson",
            "BirthDate": "1999-01-01T00:00:00",
            "Email": expected_email,
            "MobilePhone": None,
            "Address1": None,
            "Address2": None,
            "PostCode": None,
            "City": None,
            "CountryCode": None,
            "LastVisiteDate": None,
            "LoyaltyPointsBalance": 0,
            "LoyaltyCashBalance": 0.0,
            "CustomerID": expected_customer_id,
            "LoyaltyCardNumber": None,
            "CurrentTiers": "",
            "NextTiers": "",
            "NextTiersAmountLeft": 0.0,
            "Property": None,
            "TiersExpirationDate": None,
            "PointsExpirationDate": None,
            "MemberNumbersList": ["1048183413"],
            "CurrentMemberNumber": expected_current_member_number,
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(customer_details))],
            status=HTTPStatus.OK,
        )

        # WHEN
        customer_details = self.wasabi._get_customer_details(origin_id=origin_id)

        # THEN
        assert customer_details["Email"] == expected_email
        assert customer_details["CustomerID"] == expected_customer_id
        assert customer_details["CurrentMemberNumber"] == expected_current_member_number

    def test_customer_fields_are_present(self):
        """
        test for required customer fields in dict
        """
        # GIVEN
        customer_details = {
            "Email": 1,
            "CurrentMemberNumber": 1,
            "CustomerID": 1,
            "AnExtraField": 1,
        }

        # WHEN
        customer_fields_are_present = self.wasabi._customer_fields_are_present(
            customer_details=customer_details
        )

        # THEN
        assert customer_fields_are_present

    def test_customer_fields_are_present_returns_false(self):
        """
        test for required customer fields in dict
        """
        # GIVEN
        customer_details = {"Email": 1, "CurrentMemberNumber": 1, "AnExtraField": 1}

        # WHEN
        customer_fields_are_present = self.wasabi._customer_fields_are_present(
            customer_details=customer_details
        )

        # THEN
        assert not customer_fields_are_present

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._get_vouchers")
    @patch("app.agents.acteol.Acteol._get_customer_details")
    @httpretty.activate
    def test_balance(
        self, mock_get_customer_details, mock_get_vouchers, mock_authenticate
    ):
        """
        Check that the call to balance() returns an expected dict
        """
        # GIVEN
        api_url = urljoin(HERMES_URL, "schemes/accounts/1/credentials")
        httpretty.register_uri(
            httpretty.PUT, api_url, status=HTTPStatus.OK,
        )

        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        mock_points = 7
        expected_points = 7
        # Assume we only have a single in-progress voucher
        mock_get_vouchers.return_value = []
        expected_balance = {
            "points": Decimal(expected_points),
            "value": Decimal(expected_points),
            "value_label": "",
            "vouchers": [
                {
                    "state": voucher_state_names[VoucherState.IN_PROGRESS],
                    "type": VoucherType.STAMPS.value,
                    "target_value": None,
                    "value": Decimal(expected_points),
                }
            ],
        }
        customer_details = {
            "Firstname": "David",
            "Lastname": "Testperson",
            "BirthDate": "1999-01-01T00:00:00",
            "Email": "doesnotexist@bink.com",
            "MobilePhone": None,
            "Address1": None,
            "Address2": None,
            "PostCode": None,
            "City": None,
            "CountryCode": None,
            "LastVisiteDate": None,
            "LoyaltyPointsBalance": mock_points,
            "LoyaltyCashBalance": 0.0,
            "CustomerID": 142163,
            "LoyaltyCardNumber": None,
            "CurrentTiers": "",
            "NextTiers": "",
            "NextTiersAmountLeft": 0.0,
            "Property": None,
            "TiersExpirationDate": None,
            "PointsExpirationDate": None,
            "MemberNumbersList": ["1048183413"],
            "CurrentMemberNumber": "1048183413",
        }
        mock_get_customer_details.return_value = customer_details
        self.wasabi.credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
            "card_number": "1048183413",
            "merchant_identifier": 142163,
        }

        # WHEN
        balance = self.wasabi.balance()

        # THEN
        assert balance == expected_balance
        assert schemas.balance(balance)

    def test_get_email_optin_from_consent(self):
        """
        Test finding the dict  with a key of EmailOptin that also has key of "value" set to True
        """
        # GIVEN
        consents = [
            {
                "id": 2585,
                "slug": "EmailOptin",
                "value": True,
                "created_on": "2020-07-13T13:26:53.809970+00:00",
                "journey_type": 0,
            },
            {
                "id": 2586,
                "slug": "EmailOptin",
                "value": False,
                "created_on": "2020-07-13T13:26:53.809970+00:00",
                "journey_type": 0,
            },
            {
                "id": 2588,
                "slug": "AnotherOption",
                "value": 15,
                "created_on": "2020-07-13T13:26:53.809970+00:00",
                "journey_type": 0,
            },
        ]

        # WHEN
        rv: Dict = self.wasabi._get_email_optin_from_consent(consents=consents)

        # THEN
        assert rv == consents[0]

    def test_get_email_optin_from_consent_is_false(self):
        """
        Test finding no matching dict with a key of EmailOptin that also has key of "value" set to True
        """
        # GIVEN
        consents = [
            {
                "id": 2586,
                "slug": "EmailOptin",
                "value": False,
                "created_on": "2020-07-13T13:26:53.809970+00:00",
                "journey_type": 0,
            },
            {
                "id": 2588,
                "slug": "AnotherOption",
                "value": 15,
                "created_on": "2020-07-13T13:26:53.809970+00:00",
                "journey_type": 0,
            },
        ]

        # WHEN
        rv: Dict = self.wasabi._get_email_optin_from_consent(consents=consents)

        # THEN
        assert not rv

    def test_get_email_optin_from_consent_is_false_if_passed_empty(self):
        """
        Test finding no matching dict with a key of EmailOptin that also has key of "value" set to True,
        if passed a list with an empty dict
        """
        # GIVEN
        consents = [
            {},
        ]

        # WHEN
        rv: Dict = self.wasabi._get_email_optin_from_consent(consents=consents)

        # THEN
        assert not rv

    @httpretty.activate
    @patch("app.tasks.resend_consents.ReTryTaskStore.set_task")
    @patch("app.tasks.resend_consents.try_hermes_confirm")
    def test_set_customer_preferences_happy_path(
        self, mock_try_hermes_confirm, mock_set_task
    ):
        """
        This is an integration test in that it will test through to send_consents(), which is mostly mocked.
        No resend to agent's API jobs should be put on the retry queue
        """
        # GIVEN
        mock_try_hermes_confirm.return_value = (True, "done")
        ctcid = "54321"
        email_optin = {
            "id": 2585,
            "slug": "EmailOptin",
            "value": True,
            "created_on": "2020-07-13T13:26:53.809970+00:00",
            "journey_type": 0,
        }
        api_url = urljoin(self.wasabi.base_url, "api/CommunicationPreference/Post")
        ok_response_body = {"Response": True, "Error": ""}
        httpretty.register_uri(
            httpretty.POST,
            api_url,
            responses=[httpretty.Response(body=json.dumps(ok_response_body))],
            status=HTTPStatus.OK,
        )

        # WHEN
        self.wasabi._set_customer_preferences(ctcid=ctcid, email_optin=email_optin)

        # THEN
        assert not mock_set_task.called

    @httpretty.activate
    @patch("app.tasks.resend_consents.ReTryTaskStore.set_task")
    def test_set_customer_preferences_unhappy_path(self, mock_set_task):
        """
        This is more of an integration test, in that it will test through to send_consents(), which is mostly mocked.
        Failed calls to the agent's API should result in a job being put on a retry queue
        """
        # GIVEN
        ctcid = "54321"
        email_optin = {
            "id": 2585,
            "slug": "EmailOptin",
            "value": True,
            "created_on": "2020-07-13T13:26:53.809970+00:00",
            "journey_type": 0,
        }
        # Make sure we get a bad response from the agent's API
        api_url = urljoin(self.wasabi.base_url, "api/CommunicationPreference/Post")
        ok_response_body = {
            "Response": False,
            "Error": "Bad things, flee for the hills",
        }
        httpretty.register_uri(
            httpretty.POST,
            api_url,
            responses=[httpretty.Response(body=json.dumps(ok_response_body))],
            status=HTTPStatus.OK,
        )

        # WHEN
        self.wasabi._set_customer_preferences(ctcid=ctcid, email_optin=email_optin)

        # THEN
        assert mock_set_task.called_once()

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._validate_member_number")
    def test_login_happy_path(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() does not raise exception on happy path
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        mock_validate_member_number.return_value = (None, None)

        credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # WHEN
        try:
            self.wasabi.login(credentials=credentials)
        except Exception as e:
            pytest.fail(f"test_login_happy_path failed: {str(e)}")

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch(
        "app.agents.acteol.Acteol._validate_member_number",
        side_effect=LoginError(STATUS_LOGIN_FAILED),
    )
    def test_login_fail(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() fails with the appropriate exception
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # THEN
        with pytest.raises(LoginError):
            self.wasabi.login(credentials=credentials)

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._validate_member_number")
    def test_login_join_path(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() avoids an email verification call to Acteol when on join journey
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }
        self.wasabi.user_info["from_register"] = True

        # WHEN
        self.wasabi.login(credentials=credentials)

        # THEN
        assert not mock_validate_member_number.called

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._validate_member_number")
    def test_login_balance_path(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() that happens during a balance request avoids an email verification call
        to Acteol
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
            "merchant_identifier": "54321",
        }

        # WHEN
        self.wasabi.login(credentials=credentials)

        # THEN
        assert not mock_validate_member_number.called

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._validate_member_number")
    def test_login_add_path(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() validates email on an add journey
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        mock_validate_member_number.return_value = (None, None)

        credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }
        # These two fields just won't be present in real requests, but set to false here deliberately so we have
        # greater transparency
        self.wasabi.user_info["from_register"] = False
        self.wasabi.user_info["merchant_identifier"] = False

        # WHEN
        self.wasabi.login(credentials=credentials)

        # THEN
        assert mock_validate_member_number.called_once()

    def test_filter_bink_vouchers(self):
        """
        Test filtering by voucher["CategoryName"] == "BINK"
        """
        # GIVEN
        vouchers = [
            {
                "VoucherID": 1,
                "OfferID": 1,
                "StartDate": "2020-07-22T16:44:39.8253129+01:00",
                "ExpiryDate": "2020-07-22T16:44:39.8253129+01:00",
                "Conditions": "sample string 1",
                "Message": "sample string 2",
                "CategoryID": 3,
                "CategoryName": "Not BINK",
                "SubCategoryName": "sample string 5",
                "Description": "sample string 6",
                "CtcID": 1,
                "CustomerName": "sample string 7",
                "Redeemed": True,
                "RedeemedBy": "sample string 8",
                "Location": "sample string 9",
                "RedemptionDate": "2020-07-22T16:44:39.8253129+01:00",
                "URD": "2020-07-22T16:44:39.8253129+01:00",
                "Disabled": True,
                "Notes": "sample string 11",
                "ReactivationComment": "sample string 12",
                "WeekDays": [
                    {
                        "Id": 1,
                        "Name": "sample string 2",
                        "IsSelected": True,
                        "Tags": {},
                    },
                    {
                        "Id": 1,
                        "Name": "sample string 2",
                        "IsSelected": True,
                        "Tags": {},
                    },
                ],
                "DayHours": [
                    {
                        "Id": 1,
                        "Name": "sample string 2",
                        "IsSelected": True,
                        "Tags": {},
                    },
                    {
                        "Id": 1,
                        "Name": "sample string 2",
                        "IsSelected": True,
                        "Tags": {},
                    },
                ],
                "RandomID": "sample string 13",
                "VoucherCode": "sample string 14",
                "SmallImage": "sample string 15",
                "MediumImage": "sample string 16",
                "LargeImage": "sample string 17",
                "VoucherTypeName": "sample string 18",
                "Value": 1.1,
                "Products": ["sample string 1", "sample string 2"],
                "DiscountType": "sample string 19",
                "DiscountAmount": 20.1,
                "DiscountPercentage": 21.1,
                "QualifiedBasketAmount": 22.1,
                "QualifiedBasketProducts": ["sample string 1", "sample string 2"],
                "ProductKey": "sample string 23",
                "Source": "sample string 24",
                "InterestNodeCode": 25,
                "ActiveOffer": True,
                "BrandID": 1,
            },
            {
                "VoucherID": 2,
                "OfferID": 2,
                "StartDate": "2020-07-22T16:44:39.8253129+01:00",
                "ExpiryDate": "2020-07-22T16:44:39.8253129+01:00",
                "Conditions": "sample string 1",
                "Message": "sample string 2",
                "CategoryID": 3,
                "CategoryName": "BINK",
                "SubCategoryName": "sample string 5",
                "Description": "sample string 6",
                "CtcID": 1,
                "CustomerName": "sample string 7",
                "Redeemed": True,
                "RedeemedBy": "sample string 8",
                "Location": "sample string 9",
                "RedemptionDate": "2020-07-22T16:44:39.8253129+01:00",
                "URD": "2020-07-22T16:44:39.8253129+01:00",
                "Disabled": True,
                "Notes": "sample string 11",
                "ReactivationComment": "sample string 12",
                "WeekDays": [
                    {
                        "Id": 1,
                        "Name": "sample string 2",
                        "IsSelected": True,
                        "Tags": {},
                    },
                    {
                        "Id": 1,
                        "Name": "sample string 2",
                        "IsSelected": True,
                        "Tags": {},
                    },
                ],
                "DayHours": [
                    {
                        "Id": 1,
                        "Name": "sample string 2",
                        "IsSelected": True,
                        "Tags": {},
                    },
                    {
                        "Id": 1,
                        "Name": "sample string 2",
                        "IsSelected": True,
                        "Tags": {},
                    },
                ],
                "RandomID": "sample string 13",
                "VoucherCode": "sample string 14",
                "SmallImage": "sample string 15",
                "MediumImage": "sample string 16",
                "LargeImage": "sample string 17",
                "VoucherTypeName": "sample string 18",
                "Value": 1.1,
                "Products": ["sample string 1", "sample string 2"],
                "DiscountType": "sample string 19",
                "DiscountAmount": 20.1,
                "DiscountPercentage": 21.1,
                "QualifiedBasketAmount": 22.1,
                "QualifiedBasketProducts": ["sample string 1", "sample string 2"],
                "ProductKey": "sample string 23",
                "Source": "sample string 24",
                "InterestNodeCode": 25,
                "ActiveOffer": True,
                "BrandID": 1,
            },
        ]

        # WHEN
        bink_only_vouchers = self.wasabi._filter_bink_vouchers(vouchers=vouchers)

        # THEN
        assert len(bink_only_vouchers) == 1

    def test_map_redeemed_voucher_to_bink_struct(self):
        # GIVEN
        voucher = {
            "VoucherID": 1,
            "OfferID": 1,
            "StartDate": "2020-07-22T16:44:39.8253129+01:00",
            "ExpiryDate": "2020-07-22T16:44:39.8253129+01:00",
            "Conditions": "sample string 1",
            "Message": "sample string 2",
            "CategoryID": 3,
            "CategoryName": "BINK",
            "SubCategoryName": "sample string 5",
            "Description": "sample string 6",
            "CtcID": 1,
            "CustomerName": "sample string 7",
            "Redeemed": True,
            "RedeemedBy": "sample string 8",
            "Location": "sample string 9",
            "RedemptionDate": "2020-07-22T16:44:39.8253129+01:00",
            "URD": "2020-07-22T16:44:39.8253129+01:00",
            "Disabled": False,
            "Notes": "sample string 11",
            "ReactivationComment": "sample string 12",
            "WeekDays": [],
            "DayHours": [],
            "RandomID": "sample string 13",
            "VoucherCode": "12KT026N",
            "SmallImage": "sample string 15",
            "MediumImage": "sample string 16",
            "LargeImage": "sample string 17",
            "VoucherTypeName": "sample string 18",
            "Value": 1.1,
            "Products": ["sample string 1", "sample string 2"],
            "DiscountType": "sample string 19",
            "DiscountAmount": 20.1,
            "DiscountPercentage": 21.1,
            "QualifiedBasketAmount": 22.1,
            "QualifiedBasketProducts": ["sample string 1", "sample string 2"],
            "ProductKey": "sample string 23",
            "Source": "sample string 24",
            "InterestNodeCode": 25,
            "ActiveOffer": True,
            "BrandID": 1,
        }

        expected_mapped_voucher = {
            "state": voucher_state_names[VoucherState.REDEEMED],
            "type": VoucherType.STAMPS.value,
            "code": voucher["VoucherCode"],
            "target_value": None,
            "value": None,
            "issue_date": 1595432679,  # voucher URD as timestamp
            "redeem_date": 1595432679,  # voucher RedemptionDate as timestamp
            "expiry_date": 1595432679,  # voucher ExpiryDate as timestamp
        }

        # WHEN
        mapped_voucher = self.wasabi._map_acteol_voucher_to_bink_struct(voucher=voucher)

        # THEN
        assert mapped_voucher == expected_mapped_voucher

    def test_map_cancelled_voucher_to_bink_struct(self):
        # GIVEN
        voucher = {
            "VoucherID": 1,
            "OfferID": 1,
            "StartDate": "2020-07-22T16:44:39.8253129+01:00",
            "ExpiryDate": "2020-07-22T16:44:39.8253129+01:00",
            "Conditions": "sample string 1",
            "Message": "sample string 2",
            "CategoryID": 3,
            "CategoryName": "BINK",
            "SubCategoryName": "sample string 5",
            "Description": "sample string 6",
            "CtcID": 1,
            "CustomerName": "sample string 7",
            "Redeemed": False,
            "RedeemedBy": "",
            "Location": "sample string 9",
            "RedemptionDate": None,
            "URD": "2020-07-22T16:44:39.8253129+01:00",
            "Disabled": True,
            "Notes": "sample string 11",
            "ReactivationComment": "sample string 12",
            "WeekDays": [],
            "DayHours": [],
            "RandomID": "sample string 13",
            "VoucherCode": "12KT026N",
            "SmallImage": "sample string 15",
            "MediumImage": "sample string 16",
            "LargeImage": "sample string 17",
            "VoucherTypeName": "sample string 18",
            "Value": 1.1,
            "Products": ["sample string 1", "sample string 2"],
            "DiscountType": "sample string 19",
            "DiscountAmount": 20.1,
            "DiscountPercentage": 21.1,
            "QualifiedBasketAmount": 22.1,
            "QualifiedBasketProducts": ["sample string 1", "sample string 2"],
            "ProductKey": "sample string 23",
            "Source": "sample string 24",
            "InterestNodeCode": 25,
            "ActiveOffer": True,
            "BrandID": 1,
        }

        expected_mapped_voucher = {
            "state": voucher_state_names[VoucherState.CANCELLED],
            "type": VoucherType.STAMPS.value,
            "code": voucher["VoucherCode"],
            "target_value": None,
            "value": None,
            "issue_date": 1595432679,  # voucher URD as timestamp
            "expiry_date": 1595432679,  # voucher ExpiryDate as timestamp
        }

        # WHEN
        mapped_voucher = self.wasabi._map_acteol_voucher_to_bink_struct(voucher=voucher)

        # THEN
        assert mapped_voucher == expected_mapped_voucher

    def test_map_issued_voucher_to_bink_struct(self):
        """
        # Test for issued voucher. Conditions are:
        # vouchers.state = GetAllByCustomerID.voucher.ExpiryDate >= CurrentDate
        # && GetAllByCustomerID.voucher.Redeemed = false
        # && GetAllByCustomerID.voucher.Disabled = false
        """
        # GIVEN
        now = arrow.now()
        one_month_from_now = arrow.now().shift(months=1)
        one_month_from_now_timestamp = one_month_from_now.timestamp

        voucher = {
            "VoucherID": 1,
            "OfferID": 1,
            "StartDate": "2020-07-22T16:44:39.8253129+01:00",
            "ExpiryDate": str(one_month_from_now),
            "Conditions": "sample string 1",
            "Message": "sample string 2",
            "CategoryID": 3,
            "CategoryName": "BINK",
            "SubCategoryName": "sample string 5",
            "Description": "sample string 6",
            "CtcID": 1,
            "CustomerName": "sample string 7",
            "Redeemed": False,
            "RedeemedBy": "sample string 8",
            "Location": "sample string 9",
            "RedemptionDate": "2020-07-22T16:44:39.8253129+01:00",
            "URD": str(now),
            "Disabled": False,
            "Notes": "sample string 11",
            "ReactivationComment": "sample string 12",
            "WeekDays": [],
            "DayHours": [],
            "RandomID": "sample string 13",
            "VoucherCode": "12KT026N",
            "SmallImage": "sample string 15",
            "MediumImage": "sample string 16",
            "LargeImage": "sample string 17",
            "VoucherTypeName": "sample string 18",
            "Value": 1.1,
            "Products": ["sample string 1", "sample string 2"],
            "DiscountType": "sample string 19",
            "DiscountAmount": 20.1,
            "DiscountPercentage": 21.1,
            "QualifiedBasketAmount": 22.1,
            "QualifiedBasketProducts": ["sample string 1", "sample string 2"],
            "ProductKey": "sample string 23",
            "Source": "sample string 24",
            "InterestNodeCode": 25,
            "ActiveOffer": True,
            "BrandID": 1,
        }

        expected_mapped_voucher = {
            "state": voucher_state_names[VoucherState.ISSUED],
            "type": VoucherType.STAMPS.value,
            "code": voucher["VoucherCode"],
            "target_value": None,
            "value": None,
            "issue_date": now.timestamp,  # voucher URD as timestamp
            "expiry_date": one_month_from_now_timestamp,
        }

        # WHEN
        mapped_voucher = self.wasabi._map_acteol_voucher_to_bink_struct(voucher=voucher)

        # THEN
        assert mapped_voucher == expected_mapped_voucher

    def test_map_expired_voucher_to_bink_struct(self):
        """
        # Test for expired voucher. Conditions are:
        # vouchers.state = GetAllByCustomerID.voucher.ExpiryDate < CurrentDate
        """
        # GIVEN
        now = arrow.now()
        one_month_ago = arrow.now().shift(months=-1)
        one_month_ago_timestamp = one_month_ago.timestamp

        voucher = {
            "VoucherID": 1,
            "OfferID": 1,
            "StartDate": "2020-07-22T16:44:39.8253129+01:00",
            "ExpiryDate": str(one_month_ago),
            "Conditions": "sample string 1",
            "Message": "sample string 2",
            "CategoryID": 3,
            "CategoryName": "BINK",
            "SubCategoryName": "sample string 5",
            "Description": "sample string 6",
            "CtcID": 1,
            "CustomerName": "sample string 7",
            "Redeemed": False,
            "RedeemedBy": "sample string 8",
            "Location": "sample string 9",
            "RedemptionDate": "2020-07-22T16:44:39.8253129+01:00",
            "URD": str(now),
            "Disabled": False,
            "Notes": "sample string 11",
            "ReactivationComment": "sample string 12",
            "WeekDays": [],
            "DayHours": [],
            "RandomID": "sample string 13",
            "VoucherCode": "12KT026N",
            "SmallImage": "sample string 15",
            "MediumImage": "sample string 16",
            "LargeImage": "sample string 17",
            "VoucherTypeName": "sample string 18",
            "Value": 1.1,
            "Products": ["sample string 1", "sample string 2"],
            "DiscountType": "sample string 19",
            "DiscountAmount": 20.1,
            "DiscountPercentage": 21.1,
            "QualifiedBasketAmount": 22.1,
            "QualifiedBasketProducts": ["sample string 1", "sample string 2"],
            "ProductKey": "sample string 23",
            "Source": "sample string 24",
            "InterestNodeCode": 25,
            "ActiveOffer": True,
            "BrandID": 1,
        }

        expected_mapped_voucher = {
            "state": voucher_state_names[VoucherState.EXPIRED],
            "type": VoucherType.STAMPS.value,
            "code": voucher["VoucherCode"],
            "target_value": None,
            "value": None,
            "issue_date": now.timestamp,  # voucher URD as timestamp
            "expiry_date": one_month_ago_timestamp,
        }

        # WHEN
        mapped_voucher = self.wasabi._map_acteol_voucher_to_bink_struct(voucher=voucher)

        # THEN
        assert mapped_voucher == expected_mapped_voucher

    def test_make_in_progress_voucher(self):
        """
            Test making an in-progress voucher dict
            """
        # GIVEN
        points = Decimal(123)
        expected_in_progress_voucher = {
            "state": voucher_state_names[VoucherState.IN_PROGRESS],
            "type": VoucherType.STAMPS.value,
            "target_value": None,
            "value": points,
        }

        # WHEN
        in_progress_voucher = self.wasabi._make_in_progress_voucher(
            points=points, voucher_type=VoucherType.STAMPS
        )

        # THEN
        assert in_progress_voucher == expected_in_progress_voucher

        return in_progress_voucher

    @httpretty.activate
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_scrape_transactions(self, mock_authenticate):
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        ctcid = 666999
        n_records = 5
        api_url = urljoin(
            self.wasabi.base_url,
            f"api/Order/Get?CtcID={ctcid}&LastRecordsCount={n_records}&IncludeOrderDetails=false",
        )
        mock_transactions = [
            {
                "CustomerID": ctcid,
                "OrderID": 18355,
                "LocationID": "66",
                "LocationName": "Kimchee Pancras Square",
                "OrderDate": "2020-06-17T10:56:38.36",
                "OrderItems": None,
                "TotalCostExclTax": 0.0,
                "TotalCost": 72.5,
                "PointEarned": 1.0,
                "AmountEarned": 0.0,
                "SourceID": None,
                "VATNumber": "198",
                "UsedToEarnPoint": False,
            },
            {
                "CustomerID": ctcid,
                "OrderID": 18631,
                "LocationID": "66",
                "LocationName": "Kimchee Pancras Square",
                "OrderDate": "2020-06-17T10:56:38.36",
                "OrderItems": None,
                "TotalCostExclTax": 0.0,
                "TotalCost": 0.0,
                "PointEarned": 1.0,
                "AmountEarned": 0.0,
                "SourceID": None,
                "VATNumber": "513",
                "UsedToEarnPoint": False,
            },
        ]
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(mock_transactions))],
            status=HTTPStatus.OK,
        )
        self.wasabi.credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
            "card_number": "1048183413",
            "merchant_identifier": ctcid,
        }

        # WHEN
        transactions = self.wasabi.scrape_transactions()

        # THEN
        assert transactions == mock_transactions

    def test_format_money_value(self):
        # GIVEN
        money_value1 = 6.1
        money_value2 = 06.1
        money_value3 = 600.1
        money_value4 = 6000.100

        # WHEN
        formatted_money_value1 = self.wasabi._format_money_value(
            money_value=money_value1
        )
        formatted_money_value2 = self.wasabi._format_money_value(
            money_value=money_value2
        )
        formatted_money_value3 = self.wasabi._format_money_value(
            money_value=money_value3
        )
        formatted_money_value4 = self.wasabi._format_money_value(
            money_value=money_value4
        )

        # THEN
        assert formatted_money_value1 == "6.10"
        assert formatted_money_value2 == "6.10"
        assert formatted_money_value3 == "600.10"
        assert formatted_money_value4 == "6000.10"

    def test_decimalise_to_two_places(self):
        # GIVEN
        value1 = 6.1
        value2 = 06.1
        value3 = 600.1
        value4 = 6000.100
        value5 = 6

        # WHEN
        decimalised1 = self.wasabi._decimalise_to_two_places(value=value1)
        decimalised2 = self.wasabi._decimalise_to_two_places(value=value2)
        decimalised3 = self.wasabi._decimalise_to_two_places(value=value3)
        decimalised4 = self.wasabi._decimalise_to_two_places(value=value4)
        decimalised5 = self.wasabi._decimalise_to_two_places(value=value5)

        # THEN
        assert decimalised1 == Decimal("6.10")
        assert decimalised2 == Decimal("6.10")
        assert decimalised3 == Decimal("600.10")
        assert decimalised4 == Decimal("6000.10")
        assert decimalised5 == Decimal("6.00")

    def test_parse_transaction(self):
        # GIVEN
        ctcid = 666999
        location_name = "Kimchee Pancras Square"
        expected_points = self.wasabi._decimalise_to_two_places(7.1)
        total_cost = 6.1
        transaction = {
            "CustomerID": ctcid,
            "OrderID": 2,
            "LocationID": "66",
            "LocationName": location_name,
            "OrderDate": "2020-07-28T17:55:35.6644044+01:00",
            "OrderItems": [
                {
                    "ItemID": 1,
                    "Name": "sample string 2",
                    "ProductCode": "sample string 3",
                    "Quantity": 4,
                    "UnitPrice": 5.1,
                    "DiscountAmount": 6.1,
                    "TotalAmountExclTax": 7.1,
                    "TotalAmount": 8.1,
                    "CustomerID": 9,
                },
                {
                    "ItemID": 1,
                    "Name": "sample string 2",
                    "ProductCode": "sample string 3",
                    "Quantity": 4,
                    "UnitPrice": 5.1,
                    "DiscountAmount": 6.1,
                    "TotalAmountExclTax": 7.1,
                    "TotalAmount": 8.1,
                    "CustomerID": 9,
                },
            ],
            "TotalCostExclTax": 5.1,
            "TotalCost": total_cost,
            "PointEarned": 7.1,
            "AmountEarned": 8.1,
            "SourceID": "sample string 9",
            "VATNumber": "sample string 10",
            "UsedToEarnPoint": True,
        }

        # WHEN
        parsed_transaction = self.wasabi.parse_transaction(transaction=transaction)
        # AND
        formatted_total_cost = self.wasabi._format_money_value(money_value=total_cost)
        description = self.wasabi._make_transaction_description(
            location_name=location_name, formatted_total_cost=formatted_total_cost,
        )

        # THEN
        assert isinstance(parsed_transaction["date"], int)  # Is a timestamp
        assert parsed_transaction["description"] == description
        assert parsed_transaction["location"] == location_name
        assert isinstance(parsed_transaction["points"], Decimal)
        assert parsed_transaction["points"] == expected_points

    def test_check_internal_error(self):
        """
        Test handling 'Internal Exception error'
        """
        # GIVEN
        resp_json = {"Response": False, "Error": "Internal Exception"}

        # WHEN
        with pytest.raises(AgentError):
            self.wasabi._check_internal_error(resp_json)

    def test_check_deleted_user(self):
        """
        Test handling 'Deleted User error'
        """
        # GIVEN
        resp_json = {"CustomerID": "0", "CurrentMemberNumber": "ABC123"}

        # WHEN
        with pytest.raises(AgentError):
            self.wasabi._check_deleted_user(resp_json)

    @httpretty.activate
    @patch("app.agents.acteol.Retrying")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_timeout(self, mock_authenticate, mock_retrying):
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        # Force fast-as-possible retries so we don't have slow running tests
        retrying = Retrying(stop=stop_after_attempt(1), reraise=True)
        mock_retrying.return_value = retrying

        api_url = urljoin(
            self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber"
        )
        httpretty.register_uri(
            httpretty.GET, api_url, status=HTTPStatus.GATEWAY_TIMEOUT,
        )
        credentials = {
            "email": "testastic@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # THEN
        with pytest.raises(AgentError):
            self.wasabi._validate_member_number(credentials)

    @httpretty.activate
    @patch("app.agents.acteol.Retrying")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_fail_authentication(
        self, mock_authenticate, mock_retrying
    ):
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        # Force fast-as-possible retries so we don't have slow running tests
        retrying = Retrying(stop=stop_after_attempt(1), reraise=True)
        mock_retrying.return_value = retrying

        api_url = urljoin(
            self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber"
        )
        httpretty.register_uri(
            httpretty.GET, api_url, status=HTTPStatus.UNAUTHORIZED,
        )
        credentials = {
            "email": "testastic@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # THEN
        with pytest.raises(AgentError):
            self.wasabi._validate_member_number(credentials)

    @httpretty.activate
    @patch("app.agents.acteol.Retrying")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_fail_forbidden(
        self, mock_authenticate, mock_retrying
    ):
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        # Force fast-as-possible retries so we don't have slow running tests
        retrying = Retrying(stop=stop_after_attempt(1), reraise=True)
        mock_retrying.return_value = retrying

        api_url = urljoin(
            self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber"
        )
        httpretty.register_uri(
            httpretty.GET, api_url, status=HTTPStatus.FORBIDDEN,
        )
        credentials = {
            "email": "testastic@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # THEN
        with pytest.raises(AgentError):
            self.wasabi._validate_member_number(credentials)

    @httpretty.activate
    @patch("app.agents.acteol.Retrying")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_validation_error(
        self, mock_authenticate, mock_retrying
    ):
        """
        Test one of the LoginError scenarios
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        # Force fast-as-possible retries so we don't have slow running tests
        retrying = Retrying(stop=stop_after_attempt(1), reraise=True)
        mock_retrying.return_value = retrying

        api_url = urljoin(
            self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber"
        )
        response_data = {
            "ValidationMsg": "Invalid Email",
            "IsValid": False,
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )
        credentials = {
            "email": "testastic@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # THEN
        with pytest.raises(LoginError):
            self.wasabi._validate_member_number(credentials)

    @httpretty.activate
    @patch("app.agents.acteol.Retrying")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_succeeds(self, mock_authenticate, mock_retrying):
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        # Force fast-as-possible retries so we don't have slow running tests
        retrying = Retrying(stop=stop_after_attempt(1), reraise=True)
        mock_retrying.return_value = retrying

        api_url = urljoin(
            self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber"
        )
        ctcid = 54321
        response_data = {"ValidationMsg": "", "IsValid": True, "CtcID": ctcid}
        expected_ctcid = str(ctcid)
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )
        credentials = {
            "email": "testastic@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # WHEN
        ctcid = self.wasabi._validate_member_number(credentials)

        # THEN
        assert ctcid == expected_ctcid
