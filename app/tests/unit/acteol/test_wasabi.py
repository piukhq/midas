import json
import string
import unittest
from http import HTTPStatus
from unittest.mock import patch
from urllib.parse import urljoin

import httpretty
import pytest
from app.agents.acteol import Wasabi
from app.agents.exceptions import STATUS_LOGIN_FAILED, AgentError, LoginError


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
        api_url = urljoin(self.wasabi.base_url, "api/Contact/PostContact")
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

    # TODO: mock _get_vouchers()
    @unittest.skip("skipped")
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
        expected_points = 7
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
            "card_number": "1048183413",
            "merchant_identifier": 142163,
        }

        # WHEN
        balance = self.wasabi.balance()

        # THEN
        assert balance == expected_balance

    def test_get_email_optin_pref_from_consent(self):
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
        rv: bool = self.wasabi._get_email_optin_pref_from_consent(consents=consents)

        # THEN
        assert rv

    def test_get_email_optin_pref_from_consent_is_false(self):
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
        rv: bool = self.wasabi._get_email_optin_pref_from_consent(consents=consents)

        # THEN
        assert not rv

    def test_get_email_optin_pref_from_consent_is_false_if_passed_empty(self):
        """
        Test finding no matching dict with a key of EmailOptin that also has key of "value" set to True,
        if passed a list with an empty dict
        """
        # GIVEN
        consents = [
            {},
        ]

        # WHEN
        rv: bool = self.wasabi._get_email_optin_pref_from_consent(consents=consents)

        # THEN
        assert not rv

    @httpretty.activate
    def test_set_optin_prefs_exception(self):
        """
        Test that an exception during setting prefs won't derail the join process
        """
        # GIVEN
        ctcid = "54321"
        email_optin_pref = True
        api_url = urljoin(self.wasabi.base_url, "api/CommunicationPreference/Post")
        httpretty.register_uri(
            httpretty.POST, api_url, status=HTTPStatus.GATEWAY_TIMEOUT,
        )

        # WHEN
        with pytest.raises(AgentError):
            self.wasabi._set_customer_preferences(
                ctcid=ctcid, email_optin_pref=email_optin_pref
            )

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._validate_member_number")
    def test_login_happy_path(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() does not raise exception on happy path
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

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
    def test_login_add_path(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() validates email on an add journey
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }
        self.wasabi.user_info["from_register"] = False

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
