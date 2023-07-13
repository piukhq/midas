import json
import unittest
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import MagicMock, call, patch
from urllib.parse import urljoin

import httpretty
import pytest
from soteria.configuration import Configuration

import settings
from app.agents.itsu import Itsu
from app.agents.schemas import Balance, Voucher
from app.exceptions import CardNumberError
from app.scheme_account import JourneyTypes

settings.ITSU_VOUCHER_OFFER_ID = 23


class TestItsu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mock_config = MagicMock()
        mock_config.merchant_url = "https://atreemouat.itsucomms.co.uk/"
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
            "itsu_access_token": "abcde12345fghij",
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
            cls.itsu = Itsu(*MOCK_AGENT_CLASS_ARGUMENTS, scheme_slug="itsu")
            cls.itsu.integration_service = "SYNC"

        cls.itsu.max_retries = 0
        cls.mock_voucher_resp = [
            {
                "VoucherID": 54157,
                "OfferID": 23,
                "StartDate": "2023-05-22T10:11:30.263",
                "ExpiryDate": "2024-05-21T23:59:00",
                "CategoryID": 11,
                "CategoryName": "Loyalty",
                "Description": "itsu loyalty reward for earning 7 stamps",
                "CtcID": 576077,
                "Redeemed": False,
                "URD": "2023-05-22T10:11:30.263",
                "Disabled": False,
                "RandomID": "A3OM3660",
                "VoucherCode": "A3OM3660",
                "Value": None,
                "DiscountAmount": 0.0,
                "DiscountPercentage": 0.0,
                "QualifiedBasketAmount": 0.0,
                "ProductKey": "A3",
                "InterestNodeCode": 0,
                "RedemptionTypes": [{"OrderTypeID": 1, "OrderTypeDescription": "InStore"}],
                "DisplayChannels": [],
            },
            {
                "VoucherID": 54158,
                "OfferID": 23,
                "StartDate": "2023-05-22T10:11:30.42",
                "ExpiryDate": "2024-05-21T23:59:00",
                "CategoryID": 11,
                "CategoryName": "Loyalty",
                "Description": "itsu loyalty reward for earning 7 stamps",
                "CtcID": 576077,
                "Redeemed": False,
                "RedemptionDate": "null",
                "URD": "2023-05-22T10:11:30.42",
                "Disabled": True,
                "RandomID": "A3CV5655",
                "VoucherCode": "A3CV5655",
                "DiscountAmount": 0.0,
                "DiscountPercentage": 0.0,
                "QualifiedBasketAmount": 0.0,
                "ProductKey": "A3",
                "InterestNodeCode": 0,
                "ActiveOffer": "true",
                "RedemptionTypes": [{"OrderTypeID": 1, "OrderTypeDescription": "InStore"}],
                "DisplayChannels": [],
            },
        ]
        cls.mock_get_customer_details_resp = {
            "Firstname": "Georgie",
            "Lastname": "Smith",
            "BirthDate": "null",
            "Email": "null",
            "MobilePhone": "null",
            "Address1": "null",
            "Address2": "null",
            "PostCode": "null",
            "City": "null",
            "CountryCode": "null",
            "LastVisiteDate": "null",
            "LoyaltyPointsBalance": 3,
            "LoyaltyCashBalance": 0.05,
            "CustomerID": 576077,
            "LoyaltyCardNumber": "null",
            "CurrentTiers": "",
            "NextTiers": "",
            "NextTiersAmountLeft": 0.0,
            "Property": "null",
            "TiersExpirationDate": "null",
            "PointsExpirationDate": "null",
            "MemberNumbersList": ["1406000001"],
            "CurrentMemberNumber": "1406000001",
        }

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.itsu.Itsu.authenticate")
    @patch("app.agents.itsu.Itsu._patch_customer_details")
    @patch("app.agents.itsu.Itsu._find_customer_details", return_value=["123", "456"])
    def test_login_happy_path(self, mock_validate_member_number, mock_patch_details, mock_authenticate, mock_signal):
        mock_authenticate.return_value = self.mock_token
        self.itsu.credentials = {"card_number": "111111"}
        self.itsu.login()
        self.assertEqual(self.itsu.identifier, {"card_number": "111111", "merchant_identifier": "456"})
        self.assertEqual(self.itsu.credentials, {"card_number": "111111", "merchant_identifier": "456", "ctcid": "123"})
        mock_patch_details.assert_called
        expected_calls = [  # The expected call stack for signal, in order
            call("log-in-success"),
            call().send(self.itsu, slug=self.itsu.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.itsu.Itsu._patch_customer_details")
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.itsu.Itsu.authenticate")
    def test_login_invalid_card_number(self, mock_authenticate, mock_signal, mock_patch_customer_details):
        mock_authenticate.return_value = self.mock_token
        self.itsu.credentials = {"card_number": "12345"}
        api_url = urljoin(
            self.itsu.base_url,
            "api/Customer/FindCustomerDetails",
        )
        response = {
            "ResponseData": None,
            "ResponseStatus": False,
            "Errors": [{"ErrorCode": 4, "ErrorDescription": "No Data found"}],
        }
        httpretty.register_uri(
            httpretty.POST,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response))],
            status=HTTPStatus.OK,
        )
        with pytest.raises(CardNumberError):
            self.itsu.login()
            expected_calls = [  # The expected call stack for signal, in order
                call("log-in-fail"),
                call().send(self.itsu, slug=self.itsu.scheme_slug),
            ]
            mock_signal.assert_has_calls(expected_calls)
            mock_patch_customer_details.assert_not_called

    @httpretty.activate
    @patch("app.agents.itsu.Itsu.authenticate")
    def test_find_customer_details(self, mock_authenticate):
        mock_authenticate.return_value = self.mock_token
        self.itsu.credentials = {"card_number": "12345"}
        api_url = urljoin(
            self.itsu.base_url,
            "api/Customer/FindCustomerDetails",
        )
        response = {
            "ResponseData": [
                {
                    "CtcID": 576077,
                    "CpyID": 532426,
                    "CreateDate": "2022-07-29T17:55:00.787",
                    "ModifiedDate": "2022-09-22T12:34:03.387",
                    "ModifiedBy": 643,
                    "ModifiedByName": "PEPPER",
                    "Source": "PEPPER",
                    "LastModifiedSource": "null",
                    "MD5": "711f80daf3b0d6c2f77829e68682ab4a",
                    "ExternalIdentifier": {"ExternalID": "62e4018390e6630e49aedcc8", "ExternalSource": "PEPPER"},
                    "PersonalDetails": {
                        "Title": "null",
                        "FirstName": "Georgie",
                        "LastName": "Smith",
                        "Email": "null",
                        "MobilePhone": "null",
                        "Phone": "null",
                        "BirthDate": "null",
                        "JobTitle": "",
                        "ParentEmailAddress": "null",
                        "Gender": 0,
                        "CustomerAddress": {
                            "Address1": "null",
                            "Address2": "null",
                            "Address3": "null",
                            "City": "null",
                            "PostCode": "null",
                            "StateName": "null",
                            "CountryCode": "null",
                            "Phone": "null",
                        },
                    },
                    "ReferrerDetails": "null",
                    "LoyaltyDetails": "null",
                    "SupInfo": [
                        {"FieldName": "HomeSiteID", "FieldContent": ""},
                        {"FieldName": "Interests", "FieldContent": ""},
                        {"FieldName": "BinkActive", "FieldContent": "true"},
                        {"FieldName": "BinkActive2", "FieldContent": ""},
                        {"FieldName": "acquisitionChannel", "FieldContent": ""},
                    ],
                    "MarketingOptin": "null",
                    "Preferences": "null",
                    "Tags": "null",
                    "InteractionsInfo": "null",
                    "ProcessMydata": "null",
                    "IsSuspended": "false",
                    "DeleteMyData": "null",
                    "DoNotExport": "false",
                    "BrandID": "null",
                    "CorporateDetails": "null",
                }
            ],
            "ResponseStatus": "true",
            "Errors": [],
        }
        httpretty.register_uri(
            httpretty.POST,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response))],
            status=HTTPStatus.OK,
        )
        ctcid, pepper_id = self.itsu._find_customer_details()
        self.assertEqual(ctcid, "576077")
        self.assertEqual(pepper_id, "62e4018390e6630e49aedcc8")

    @patch("app.agents.itsu.Itsu.authenticate")
    @patch("app.agents.itsu.Itsu._find_customer_details")
    @patch("app.agents.itsu.Itsu._get_customer_details")
    @patch("app.agents.itsu.Itsu.update_hermes_credentials")
    @patch("app.agents.itsu.Itsu._get_vouchers_by_offer_id")
    def test_balance_from_login_happy_path(
        self,
        mock_get_vouchers,
        mock_update_credentials,
        mock_get_customer_details,
        mock_find_customer_details,
        mock_authenticate,
    ):
        mock_authenticate.return_value = self.mock_token
        mock_get_customer_details.return_value = self.mock_get_customer_details_resp
        mock_get_vouchers.return_value = self.mock_voucher_resp

        self.itsu.credentials = {"ctcid": "12345", "merchant_identifier": "67890", "card_number": "00000"}
        balance = self.itsu.balance()
        self.assertEqual(
            balance,
            Balance(
                points=Decimal("3"),
                value=Decimal("3"),
                value_label="",
                reward_tier=0,
                balance=None,
                vouchers=[
                    Voucher(
                        state="inprogress",
                        issue_date=None,
                        redeem_date=None,
                        expiry_date=None,
                        code=None,
                        value=Decimal("3"),
                        target_value=None,
                        conversion_date=None,
                    ),
                    Voucher(
                        state="issued",
                        issue_date=1684750290,
                        redeem_date=None,
                        expiry_date=1716335940,
                        code="----------",
                        value=None,
                        target_value=None,
                        conversion_date=None,
                    ),
                ],
            ),
        )
        mock_find_customer_details.assert_not_called()
        mock_update_credentials.assert_called_with("67890", mock_get_customer_details.return_value)

    @patch("app.agents.itsu.Itsu.authenticate")
    @patch("app.agents.itsu.Itsu._find_customer_details")
    @patch("app.agents.itsu.Itsu._get_customer_details")
    @patch("app.agents.itsu.Itsu.update_hermes_credentials")
    @patch("app.agents.itsu.Itsu._get_vouchers_by_offer_id")
    def test_balance_from_view_happy_path(
        self,
        mock_get_vouchers,
        mock_update_credentials,
        mock_get_customer_details,
        mock_find_customer_details,
        mock_authenticate,
    ):
        mock_authenticate.return_value = self.mock_token
        mock_get_customer_details.return_value = self.mock_get_customer_details_resp
        mock_get_vouchers.return_value = self.mock_voucher_resp
        self.itsu.credentials = {"merchant_identifier": "67890", "card_number": "00000"}
        mock_find_customer_details.return_value = ("90909090", "67890")
        balance = self.itsu.balance()
        self.assertEqual(
            balance,
            Balance(
                points=Decimal("3"),
                value=Decimal("3"),
                value_label="",
                reward_tier=0,
                balance=None,
                vouchers=[
                    Voucher(
                        state="inprogress",
                        issue_date=None,
                        redeem_date=None,
                        expiry_date=None,
                        code=None,
                        value=Decimal("3"),
                        target_value=None,
                        conversion_date=None,
                    ),
                    Voucher(
                        state="issued",
                        issue_date=1684750290,
                        redeem_date=None,
                        expiry_date=1716335940,
                        code="----------",
                        value=None,
                        target_value=None,
                        conversion_date=None,
                    ),
                ],
            ),
        )
        mock_find_customer_details.assert_called
        mock_update_credentials.assert_called_with("67890", mock_get_customer_details.return_value)

    @httpretty.activate
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.itsu.Itsu.authenticate")
    def test_balance_unknown_error_occured_when_getting_customer_details(self, mock_authenticate, mock_signal):
        mock_authenticate.return_value = self.mock_token
        ctcid = "7778888"
        self.itsu.credentials = {"card_number": "12345", "ctcid": ctcid}
        api_url = urljoin(
            self.itsu.base_url,
            f"api/Loyalty/GetCustomerDetails?customerid={ctcid}",
        )
        response = {
            "ResponseData": None,
            "ResponseStatus": False,
            "Errors": [{"ErrorCode": 8, "ErrorDescription": "Unknown Error"}],
        }
        httpretty.register_uri(
            httpretty.GET,
            api_url,
            responses=[httpretty.Response(body=json.dumps(response))],
            status=HTTPStatus.OK,
        )
        with pytest.raises(Exception):
            self.itsu.balance()
