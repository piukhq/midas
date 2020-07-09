import json
import string
import unittest
from http import HTTPStatus
from unittest.mock import patch

import httpretty
import pytest
from app.agents.acteol import Wasabi
from app.agents.exceptions import AgentError


class TestWasabi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with unittest.mock.patch("app.agents.acteol.Configuration"):
            cls.mock_token = {
                "token": "abcde12345fghij",
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
                },
            ]
            cls.wasabi = Wasabi(*MOCK_AGENT_CLASS_ARGUMENTS, scheme_slug="wasabi-club")

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
            "token": "abcde12345fghij",
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
            "token": "abcde12345fghij",
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
            "token": "abcde12345fghij",
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
            "token": mock_acteol_access_token,
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
        api_url = (
            f"{self.wasabi.BASE_API_URL}/Contact/FindByOriginID?OriginID={origin_id}"
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
        api_url = (
            f"{self.wasabi.BASE_API_URL}/Contact/FindByOriginID?OriginID={origin_id}"
        )
        httpretty.register_uri(
            httpretty.GET, api_url, status=HTTPStatus.GATEWAY_TIMEOUT,
        )

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
        api_url = (
            f"{self.wasabi.BASE_API_URL}/Contact/FindByOriginID?OriginID={origin_id}"
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
        api_url = f"{self.wasabi.BASE_API_URL}/Contact/PostContact"
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
            "phone": "08765543210",
            "postcode": "BN77UU",
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
        api_url = f"{self.wasabi.BASE_API_URL}/Contact/PostContact"
        httpretty.register_uri(httpretty.POST, api_url, status=HTTPStatus.BAD_REQUEST)
        credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "phone": "08765543210",
            "postcode": "BN77UU",
        }

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
        api_url = f"{self.wasabi.BASE_API_URL}/Contact/AddMemberNumber?CtcID={ctcid}"
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
        api_url = (
            f"{self.wasabi.BASE_API_URL}/Loyalty/GetCustomerDetailsByExternalCustomerID"
            f"?externalcustomerid={origin_id}&partnerid=BinkPlatform"
        )
        expected_email = "doesnotexist@bink.com"
        expected_customer_id = 142163
        expected_current_member_number = "1048183413"
        customer_details = {
            "Firstname": "David",
            "Lastname": "Testperson",
            "BirthDate": None,
            "Email": expected_email,
            "MobilePhone": None,
            "Address1": None,
            "Address2": None,
            "PostCode": "BN7 7UU",
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
    @patch("app.agents.acteol.Acteol._get_customer_details")
    def test_balance(self, mock_get_customer_details, mock_authenticate):
        """
        Check that the call to balance() returns an expected dict
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        mock_points = 7
        expected_points = "7/7"
        expected_balance = {
            "points": expected_points,
            "value": expected_points,
            "value_label": "",
        }
        customer_details = {
            "Firstname": "David",
            "Lastname": "Testperson",
            "BirthDate": None,
            "Email": "doesnotexist@bink.com",
            "MobilePhone": None,
            "Address1": None,
            "Address2": None,
            "PostCode": "BN7 7UU",
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
            "phone": "08765543210",
            "postcode": "BN77UU",
        }

        # WHEN
        balance = self.wasabi.balance()

        # THEN
        assert balance == expected_balance
