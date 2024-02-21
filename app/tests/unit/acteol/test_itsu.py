import json
import unittest
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import MagicMock, call, patch
from urllib.parse import urljoin

import httpretty
import pytest
import requests
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
        cls.mock_voucher_resp = {
            "voucher": [
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
        }
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
        cls.mock_find_customer_details_resp = {
            "ResponseData": [
                {
                    "CtcID": 576077,
                    "CpyID": 532765,
                    "CreateDate": "2023-08-23T14:09:09.12",
                    "ModifiedDate": "2023-08-23T14:09:09.12",
                    "ModifiedBy": None,
                    "ModifiedByName": None,
                    "Source": "PEPPER",
                    "LastModifiedSource": None,
                    "MD5": "711f80daf3b0d6c2f77829e68682ab4a",
                    "ExternalIdentifier": {"ExternalID": "62e4018390e6630e49aedcc8", "ExternalSource": "PEPPER"},
                    "PersonalDetails": {
                        "Title": None,
                        "FirstName": "Georgie",
                        "LastName": "Smith",
                        "Email": "gsmith@test.com",
                        "MobilePhone": "",
                        "Phone": "",
                        "BirthDate": None,
                        "JobTitle": None,
                        "ParentEmailAddress": "",
                        "Gender": 0,
                        "CustomerAddress": {
                            "Address1": None,
                            "Address2": None,
                            "Address3": None,
                            "City": None,
                            "PostCode": None,
                            "StateName": None,
                            "CountryCode": None,
                            "Phone": None,
                        },
                        "DoNotExport": None,
                    },
                    "ReferrerDetails": None,
                    "LoyaltyDetails": {
                        "LoyaltyPointsBalance": 3.0,
                        "LoyaltyCashBalance": 0.05,
                        "LifeTimePoints": 1.0,
                        "CyclePointsBalance": 1.0,
                        "PointsNeededForNextRewards": 4.0,
                        "CurrentTiersName": "",
                        "TierLastUpdatedDate": None,
                        "NextTiersName": "",
                        "TiersExpirationDate": None,
                        "MemberNumbers": ["1406000001"],
                        "CardsToken": None,
                    },
                    "SupInfo": [
                        {"FieldName": "HomeSiteID", "FieldContent": ""},
                        {"FieldName": "Interests", "FieldContent": ""},
                        {"FieldName": "BinkActive", "FieldContent": ""},
                        {"FieldName": "BinkActive2", "FieldContent": ""},
                        {"FieldName": "acquisitionChannel", "FieldContent": "BINK"},
                        {"FieldName": "hadLoggedIn", "FieldContent": ""},
                        {"FieldName": "hasLoggedIn", "FieldContent": "false"},
                    ],
                    "MarketingOptin": {
                        "EmailOptin": True,
                        "SmsOptin": True,
                        "MailOptin": True,
                        "PhoneOptin": True,
                        "PushNotificationOptin": True,
                        "WebPushNotificationOptin": False,
                        "WhatsAppOptin": False,
                        "AppOptin": False,
                    },
                    "Preferences": None,
                    "Interests": None,
                    "Tags": None,
                    "InteractionsInfo": None,
                    "ProcessMydata": True,
                    "IsSuspended": False,
                    "DeleteMyData": False,
                    "DoNotExport": False,
                    "BrandID": None,
                    "CorporateDetails": None,
                    "CustomerPicture": None,
                    "StaffDetails": None,
                }
            ]
        }

    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.itsu.Itsu.authenticate")
    @patch("app.agents.itsu.Itsu._find_customer_details")
    @httpretty.activate
    def test_login_happy_path(self, mock_find_customer_details, mock_authenticate, mock_signal):
        httpretty.register_uri(
            httpretty.PUT,
            urljoin(settings.HERMES_URL, "schemes/accounts/1/credentials"),
            status=HTTPStatus.OK,
        )
        httpretty.register_uri(
            httpretty.PATCH,
            urljoin(
                self.itsu.base_url,
                "api/Customer/Patch",
            ),
            status=HTTPStatus.OK,
        )
        mock_find_customer_details.return_value = self.mock_find_customer_details_resp["ResponseData"][0]
        mock_authenticate.return_value = self.mock_token
        self.itsu.credentials = {"card_number": "111111"}

        self.itsu.login()

        assert self.itsu.identifier == {"card_number": "111111", "merchant_identifier": "62e4018390e6630e49aedcc8"}
        assert self.itsu.credentials == {
            "card_number": "111111",
            "merchant_identifier": "62e4018390e6630e49aedcc8",
            "ctcid": "576077",
        }
        mock_signal.assert_has_calls(
            [  # The expected call stack for signal, in order
                call("log-in-success"),
                call().send(self.itsu, slug=self.itsu.scheme_slug),
            ]
        )
        assert httpretty.last_request().path == "/schemes/accounts/1/credentials"

    @httpretty.activate
    @patch("app.requests_retry.requests_retry_session", return_value=requests.Session())
    @patch("app.agents.itsu.signal", autospec=True)
    @patch("app.agents.itsu.Itsu.authenticate")
    def test_login_invalid_card_number(self, mock_authenticate, mock_signal, mock_requests_retry_session):
        httpretty.register_uri(
            httpretty.POST,
            uri=f"{settings.ATLAS_URL}/audit/membership/",
            status=HTTPStatus.OK,
        )
        mock_authenticate.return_value = self.mock_token
        self.itsu.credentials = {"card_number": "12345"}
        httpretty.register_uri(
            httpretty.POST,
            urljoin(
                self.itsu.base_url,
                "api/Customer/FindCustomerDetails",
            ),
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "ResponseData": None,
                            "ResponseStatus": False,
                            "Errors": [{"ErrorCode": 4, "ErrorDescription": "No Data found"}],
                        }
                    )
                )
            ],
            status=HTTPStatus.OK,
        )
        with pytest.raises(CardNumberError):
            self.itsu.login()
        mock_signal.assert_has_calls(
            [
                call("log-in-fail"),
                call().send(self.itsu, slug=self.itsu.scheme_slug),
            ]
        )

    @httpretty.activate
    @patch("app.agents.itsu.Itsu.authenticate")
    def test_find_customer_details(self, mock_authenticate):
        mock_authenticate.return_value = self.mock_token
        self.itsu.credentials = {"card_number": "12345"}
        httpretty.register_uri(
            httpretty.POST,
            urljoin(
                self.itsu.base_url,
                "api/Customer/FindCustomerDetails",
            ),
            responses=[httpretty.Response(body=json.dumps(self.mock_find_customer_details_resp))],
            status=HTTPStatus.OK,
        )
        customer_details = self.itsu._find_customer_details()
        assert customer_details == self.mock_find_customer_details_resp["ResponseData"][0]

    @httpretty.activate
    @patch("app.agents.itsu.Itsu.authenticate")
    def test_balance_happy_path(
        self,
        mock_authenticate,
    ):
        mock_authenticate.return_value = self.mock_token
        httpretty.register_uri(
            httpretty.POST,
            urljoin(
                self.itsu.base_url,
                "api/Customer/FindCustomerDetails",
            ),
            responses=[httpretty.Response(body=json.dumps(self.mock_find_customer_details_resp))],
            status=HTTPStatus.OK,
        )
        httpretty.register_uri(
            httpretty.POST,
            urljoin(
                self.itsu.base_url,
                "api/Voucher/GetAllByCustomerIDByParams",
            ),
            responses=[httpretty.Response(body=json.dumps(self.mock_voucher_resp))],
            status=HTTPStatus.OK,
        )
        self.itsu.credentials = {"ctcid": "12345", "merchant_identifier": "67890", "card_number": "00000"}
        self.itsu._points_balance = Decimal(3)

        balance = self.itsu.balance()

        assert balance == Balance(
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
        )
