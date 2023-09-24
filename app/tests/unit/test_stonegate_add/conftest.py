import pytest
from soteria.configuration import Configuration

import settings


@pytest.fixture()
def patch_balance_login(monkeypatch, mock_europa_request, redis_retry_pretty_fix):
    def patchit(credentials, secret, conf_body):
        monkeypatch.setattr("app.resources.decrypt_credentials", lambda *_: credentials)
        monkeypatch.setattr(settings, "CONFIG_SERVICE_URL", "http://mock_europa.com")
        monkeypatch.setattr(Configuration, "get_security_credentials", lambda *_: secret)
        monkeypatch.setattr("app.agents.stonegate.Stonegate.authenticate", lambda *_: None)
        mock_europa_request(conf_body)

    return patchit


@pytest.fixture
def mock_stonegate_signals(mock_signals):
    return mock_signals(patches=["app.agents.stonegate.signal"], base_agent=True)


@pytest.fixture
def test_vars():
    class Vars:
        def __init__(
            self,
            account_id=95812687,
            user_id="289645",
            bink_user_id=678934,
            ctc_id=35,
            card_number="3287211356",
            points=3.1,
        ):
            self.account_id = account_id
            self.user_id = user_id
            self.bink_user_id = bink_user_id
            self.ctc_id = ctc_id
            self.card_number = card_number
            self.points_balance = points

            self.customer_details_response = {
                "ResponseData": [
                    {
                        "CtcID": self.ctc_id,
                        "CpyID": self.ctc_id,
                        "CreateDate": "2023-06-08T09:11:41",
                        "ModifiedDate": "2023-06-08T09:11:41",
                        "ModifiedBy": None,
                        "ModifiedByName": None,
                        "Source": "Bink",
                        "LastModifiedSource": None,
                        "MD5": "21f759d4187a42c2bf789e17df9784ba",
                        "ExternalIdentifier": {"ExternalID": "", "ExternalSource": "Bink"},
                        "PersonalDetails": {
                            "Title": None,
                            "FirstName": "Michael",
                            "LastName": "Morar",
                            "Email": "bink_mm@bink.com",
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
                            "LoyaltyPointsBalance": self.points_balance,
                            "LoyaltyCashBalance": 0.0,
                            "LifeTimePoints": 0.0,
                            "CyclePointsBalance": 0.0,
                            "PointsNeededForNextRewards": 0.0,
                            "CurrentTiersName": "",
                            "TierLastUpdatedDate": None,
                            "NextTiersName": "",
                            "TiersExpirationDate": None,
                            "MemberNumbers": ["3287211356"],
                            "CardsToken": None,
                        },
                        "SupInfo": [
                            {"FieldName": "CompletedFavoriteMission", "FieldContent": ""},
                            {"FieldName": "CompletedLocationPermissionMission", "FieldContent": ""},
                            {"FieldName": "CompletedSocialShareMission", "FieldContent": ""},
                            {
                                "FieldName": "HashPassword",
                                "FieldContent": "$argon2id$v=19$m=16,t=2,p=1$MTIzNDU2Nzg$Dhk8fwnes+f9vzOwgdALlA",
                            },
                            {"FieldName": "pll_bink", "FieldContent": "false"},
                            {"FieldName": "pll_mixr", "FieldContent": ""},
                            {"FieldName": "ReferredByCode", "FieldContent": ""},
                            {"FieldName": "sample string 1", "FieldContent": "sample string 4"},
                            {"FieldName": "sample string 2", "FieldContent": ""},
                        ],
                        "MarketingOptin": None,
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
                ],
                "ResponseStatus": True,
                "Errors": [],
            }
            self.customer_details_not_found_response = {
                "ResponseData": None,
                "ResponseStatus": False,
                "Errors": [{"ErrorCode": 4, "ErrorDescription": "No Data found"}],
            }

    return Vars
