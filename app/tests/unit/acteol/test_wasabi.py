import json
import string
import unittest
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import MagicMock, Mock, call, patch
from urllib.parse import urljoin

import arrow
import httpretty
import pytest
from soteria.configuration import Configuration

import settings
from app.agents.acteol import Wasabi
from app.agents.schemas import Balance, Transaction, Voucher
from app.exceptions import (
    AccountAlreadyExistsError,
    EndSiteDownError,
    IPBlockedError,
    JoinError,
    NoSuchRecordError,
    RetryLimitReachedError,
    StatusLoginFailedError,
    ValidationError,
)
from app.scheme_account import JourneyTypes
from app.vouchers import VoucherState, voucher_state_names
from settings import HERMES_URL


class TestWasabi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mock_config = MagicMock()
        mock_config.merchant_url = "https://wasabiuat.test.wasabiworld.co.uk/"
        mock_config.security_credentials = {
            "outbound": {
                "service": Configuration.OAUTH_SECURITY,
                "credentials": [
                    {
                        "credential_type": "compound_key",
                        "storage_key": "a_storage_key",
                        "value": {"password": "paSSword", "username": "username@bink.com"},
                    }
                ],
            },
        }
        cls.mock_token = {
            "wasabi_club_access_token": "abcde12345fghij",
            "timestamp": 123456789,
        }

        MOCK_AGENT_CLASS_ARGUMENTS = [
            1,
            {
                "scheme_account_id": 1,
                "status": 1,
                "user_set": "1,2",
                "bink_user_id": 1,
                "journey_type": JourneyTypes.JOIN.value,
                "credentials": {},
                "channel": "com.bink.wallet",
            },
        ]

        with patch("app.agents.base.Configuration", return_value=mock_config):
            cls.wasabi = Wasabi(*MOCK_AGENT_CLASS_ARGUMENTS, scheme_slug="wasabi-club")
            cls.wasabi.integration_service = "SYNC"

        cls.wasabi.max_retries = 0

    def test_get_oauth_url_and_payload(self):
        url, payload = self.wasabi.get_auth_url_and_payload()
        self.assertEqual("https://wasabiuat.test.wasabiworld.co.uk/token", url)
        self.assertEqual(
            {"grant_type": "password", "password": "paSSword", "username": "username@bink.com"},
            payload,
        )

    # @patch("app.agents.acteol.Acteol._token_is_valid")
    # @patch("app.agents.acteol.Acteol._refresh_token")
    # @patch("app.agents.acteol.Acteol._store_token")
    # def test_refreshes_token(
    #     self,
    #     mock_store_token,
    #     mock_refresh_token,
    #     mock_token_is_valid,
    # ):
    #     """
    #     The token is invalid and should be refreshed.
    #     """
    #     # GIVEN
    #     mock_token_is_valid.return_value = False

    #     # WHEN
    #     with patch.object(self.wasabi.token_store, "get", return_value=json.dumps(self.mock_token)):
    #         self.wasabi.authenticate()

    #         # THEN
    #         mock_refresh_token.assert_called_once()
    #         mock_store_token.assert_called_once_with(self.mock_token)

    @patch("app.agents.base.BaseAgent._token_is_valid")
    @patch("app.agents.base.BaseAgent._refresh_token")
    @patch("app.agents.base.BaseAgent._store_token")
    def test_does_not_refresh_token(self, mock_store_token, mock_refresh_token, mock_token_is_valid):
        """
        The token is valid and should not be refreshed.
        """
        # GIVEN
        self.wasabi.outbound_auth_service = Configuration.OAUTH_SECURITY
        mock_token_is_valid.return_value = True

        # WHEN
        with patch.object(self.wasabi.token_store, "get", return_value=json.dumps(self.mock_token)):
            self.wasabi.authenticate()

            # THEN
            assert not mock_refresh_token.called
            assert not mock_store_token.called
            self.assertEqual({"Authorization": "Bearer abcde12345fghij"}, self.wasabi.headers)

    def test_token_is_valid_false_for_just_expired(self):
        """
        Test that _token_is_valid() returns false when we have exactly reached the expiry
        """

        # GIVEN
        mock_current_timestamp = 75700
        mock_auth_token_timeout = 75600  # 21 hours, our cutoff point, is 75600 seconds
        self.wasabi.oauth_token_timeout = mock_auth_token_timeout
        mock_token = {
            "wasabi_club_access_token": "abcde12345fghij",
            "timestamp": 100,  # an easy number to work with to get 75600
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(
            token=mock_token,
            current_timestamp=mock_current_timestamp,
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
        self.wasabi.oauth_token_timeout = mock_auth_token_timeout
        mock_token = {
            "wasabi_club_access_token": "abcde12345fghij",
            "timestamp": 10,  # an easy number to work with to exceed the timout setting
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(
            token=mock_token,
            current_timestamp=mock_current_timestamp,
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
        self.wasabi.oauth_token_timeout = mock_auth_token_timeout
        mock_token = {
            "wasabi_club_access_token": "abcde12345fghij",
            "timestamp": 450,  # an easy number to work with to stay within validity range
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(token=mock_token, current_timestamp=mock_current_timestamp)

        # THEN
        assert is_valid is True

    # def test_store_token(self):
    #     """
    #     Test that _store_token() calls the token store set method and returns an expected dict
    #     """
    #     # GIVEN
    #     mock_wasabi_club_access_token = "abcde12345fghij"
    #     mock_current_timestamp = 123456789
    #     expected_token = {
    #         "wasabi_club_access_token": mock_wasabi_club_access_token,
    #         "timestamp": mock_current_timestamp,
    #     }

    #     # WHEN
    #     with patch.object(self.wasabi.token_store, "set", return_value=True):
    #         self.wasabi._store_token(
    #             token=mock_wasabi_club_access_token,
    #             current_timestamp=mock_current_timestamp,
    #         )

    #         # THEN
    #         self.wasabi.token_store.set.assert_called_once_with(self.wasabi.scheme_id, json.dumps(expected_token))

    def test_make_headers(self):
        """
        Test that _make_headers returns a valid HTTP request authorization header
        """
        # GIVEN
        mock_wasabi_club_access_token = "abcde12345fghij"
        expected_header = {"Authorization": f"Bearer {mock_wasabi_club_access_token}"}

        # WHEN
        header = self.wasabi._make_headers(token=mock_wasabi_club_access_token)

        # THEN
        assert header == expected_header

    @patch("app.agents.base.BaseAgent._oauth_authentication")
    def test_oauth(self, mock_oauth_authentication):
        self.wasabi.authenticate()
        self.assertEqual(1, mock_oauth_authentication.call_count)

    @patch("app.agents.base.BaseAgent._oauth_authentication")
    def test_open_auth(self, mock_oauth_authentication):
        self.wasabi.outbound_auth_service = Configuration.OPEN_AUTH_SECURITY
        self.wasabi.authenticate()
        self.assertEqual(0, mock_oauth_authentication.call_count)

    def test_create_origin_id(self):
        """
        Test that _create_origin_id returns a hex string
        """
        # GIVEN
        user_email = "testperson@bink.com"
        origin_root = "Bink-Wasabi"

        # WHEN
        origin_id = self.wasabi._create_origin_id(user_email=user_email, origin_root=origin_root)

        # THEN
        assert all(c in string.hexdigits for c in origin_id)

    @httpretty.activate
    def test_account_already_exists(self):
        """
        Check if account already exists in Acteol
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, f"api/Contact/FindByOriginID?OriginID={origin_id}")
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.OK,
        )

        # WHEN
        account_already_exists = self.wasabi._account_already_exists(origin_id=origin_id)

        # THEN
        assert account_already_exists
        # Need to get the first (API) request, not the later Prometheus requests
        querystring = httpretty.latest_requests()[0].querystring
        assert querystring["OriginID"][0] == origin_id

    @httpretty.activate
    def test_account_already_exists_timeout(self):
        """
        Check if account already exists in Acteol, API request times out
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, f"api/Contact/FindByOriginID?OriginID={origin_id}")
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.GATEWAY_TIMEOUT,
        )
        # Force fast-as-possible retries so we don't have slow running tests

        # WHEN
        with pytest.raises(RetryLimitReachedError):
            self.wasabi._account_already_exists(origin_id=origin_id)

    @httpretty.activate
    def test_account_does_not_exist(self):
        """
        Check for account not existing: an empty but OK response
        """
        # GIVEN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, f"api/Contact/FindByOriginID?OriginID={origin_id}")
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body="[]")],
            status=HTTPStatus.OK,
        )

        # WHEN
        account_already_exists = self.wasabi._account_already_exists(origin_id=origin_id)

        # THEN
        assert not account_already_exists

    @httpretty.activate
    @patch("app.agents.base.signal", autospec=True)
    def test_create_account(self, mock_base_signal):
        """
        Test creating an account
        """
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.JOIN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, "api/Contact/PostContact")
        expected_ctcid = "54321"
        httpretty.register_uri(
            httpretty.POST,
            api_url,
            responses=[httpretty.Response(body=json.dumps({"CtcID": expected_ctcid}))],
            status=HTTPStatus.OK,
        )
        # WHEN
        ctcid = self.wasabi._create_account(origin_id=origin_id)

        # THEN
        assert ctcid == expected_ctcid

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    def test_create_account_error(self, mock_send_to_atlas):
        """
        Test _check_response_for_error
        """
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.JOIN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, "api/Contact/PostContact")
        response_data = {
            "FirstName": "TestPerson3",
            "Email": "testperson@bink.com",
            "Error": "errortest122",
        }
        httpretty.register_uri(
            httpretty.POST,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )

        # WHEN
        with pytest.raises(EndSiteDownError):
            self.wasabi._create_account(origin_id=origin_id)

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    def test_create_account_raises(self, mock_send_to_atlas):
        """
        Test creating an account raises an exception from base class's make_request()
        """
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.JOIN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, "api/Contact/PostContact")
        httpretty.register_uri(httpretty.POST, api_url, status=HTTPStatus.BAD_REQUEST)

        # WHEN
        assert not mock_send_to_atlas.called
        with self.assertRaises(EndSiteDownError):
            self.wasabi._create_account(origin_id=origin_id)

    @httpretty.activate
    def test_create_account_ctcid_equals_zero(self):
        """
        Test creating an account with ctcid = 0 returned in response
        """
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.JOIN
        origin_id = "d232c52c8aea16e454061f2a05e63f60a92445c0"
        api_url = urljoin(self.wasabi.base_url, "api/Contact/PostContact")
        self.wasabi.credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
        }
        zero_ctcid = 0
        httpretty.register_uri(
            httpretty.POST,
            api_url,
            responses=[httpretty.Response(body=json.dumps({"CtcID": zero_ctcid}))],
            status=HTTPStatus.OK,
        )
        httpretty.register_uri(
            httpretty.POST,
            uri=f"{settings.ATLAS_URL}/audit/membership/",
            status=HTTPStatus.OK,
        )
        # WHEN
        with self.assertRaises(JoinError) as captured_exception:
            self.wasabi._create_account(origin_id=origin_id)

        assert captured_exception.exception.message == "Acteol returned a CTCID = 0 for loyalty account id: 1"

    @httpretty.activate
    @patch("app.agents.base.signal", autospec=True)
    def test_add_member_number(self, mock_base_signal):
        """
        Test adding member number to Acteol
        """
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.ADD
        ctcid = "54321"
        expected_member_number = "987654321"
        api_url = urljoin(self.wasabi.base_url, f"api/Contact/AddMemberNumber?CtcID={ctcid}")
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
    @patch("app.agents.base.signal", autospec=True)
    def test_add_member_number_error(self, mock_base_signal):
        """
        Test _check_response_for_error
        """
        # GIVEN
        ctcid = "54321"
        expected_member_number = "987654321"
        api_url = urljoin(self.wasabi.base_url, f"api/Contact/AddMemberNumber?CtcID={ctcid}")
        response_data = {
            "Response": True,
            "MemberNumber": expected_member_number,
            "Error": "errortest123",
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )
        self.wasabi.journey_type = JourneyTypes.ADD

        # WHEN
        with pytest.raises(EndSiteDownError):
            self.wasabi._add_member_number(ctcid=ctcid)

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

    @httpretty.activate
    def test_get_customer_details_error(self):
        """
        Test _check_response_for_error
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
            "Error": "errortest123",
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(customer_details))],
            status=HTTPStatus.OK,
        )

        # WHEN
        with pytest.raises(EndSiteDownError):
            self.wasabi._get_customer_details(origin_id=origin_id)

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
        customer_fields_are_present = self.wasabi._customer_fields_are_present(customer_details=customer_details)

        # THEN
        assert customer_fields_are_present

    def test_customer_fields_are_present_returns_false(self):
        """
        test for required customer fields in dict
        """
        # GIVEN
        customer_details = {"Email": 1, "CurrentMemberNumber": 1, "AnExtraField": 1}

        # WHEN
        customer_fields_are_present = self.wasabi._customer_fields_are_present(customer_details=customer_details)

        # THEN
        assert not customer_fields_are_present

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._get_vouchers")
    @patch("app.agents.acteol.Acteol._get_customer_details")
    @httpretty.activate
    def test_balance(self, mock_get_customer_details, mock_get_vouchers, mock_authenticate):
        """
        Check that the call to balance() returns an expected dict
        """
        # GIVEN
        api_url = urljoin(HERMES_URL, "schemes/accounts/1/credentials")
        httpretty.register_uri(
            httpretty.PUT,
            api_url,
            status=HTTPStatus.OK,
        )

        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        mock_points = 7
        expected_points = 7
        # Assume we only have a single in-progress voucher
        mock_get_vouchers.return_value = []
        expected_balance = Balance(
            points=Decimal(expected_points),
            value=Decimal(expected_points),
            value_label="",
            vouchers=[
                Voucher(
                    state=voucher_state_names[VoucherState.IN_PROGRESS],
                    target_value=None,
                    value=Decimal(expected_points),
                )
            ],
        )
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
        rv = self.wasabi._get_email_optin_from_consent(consents=consents)

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
        rv = self.wasabi._get_email_optin_from_consent(consents=consents)

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
        rv = self.wasabi._get_email_optin_from_consent(consents=consents)

        # THEN
        assert not rv

    @httpretty.activate
    @patch("app.tasks.resend_consents.ReTryTaskStore.set_task")
    @patch("app.tasks.resend_consents.try_hermes_confirm")
    def test_set_customer_preferences_happy_path(self, mock_try_hermes_confirm, mock_set_task):
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
        mock_set_task.assert_called_once()

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._validate_member_number")
    def test_login_happy_path(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() does not raise exception on happy path
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        mock_validate_member_number.return_value = "54321"

        # WHEN
        try:
            self.wasabi.login()
        except Exception as e:
            pytest.fail(f"test_login_happy_path failed: {str(e)}")

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch(
        "app.agents.acteol.Acteol._validate_member_number",
        side_effect=StatusLoginFailedError,
    )
    def test_login_fail(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() fails with the appropriate exception
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        self.wasabi.credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # THEN
        with pytest.raises(StatusLoginFailedError):
            self.wasabi.login()

    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._validate_member_number")
    def test_login_join_path(self, mock_validate_member_number, mock_authenticate):
        """
        Check that the call to login() avoids an email verification call to Acteol when on join journey
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        self.wasabi.user_info["from_join"] = True
        self.wasabi.user_info["credentials"] = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }

        # WHEN
        self.wasabi.login()

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

        self.wasabi.credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
            "merchant_identifier": "54321",
        }

        # WHEN
        self.wasabi.login()

        # THEN
        assert not mock_validate_member_number.called

    # @patch("app.agents.acteol.Acteol.authenticate")
    # @patch("app.agents.acteol.Acteol._validate_member_number")
    # def test_login_add_path(self, mock_validate_member_number, mock_authenticate):
    #     """
    #     Check that the call to login() validates email on an add journey
    #     """
    #     # GIVEN
    #     # Mock us through authentication
    #     mock_authenticate.return_value = self.mock_token

    #     mock_validate_member_number.return_value = "54321"

    #     # These two fields just won't be present in real requests, but set to false here deliberately so we have
    #     # greater transparency
    #     self.wasabi.user_info["from_join"] = False
    #     self.wasabi.user_info["merchant_identifier"] = False

    #     # WHEN
    #     self.wasabi.login()

    #     # THEN
    #     mock_validate_member_number.assert_called_once()

    @patch("app.agents.acteol.signal", autospec=True)
    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.Acteol._validate_member_number")
    def test_login_add_path_calls_success_signals(self, mock_validate_member_number, mock_authenticate, mock_signal):
        """
        Check that the call to login() calls signal events if we're on an ADD journey
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        mock_validate_member_number.return_value = "54321"

        # These two fields just won't be present in real requests, but set to false here to be more explicit
        # about the fact we're on an ADD journey
        self.wasabi.user_info["from_join"] = False
        self.wasabi.user_info["merchant_identifier"] = False
        expected_calls = [  # The expected call stack for signal, in order
            call("log-in-success"),
            call().send(self.wasabi, slug=self.wasabi.scheme_slug),
        ]

        # WHEN
        self.wasabi.login()

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @patch("app.agents.acteol.signal", autospec=True)
    @patch("app.agents.acteol.Acteol.authenticate")
    @patch(
        "app.agents.acteol.Acteol._validate_member_number",
        side_effect=StatusLoginFailedError,
    )
    def test_login_add_path_calls_fail_signals_on_login_error(
        self, mock_validate_member_number, mock_authenticate, mock_signal
    ):
        """
        Check that the call to login() calls signal events if we're on an ADD
        journey but there's a StatusLoginFailedError
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        # These two fields just won't be present in real requests, but set to false here to be more explicit
        # about the fact we're on an ADD journey
        self.wasabi.user_info["from_join"] = False
        self.wasabi.user_info["merchant_identifier"] = False
        self.wasabi.user_info["credentials"] = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }
        expected_calls = [  # The expected call stack for signal, in order
            call("log-in-fail"),
            call().send(self.wasabi, slug=self.wasabi.scheme_slug),
        ]

        # WHEN
        self.assertRaises(
            StatusLoginFailedError,
            self.wasabi.login,
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @patch("app.agents.acteol.signal", autospec=True)
    @patch("app.agents.acteol.Acteol.authenticate")
    @patch(
        "app.agents.acteol.Acteol._validate_member_number",
        side_effect=EndSiteDownError,
    )
    def test_login_add_path_calls_fail_signals_on_agent_error(
        self, mock_validate_member_number, mock_authenticate, mock_signal
    ):
        """
        Check that the call to login() calls signal events if we're on an ADD journey but there's an AgentError
        """
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        # These two fields just won't be present in real requests, but set to false here to be more explicit
        # about the fact we're on an ADD journey
        self.wasabi.user_info["from_join"] = False
        self.wasabi.user_info["merchant_identifier"] = False
        self.wasabi.credentials = {
            "email": "dfelce@testbink.com",
            "card_number": "1048235616",
            "consents": [],
        }
        expected_calls = [  # The expected call stack for signal, in order
            call("log-in-fail"),
            call().send(self.wasabi, slug=self.wasabi.scheme_slug),
        ]

        # WHEN
        self.assertRaises(
            EndSiteDownError,
            self.wasabi.login,
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

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

        expected_mapped_voucher = Voucher(
            state=voucher_state_names[VoucherState.REDEEMED],
            code=voucher["VoucherCode"],
            target_value=None,
            value=None,
            issue_date=1595432679,  # voucher URD as timestamp
            redeem_date=1595432679,  # voucher RedemptionDate as timestamp
            expiry_date=1595432679,  # voucher ExpiryDate as timestamp
        )

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

        expected_mapped_voucher = Voucher(
            state=voucher_state_names[VoucherState.CANCELLED],
            code=voucher["VoucherCode"],
            target_value=None,
            value=None,
            issue_date=1595432679,  # voucher URD as timestamp
            expiry_date=1595432679,  # voucher ExpiryDate as timestamp
        )

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
        one_month_from_now_timestamp = one_month_from_now.int_timestamp

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

        expected_mapped_voucher = Voucher(
            state=voucher_state_names[VoucherState.ISSUED],
            code=voucher["VoucherCode"],
            target_value=None,
            value=None,
            issue_date=now.int_timestamp,  # voucher URD as timestamp
            expiry_date=one_month_from_now_timestamp,
        )

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
        one_month_ago_timestamp = one_month_ago.int_timestamp

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

        expected_mapped_voucher = Voucher(
            state=voucher_state_names[VoucherState.EXPIRED],
            code=voucher["VoucherCode"],
            target_value=None,
            value=None,
            issue_date=now.int_timestamp,  # voucher URD as timestamp
            expiry_date=one_month_ago_timestamp,
        )

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
        expected_in_progress_voucher = Voucher(
            state=voucher_state_names[VoucherState.IN_PROGRESS],
            target_value=None,
            value=points,
        )

        # WHEN
        in_progress_voucher = self.wasabi._make_in_progress_voucher(points=points)

        # THEN
        assert in_progress_voucher == expected_in_progress_voucher

        return in_progress_voucher

    @httpretty.activate
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_transactions_success(self, mock_authenticate):
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

        expected_transactions = [
            Transaction(
                date=arrow.get("2020-06-17T10:56:38.36"),
                description="Kimchee Pancras Square £72.50",
                points=Decimal("1.00"),
                location="Kimchee Pancras Square",
            ),
            Transaction(
                date=arrow.get("2020-06-17T10:56:38.36"),
                description="Kimchee Pancras Square £0.00",
                points=Decimal("1.00"),
                location="Kimchee Pancras Square",
            ),
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
        transactions = self.wasabi.transaction_history()

        # THEN
        assert transactions == expected_transactions

    @httpretty.activate
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_get_contact_ids_by_email_error(self, mock_authenticate):
        """
        Test _check_response_for_error
        """
        # GIVEN
        ctcid = "54321"
        email = "testperson@bink.com"
        api_url = urljoin(self.wasabi.base_url, f"api/Contact/GetContactIDsByEmail?Email={email}")
        response_data = {
            "Response": True,
            "CtcID": ctcid,
            "Error": "Errortest123",
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )

        # THEN
        with pytest.raises(EndSiteDownError):
            self.wasabi.get_contact_ids_by_email(email=email)

    @httpretty.activate
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_get_vouchers_error(self, mock_authenticate):
        """
        Test _check_response_for_error
        """
        # GIVEN
        ctcid = "54321"
        api_url = urljoin(self.wasabi.base_url, f"api/Voucher/GetAllByCustomerID?customerid={ctcid}")
        response_data = {
            "voucher": "null",
            "OfferCategories": "null",
            "response": "false",
            "errors": ["CustomerID is mandatory"],
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )

        # THEN
        with pytest.raises(Exception) as e:
            self.wasabi._get_vouchers(ctcid=ctcid)
            raise Exception("CustomerID is mandatory")

        assert str(e.value) == response_data["errors"][0]

    def test_format_money_value(self):
        # GIVEN
        money_value1 = 6.1
        money_value2 = 60.1
        money_value3 = 600.1
        money_value4 = 6000.100

        # WHEN
        formatted_money_value1 = self.wasabi._format_money_value(money_value=money_value1)
        formatted_money_value2 = self.wasabi._format_money_value(money_value=money_value2)
        formatted_money_value3 = self.wasabi._format_money_value(money_value=money_value3)
        formatted_money_value4 = self.wasabi._format_money_value(money_value=money_value4)

        # THEN
        assert formatted_money_value1 == "6.10"
        assert formatted_money_value2 == "60.10"
        assert formatted_money_value3 == "600.10"
        assert formatted_money_value4 == "6000.10"

    def test_decimalise_to_two_places(self):
        # GIVEN
        value1 = 6.1
        value2 = 60.1
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
        assert decimalised2 == Decimal("60.10")
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
            location_name=location_name,
            formatted_total_cost=formatted_total_cost,
        )

        # THEN
        assert parsed_transaction is not None
        assert isinstance(parsed_transaction.date, arrow.Arrow)
        assert parsed_transaction.description == description
        assert parsed_transaction.location == location_name
        assert isinstance(parsed_transaction.points, Decimal)
        assert parsed_transaction.points == expected_points

    def test_check_response_for_error(self):
        """
        Testing _check_response_for_error response returning "Error" no "s"
        """
        # GIVEN
        resp_json = {"Response": False, "Error": "Internal Exception"}

        # WHEN
        with pytest.raises(EndSiteDownError):
            self.wasabi._check_response_for_error(resp_json)

    def test_check_deleted_user(self):
        """
        Test handling 'Deleted User error'
        """
        # GIVEN
        resp_json = {"CustomerID": "0", "CurrentMemberNumber": "ABC123"}

        # WHEN
        with pytest.raises(NoSuchRecordError):
            self.wasabi._check_deleted_user(resp_json)

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_timeout(self, mock_authenticate, mock_send_to_atlas):
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.ADD
        self.wasabi.credentials = {"card_number": "123", "email": "test@test.com"}
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token
        # Force fast-as-possible retries so we don't have slow running tests

        api_url = urljoin(self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber")
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.GATEWAY_TIMEOUT,
        )

        # THEN
        with pytest.raises(RetryLimitReachedError):
            self.wasabi._validate_member_number()

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_fail_authentication(self, mock_authenticate, mock_send_to_atlas):
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.ADD
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        api_url = urljoin(self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber")
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.UNAUTHORIZED,
        )

        # THEN
        with pytest.raises(StatusLoginFailedError):
            self.wasabi._validate_member_number()

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_fail_forbidden(self, mock_authenticate, mock_send_to_atlas):
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.ADD
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        api_url = urljoin(self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber")
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            status=HTTPStatus.FORBIDDEN,
        )

        # THEN
        with pytest.raises(IPBlockedError):
            self.wasabi._validate_member_number()

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_validation_error(self, mock_authenticate, mock_send_to_atlas):
        """
        Test one of the error scenarios - ValidationError
        """
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.ADD
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        api_url = urljoin(self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber")
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

        # THEN
        with pytest.raises(ValidationError):
            self.wasabi._validate_member_number()

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_error(self, mock_authenticate, mock_send_to_atlas):
        """
        Test _check_response_for_error
        """
        # GIVEN
        self.wasabi.journey_type = JourneyTypes.ADD
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token

        api_url = urljoin(self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber")
        response_data = {
            "Error": "errortest333",
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )

        # THEN
        with pytest.raises(EndSiteDownError):
            self.wasabi._validate_member_number()

    @httpretty.activate
    @patch("app.agents.base.signal", autospec=True)
    @patch("app.agents.acteol.Acteol.authenticate")
    def test_validate_member_number_succeeds(self, mock_authenticate, mock_base_signal):
        # GIVEN
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token
        self.wasabi.journey_type = JourneyTypes.ADD

        api_url = urljoin(self.wasabi.base_url, "api/Contact/ValidateContactMemberNumber")
        ctcid = 54321
        response_data = {"ValidationMsg": "", "IsValid": True, "CtcID": ctcid}
        expected_ctcid = str(ctcid)
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response_data))],
            status=HTTPStatus.OK,
        )

        # WHEN
        ctcid = self.wasabi._validate_member_number()

        # THEN
        assert ctcid == expected_ctcid

    @patch("app.agents.acteol.get_task", return_value=Mock())
    @patch("app.agents.acteol.Acteol._account_already_exists")
    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.signal", autospec=True)
    def test_join_calls_signal_fail_for_join_error(
        self, mock_signal, mock_authenticate, mock_account_already_exists, mock_get_task
    ):
        """
        Test JOIN journey calls signal join fail
        """
        # Mock us through authentication
        self.wasabi.credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
            "card_number": "1048183413",
            "merchant_identifier": 142163,
        }
        mock_authenticate.return_value = self.mock_token
        mock_account_already_exists.return_value = True
        # GIVEN
        expected_calls = [  # The expected call stack for signal, in order
            call("join-fail"),
            call().send(self.wasabi, channel=self.wasabi.channel, slug=self.wasabi.scheme_slug),
        ]

        # WHEN
        self.assertRaises(AccountAlreadyExistsError, self.wasabi.join)

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @patch("app.agents.acteol.get_task", return_value=Mock())
    @patch(
        "app.agents.acteol.Acteol._create_account",
        side_effect=EndSiteDownError,
    )
    @patch("app.agents.acteol.Acteol._account_already_exists")
    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.signal", autospec=True)
    def test_join_calls_signal_fail_for_agent_error(
        self,
        mock_signal,
        mock_authenticate,
        mock_account_already_exists,
        mock_create_account,
        mock_get_task,
    ):
        """
        Test JOIN journey calls signal join fail, have to mock through some of the earlier methods called in
        join()
        """
        # Mock us through authentication
        mock_authenticate.return_value = self.mock_token
        mock_account_already_exists.return_value = False
        # GIVEN
        self.wasabi.credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
            "card_number": "1048183413",
            "merchant_identifier": 142163,
        }
        expected_calls = [  # The expected call stack for signal, in order
            call("join-fail"),
            call().send(self.wasabi, channel=self.wasabi.channel, slug=self.wasabi.scheme_slug),
        ]

        # WHEN
        self.assertRaises(EndSiteDownError, self.wasabi.join)

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.acteol.get_task", return_value=Mock())
    @patch(
        "app.agents.acteol.Acteol._add_member_number",
        side_effect=StatusLoginFailedError,
    )
    @patch("app.agents.acteol.Acteol._create_account")
    @patch("app.agents.acteol.Acteol._account_already_exists")
    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.signal", autospec=True)
    def test_join_calls_signal_fail_for_login_error(
        self,
        mock_signal,
        mock_authenticate,
        mock_account_already_exists,
        mock_create_account,
        mock_add_member_number,
        mock_get_task,
    ):
        """
        Test JOIN journey calls signal join fail, have to mock through some of the earlier methods called in
        join()
        """
        # Mock us through authentication
        self.wasabi.credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
            "card_number": "1048183413",
            "merchant_identifier": 142163,
        }
        mock_get_task.return_value.request_data = {}
        mock_authenticate.return_value = self.mock_token
        mock_account_already_exists.return_value = False
        mock_create_account.return_value = "54321"
        # GIVEN
        expected_calls = [  # The expected call stack for signal, in order
            call("join-fail"),
            call().send(self.wasabi, channel=self.wasabi.channel, slug=self.wasabi.scheme_slug),
        ]

        # WHEN
        self.assertRaises(StatusLoginFailedError, self.wasabi.join)

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @patch("app.agents.acteol.get_task", return_value=Mock())
    @patch("app.agents.acteol.Acteol._set_customer_preferences")
    @patch("app.agents.acteol.Acteol._get_email_optin_from_consent")
    @patch("app.agents.acteol.Acteol._customer_fields_are_present")
    @patch("app.agents.acteol.Acteol._get_customer_details")
    @patch("app.agents.acteol.Acteol._add_member_number")
    @patch("app.agents.acteol.Acteol._create_account")
    @patch("app.agents.acteol.Acteol._account_already_exists")
    @patch("app.agents.acteol.Acteol.authenticate")
    @patch("app.agents.acteol.signal", autospec=True)
    def test_join_calls_signal_success(
        self,
        mock_signal,
        mock_authenticate,
        mock_account_already_exists,
        mock_create_account,
        mock_add_member_number,
        mock_get_customer_details,
        mock_add_customer_fields_are_present,
        mock_get_email_optin_from_consent,
        mock_set_customer_preferences,
        mock_get_task,
    ):
        """
        Test JOIN journey calls signal join success if no exceptions raised. Need to mock several calls
        to result in 'successful' join
        """

        ctcid = "54321"
        member_number = "123456789"
        # Mock us through authentication
        self.wasabi.credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
            "card_number": "1048183413",
            "merchant_identifier": 142163,
        }
        mock_get_task.return_value.request_data = {}
        mock_authenticate.return_value = self.mock_token
        mock_account_already_exists.return_value = False
        mock_create_account.return_value = ctcid
        mock_add_member_number.return_value = member_number
        mock_get_customer_details.return_value = {
            "Email": "me@there.com",
            "CurrentMemberNumber": member_number,
            "CustomerID": ctcid,
        }
        mock_add_customer_fields_are_present.return_value = True
        mock_get_email_optin_from_consent.return_value = {"EmailOptIn": True}
        # GIVEN
        expected_calls = [  # The expected call stack for signal, in order
            call("join-success"),
            call().send(self.wasabi, channel=self.wasabi.channel, slug=self.wasabi.scheme_slug),
        ]

        # WHEN
        self.wasabi.join()

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    def test_check_deleted_user_displays_correct_log_message(self):
        self.wasabi.credentials = {
            "first_name": "Sarah",
            "last_name": "TestPerson",
            "email": "testperson@bink.com",
            "date_of_birth": "1999-01-01",
            "card_number": "this_is_a_card_number",
            "merchant_identifier": 142163,
        }
        resp_json = {"CustomerID": 0, "CtcID": 456}
        with self.assertRaises(NoSuchRecordError), self.assertLogs(level="DEBUG") as log:
            self.wasabi._check_deleted_user(resp_json)
            self.assertEqual(
                log.output,
                ["INFO:acteol-agent: Acteol card number has been deleted: Card number: this_is_a_card_number"],
            )
