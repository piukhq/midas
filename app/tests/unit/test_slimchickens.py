import json
import unittest
from decimal import Decimal
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock, call

import httpretty
from soteria.configuration import Configuration

from app.agents.schemas import Balance, Voucher
from app.agents.slimchickens import SlimChickens
from app.exceptions import AccountAlreadyExistsError, BaseError, StatusLoginFailedError, WeakPasswordError
from app.scheme_account import JourneyTypes

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
    "attributes": {"optin2": "True"},
    "channels": [{"channelKey": "1eceec21734546b6b7d9a0f4a307c94b"}],
}

ADD_RESPONSE_NO_VOUCHER_JSON_200 = {
    "configuration": {},
    "tags": [],
    "heroImages": [],
    "offers": [],
    "loyaltySchemes": [],
    "sites": [],
    "nearby": [],
    "welcomeImages": [],
    "menuImages": [],
    "wallet": [
        {
            "itemId": "2b9811f91c4545b7877e78f663b9bb9b",
            "voucherCode": "747163178",
            "voucherExpiry": "2024-08-20T22:59:59Z",
            "cardPoints": 0,
            "passbookUrl": "https://demoapi.podifi.com/passbook",
            "loyaltyScheme": {
                "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                "accountName": "Eagle Eye UAT",
                "loyaltySchemeKey": "2b9811f91c4545b7877e78f663b9bb9b",
                "name": "New Stamp Loyalty",
                "tags": [
                    {
                        "name": "Bink",
                        "generic": False,
                        "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                        "tagKey": "b7b88147eead40fa883ce7591069cbf8",
                        "usernames": None,
                    }
                ],
                "defaultPoints": 1,
                "defaultFrequency": 1,
                "defaultFrequencyType": "DAY",
                "rewardTiers": [
                    {
                        "rewardTierKey": "b6b8c4c93cef4461b3dee2fabc606339",
                        "name": "New Stamp Loyalty 1",
                        "type": "REPEAT",
                        "pointValue": 1,
                        "autoTrigger": True,
                        "loyaltyScheme": None,
                        "rewardEvents": [
                            {
                                "rewardEventKey": "d9142d1fcc26461cbd952b17c66e7429",
                                "name": "New Stamp Loyalty 1 PUSH",
                                "message": "Congratulations ${consumer.forename} !",
                                "type": "PUSH",
                                "screen": "WALLET",
                                "rewardOffer": None,
                                "rewardTier": None,
                            },
                            {
                                "rewardEventKey": "ea5761530664449c80cc51f3fc601d89",
                                "name": "New Stamp Loyalty 1 OFFER",
                                "message": None,
                                "type": "OFFER",
                                "screen": None,
                                "rewardOffer": {
                                    "rewardOfferKey": "410779c0bfc985e7f87f11408ffe195e",
                                    "name": "New Stamp 1 - 3 Free Wings",
                                    "stampImageUrl": None,
                                },
                                "rewardTier": None,
                            },
                        ],
                    },
                    {
                        "rewardTierKey": "d1ba89995db245fab25a78ac8d1a4ee4",
                        "name": "New Stamp Loyalty 3",
                        "type": "REPEAT",
                        "pointValue": 3,
                        "autoTrigger": True,
                        "loyaltyScheme": None,
                        "rewardEvents": [
                            {
                                "rewardEventKey": "774dfdf598484519b838caa758a7e38f",
                                "name": "New Stamp Loyalty 3 OFFER",
                                "message": None,
                                "type": "OFFER",
                                "screen": None,
                                "rewardOffer": {
                                    "rewardOfferKey": "6e10c54986115b3fd3c8db020170a152",
                                    "name": "New Stamp 3 - Free Shake",
                                    "stampImageUrl": None,
                                },
                                "rewardTier": None,
                            },
                            {
                                "rewardEventKey": "a0482bd9eba440b4b40cf1366a68ca6a",
                                "name": "New Stamp Loyalty 3 PUSH",
                                "message": "Congratulations ${consumer.forename} !",
                                "type": "PUSH",
                                "screen": "WALLET",
                                "rewardOffer": None,
                                "rewardTier": None,
                            },
                        ],
                    },
                    {
                        "rewardTierKey": "eca485ffd3214bf4981cda15d9440592",
                        "name": "New Stamp Loyalty 5",
                        "type": "REPEAT",
                        "pointValue": 5,
                        "autoTrigger": True,
                        "loyaltyScheme": None,
                        "rewardEvents": [
                            {
                                "rewardEventKey": "ab8997c099414326980de3cccabf1ee9",
                                "name": "New Stamp Loyalty 5 OFFER",
                                "message": None,
                                "type": "OFFER",
                                "screen": None,
                                "rewardOffer": {
                                    "rewardOfferKey": "5f6f1572962eb7993aa3b3fb3d18ed57",
                                    "name": "New Stamp 5 - Free Meal",
                                    "stampImageUrl": None,
                                },
                                "rewardTier": None,
                            },
                            {
                                "rewardEventKey": "755d53b697154f1a83e4b35e633fda05",
                                "name": "New Stamp Loyalty 5 PUSH",
                                "message": "Congratulations ${consumer.forename} !",
                                "type": "PUSH",
                                "screen": "WALLET",
                                "rewardOffer": None,
                                "rewardTier": None,
                            },
                        ],
                    },
                ],
                "multipliers": [],
                "rewards": [
                    {
                        "pointValue": 1,
                        "offerKey": "410779c0bfc985e7f87f11408ffe195e",
                        "pushMessage": "Congratulations ${consumer.forename} !",
                        "autoTrigger": True,
                    },
                    {
                        "pointValue": 3,
                        "offerKey": "6e10c54986115b3fd3c8db020170a152",
                        "pushMessage": "Congratulations ${consumer.forename} !",
                        "autoTrigger": True,
                    },
                    {
                        "pointValue": 5,
                        "offerKey": "5f6f1572962eb7993aa3b3fb3d18ed57",
                        "pushMessage": "Congratulations ${consumer.forename} !",
                        "autoTrigger": True,
                    },
                ],
                "cardImageUrl": "https://demoimages.podifi.com/earn_some_tender_(1).jpg",
                "stampImageUrl": "https://demoimages.podifi.com/Slims.gif",
                "state": "PUBLISHED",
                "stateChangedon": "2023-06-19T14:33:02Z",
                "penultimatePush": "Just one more visit to go for your next reward! #Earnthatchicken 🍗",
                "test": False,
                "externalId": "1586247",
                "collectionType": "ANY",
                "autoEnroll": True,
                "description": "Earn great rewards with our NEW Slims Stamp Card!",
                "termsAndConditions": {
                    "termsAndConditionsKey": None,
                    "name": None,
                    "details": "- Please check your wallet for all offer codes",
                    "accountKey": None,
                    "etag": None,
                },
                "stampsPerRow": -1,
                "type": "STAMP",
                "favourite": False,
                "exclusive": False,
                "rulesetKey": "",
                "resourceType": "loyaltyScheme",
                "location": "",
                "locations": [],
                "national": True,
                "issuance": [
                    {"startTime": "00:00", "endTime": "23:59", "day": "sunday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "monday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "tuesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "wednesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "thursday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "friday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "saturday"},
                ],
                "publishedOn": "2023-06-19T14:33:02Z",
            },
            "objectives": [],
            "state": "DEFAULT",
        }
    ],
    "invites": [],
}

ADD_RESPONSE_VOUCHER_JSON_200 = {
    "configuration": {},
    "tags": [],
    "heroImages": [],
    "offers": [],
    "loyaltySchemes": [],
    "sites": [],
    "nearby": [],
    "welcomeImages": [],
    "menuImages": [],
    "wallet": [
        {
            "itemId": "99d007ce285943b5b9ab15628ff56898",
            "voucherCode": "874713319",
            "voucherExpiry": "2023-10-05T22:59:59Z",
            "passbookUrl": "https://demoapi.podifi.com/passbook/pass/39aae2ca579f4f0e989e26216562dafe/8eefe69678194a0a84802f9bd15c2ae4",  # noqa: E501
            "offer": {
                "modifiedDate": "2023-07-05T12:04:47Z",
                "name": "New Stamp 5 - Free Meal",
                "description": "You've completed your Slims 'Earn some tender' Stamp Card! Congratulations, get yourself a free meal on the house 😃\r\nHave 5 Tenders, 6 Wings or a Chicken Sandwich Meal, on us!",  # noqa: E501
                "amount": 0.0,
                "code": "",
                "start": "2023-06-18T23:00:00Z",
                "end": "2024-06-05T22:59:00Z",
                "siteGroupKeys": [],
                "offerKey": "5f6f1572962eb7993aa3b3fb3d18ed57",
                "multiple": False,
                "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                "publishedOn": "2023-06-19T14:30:14Z",
                "withdrawn": False,
                "testOffer": False,
                "imageUrl": "https://demoimages.podifi.com/images/6d625a6c3ddf479696f6f14cfe2cdf86/Free_Meal.jpg",
                "rewardOffer": True,
                "externalId": "1586246",
                "autoIssue": False,
                "advert": False,
                "type": "MONETARY",
                "termsAndConditions": {
                    "termsAndConditionsKey": "1dade57632b1b5ae067e00dc55d3f360",
                    "name": "New Stamp 5 - Free Meal",
                    "details": "Standard Terms and Conditions:\r\n- Offer valid for the dates shown\r\n- Offer Not Valid on Bank Holidays or Public Holidays (Delete as appropriate)\r\n- Not to be used in conjunction with any other offer (Delete as appropriate)\r\n- Only one voucher per transaction (Delete as appropriate)\r\n- Subject to availability (Delete as appropriate)\r\n- Valid for a maximum of (enter number) people (Delete as appropriate)\r\n- No cash Alternative (Delete as appropriate)\r\n- Valid on (enter items its valid on)",  # noqa: E501
                    "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                    "etag": "0",
                },
                "blackouts": {},
                "availability": {
                    "monday": [{"startTime": "00:00", "endTime": "23:59", "day": "monday"}],
                    "tuesday": [{"startTime": "00:00", "endTime": "23:59", "day": "tuesday"}],
                    "wednesday": [{"startTime": "00:00", "endTime": "23:59", "day": "wednesday"}],
                    "thursday": [{"startTime": "00:00", "endTime": "23:59", "day": "thursday"}],
                    "friday": [{"startTime": "00:00", "endTime": "23:59", "day": "friday"}],
                    "saturday": [{"startTime": "00:00", "endTime": "23:59", "day": "saturday"}],
                    "sunday": [{"startTime": "00:00", "endTime": "23:59", "day": "sunday"}],
                },
                "issuanceWindows": {
                    "monday": [{"startTime": "00:00", "endTime": "23:59", "day": "monday"}],
                    "tuesday": [{"startTime": "00:00", "endTime": "23:59", "day": "tuesday"}],
                    "wednesday": [{"startTime": "00:00", "endTime": "23:59", "day": "wednesday"}],
                    "thursday": [{"startTime": "00:00", "endTime": "23:59", "day": "thursday"}],
                    "friday": [{"startTime": "00:00", "endTime": "23:59", "day": "friday"}],
                    "saturday": [{"startTime": "00:00", "endTime": "23:59", "day": "saturday"}],
                    "sunday": [{"startTime": "00:00", "endTime": "23:59", "day": "sunday"}],
                },
                "tags": [
                    {
                        "name": "Bink",
                        "generic": False,
                        "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                        "tagKey": "b7b88147eead40fa883ce7591069cbf8",
                        "usernames": None,
                    }
                ],
                "useFavouriteSite": False,
                "favourite": False,
                "rulesetKey": "",
                "giftVoucher": False,
                "currencyCode": "",
                "objectives": [],
                "resourceType": "offer",
                "location": "",
                "issuance": [
                    {"startTime": "00:00", "endTime": "23:59", "day": "monday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "tuesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "wednesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "thursday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "friday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "saturday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "sunday"},
                ],
                "locations": [],
                "national": True,
            },
            "verificationRequired": False,
            "status": "AVAILABLE",
            "statusChangedDate": "2023-08-21T15:54:03Z",
            "objectives": [],
            "state": "DEFAULT",
        },
        {
            "itemId": "d7087f91aeec46e1a6dd6e3d0bc64546",
            "voucherCode": "416808122",
            "voucherStart": "2023-08-24T09:48:16Z",
            "voucherExpiry": "2023-10-08T22:59:59Z",
            "passbookUrl": "https://demoapi.podifi.com/passbook/pass/ad7898ef6fbe4903be4df89a0d0167c9/ecc658e9effd4dbd90aa59f871306e0b",  # noqa: E501
            "offer": {
                "modifiedDate": "2023-07-05T12:04:29Z",
                "name": "New Stamp 1 - 3 Free Wings",
                "description": "3 Free Wings New App Loyalty",
                "amount": 0.0,
                "code": "",
                "start": "2023-06-18T23:00:00Z",
                "end": "2024-06-05T22:59:00Z",
                "siteGroupKeys": [],
                "offerKey": "410779c0bfc985e7f87f11408ffe195e",
                "multiple": False,
                "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                "publishedOn": "2023-06-19T14:30:09Z",
                "withdrawn": False,
                "testOffer": False,
                "imageUrl": "https://demoimages.podifi.com/images/6d625a6c3ddf479696f6f14cfe2cdf86/free_3_wings.jpg",
                "rewardOffer": True,
                "externalId": "1586243",
                "autoIssue": False,
                "advert": False,
                "type": "MONETARY",
                "termsAndConditions": {
                    "termsAndConditionsKey": "8eefc633110ec7ee081efe917d8d3405",
                    "name": "New Stamp 1 - 3 Free Wings",
                    "details": "Standard Terms and Conditions:\r\n- Offer valid for the dates shown\r\n- Offer Not Valid on Bank Holidays or Public Holidays (Delete as appropriate)\r\n- Not to be used in conjunction with any other offer (Delete as appropriate)\r\n- Only one voucher per transaction (Delete as appropriate)\r\n- Subject to availability (Delete as appropriate)\r\n- Valid for a maximum of (enter number) people (Delete as appropriate)\r\n- No cash Alternative (Delete as appropriate)\r\n- Valid on (enter items its valid on)",  # noqa: E501
                    "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                    "etag": "0",
                },
                "blackouts": {},
                "availability": {
                    "monday": [{"startTime": "00:00", "endTime": "23:59", "day": "monday"}],
                    "tuesday": [{"startTime": "00:00", "endTime": "23:59", "day": "tuesday"}],
                    "wednesday": [{"startTime": "00:00", "endTime": "23:59", "day": "wednesday"}],
                    "thursday": [{"startTime": "00:00", "endTime": "23:59", "day": "thursday"}],
                    "friday": [{"startTime": "00:00", "endTime": "23:59", "day": "friday"}],
                    "saturday": [{"startTime": "00:00", "endTime": "23:59", "day": "saturday"}],
                    "sunday": [{"startTime": "00:00", "endTime": "23:59", "day": "sunday"}],
                },
                "issuanceWindows": {
                    "monday": [{"startTime": "00:00", "endTime": "23:59", "day": "monday"}],
                    "tuesday": [{"startTime": "00:00", "endTime": "23:59", "day": "tuesday"}],
                    "wednesday": [{"startTime": "00:00", "endTime": "23:59", "day": "wednesday"}],
                    "thursday": [{"startTime": "00:00", "endTime": "23:59", "day": "thursday"}],
                    "friday": [{"startTime": "00:00", "endTime": "23:59", "day": "friday"}],
                    "saturday": [{"startTime": "00:00", "endTime": "23:59", "day": "saturday"}],
                    "sunday": [{"startTime": "00:00", "endTime": "23:59", "day": "sunday"}],
                },
                "tags": [
                    {
                        "name": "Bink",
                        "generic": False,
                        "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                        "tagKey": "b7b88147eead40fa883ce7591069cbf8",
                        "usernames": None,
                    }
                ],
                "useFavouriteSite": False,
                "favourite": False,
                "rulesetKey": "",
                "giftVoucher": False,
                "currencyCode": "",
                "objectives": [],
                "resourceType": "offer",
                "location": "",
                "issuance": [
                    {"startTime": "00:00", "endTime": "23:59", "day": "monday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "tuesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "wednesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "thursday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "friday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "saturday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "sunday"},
                ],
                "locations": [],
                "national": True,
            },
            "verificationRequired": False,
            "status": "AVAILABLE",
            "statusChangedDate": "2023-08-24T09:48:16Z",
            "objectives": [],
            "state": "DEFAULT",
        },
        {
            "itemId": "65336de42462493dbeaabfefd259a5d1",
            "voucherCode": "847342605",
            "voucherStart": "2023-09-04T09:24:41Z",
            "voucherExpiry": "2023-10-19T22:59:59Z",
            "passbookUrl": "https://demoapi.podifi.com/passbook/pass/d9a542cfd166418ab38eb2d353b32a9e/62743eda9b33423d91a4a10644354597",  # noqa: E501
            "offer": {
                "modifiedDate": "2023-07-05T12:04:36Z",
                "name": "New Stamp 3 - Free Shake",
                "description": "Stamp 3 - Free Shake",
                "amount": 0.0,
                "code": "",
                "start": "2023-06-18T23:00:00Z",
                "end": "2024-06-05T22:59:00Z",
                "siteGroupKeys": [],
                "offerKey": "6e10c54986115b3fd3c8db020170a152",
                "multiple": False,
                "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                "publishedOn": "2023-06-19T14:30:12Z",
                "withdrawn": False,
                "testOffer": False,
                "imageUrl": "https://demoimages.podifi.com/images/6d625a6c3ddf479696f6f14cfe2cdf86/Free_Shake.jpg",
                "rewardOffer": True,
                "externalId": "1586244",
                "autoIssue": False,
                "advert": False,
                "type": "MONETARY",
                "termsAndConditions": {
                    "termsAndConditionsKey": "22feba02694029921f78f590a978c99e",
                    "name": "Stamp 3 - Free Shake",
                    "details": "Standard Terms and Conditions:\r\n- Offer valid for the dates shown\r\n- Offer Not Valid on Bank Holidays or Public Holidays (Delete as appropriate)\r\n- Not to be used in conjunction with any other offer (Delete as appropriate)\r\n- Only one voucher per transaction (Delete as appropriate)\r\n- Subject to availability (Delete as appropriate)\r\n- Valid for a maximum of (enter number) people (Delete as appropriate)\r\n- No cash Alternative (Delete as appropriate)\r\n- Valid on (enter items its valid on)",  # noqa: E501
                    "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                    "etag": "0",
                },
                "blackouts": {},
                "availability": {
                    "monday": [{"startTime": "00:00", "endTime": "23:59", "day": "monday"}],
                    "tuesday": [{"startTime": "00:00", "endTime": "23:59", "day": "tuesday"}],
                    "wednesday": [{"startTime": "00:00", "endTime": "23:59", "day": "wednesday"}],
                    "thursday": [{"startTime": "00:00", "endTime": "23:59", "day": "thursday"}],
                    "friday": [{"startTime": "00:00", "endTime": "23:59", "day": "friday"}],
                    "saturday": [{"startTime": "00:00", "endTime": "23:59", "day": "saturday"}],
                    "sunday": [{"startTime": "00:00", "endTime": "23:59", "day": "sunday"}],
                },
                "issuanceWindows": {
                    "monday": [{"startTime": "00:00", "endTime": "23:59", "day": "monday"}],
                    "tuesday": [{"startTime": "00:00", "endTime": "23:59", "day": "tuesday"}],
                    "wednesday": [{"startTime": "00:00", "endTime": "23:59", "day": "wednesday"}],
                    "thursday": [{"startTime": "00:00", "endTime": "23:59", "day": "thursday"}],
                    "friday": [{"startTime": "00:00", "endTime": "23:59", "day": "friday"}],
                    "saturday": [{"startTime": "00:00", "endTime": "23:59", "day": "saturday"}],
                    "sunday": [{"startTime": "00:00", "endTime": "23:59", "day": "sunday"}],
                },
                "tags": [
                    {
                        "name": "Bink",
                        "generic": False,
                        "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                        "tagKey": "b7b88147eead40fa883ce7591069cbf8",
                        "usernames": None,
                    }
                ],
                "useFavouriteSite": False,
                "favourite": False,
                "rulesetKey": "",
                "giftVoucher": False,
                "currencyCode": "",
                "objectives": [],
                "resourceType": "offer",
                "location": "",
                "issuance": [
                    {"startTime": "00:00", "endTime": "23:59", "day": "monday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "tuesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "wednesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "thursday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "friday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "saturday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "sunday"},
                ],
                "locations": [],
                "national": True,
            },
            "verificationRequired": False,
            "status": "AVAILABLE",
            "statusChangedDate": "2023-09-04T09:24:41Z",
            "objectives": [],
            "state": "DEFAULT",
        },
        {
            "itemId": "2b9811f91c4545b7877e78f663b9bb9b",
            "voucherCode": "376819964",
            "voucherExpiry": "2024-08-20T22:59:59Z",
            "cardPoints": 4,
            "passbookUrl": "https://demoapi.podifi.com/passbook/pass/b148a148ec674cd0bcc412f0301a5c11/39ae7b1871e8439583404dcd1559012b",  # noqa: E501
            "loyaltyScheme": {
                "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                "accountName": "Eagle Eye UAT",
                "loyaltySchemeKey": "2b9811f91c4545b7877e78f663b9bb9b",
                "name": "New Stamp Loyalty",
                "tags": [
                    {
                        "name": "Bink",
                        "generic": False,
                        "accountKey": "6d625a6c3ddf479696f6f14cfe2cdf86",
                        "tagKey": "b7b88147eead40fa883ce7591069cbf8",
                        "usernames": None,
                    }
                ],
                "defaultPoints": 1,
                "defaultFrequency": 1,
                "defaultFrequencyType": "DAY",
                "rewardTiers": [
                    {
                        "rewardTierKey": "b6b8c4c93cef4461b3dee2fabc606339",
                        "name": "New Stamp Loyalty 1",
                        "type": "REPEAT",
                        "pointValue": 1,
                        "autoTrigger": True,
                        "loyaltyScheme": None,
                        "rewardEvents": [
                            {
                                "rewardEventKey": "d9142d1fcc26461cbd952b17c66e7429",
                                "name": "New Stamp Loyalty 1 PUSH",
                                "message": "Congratulations ${consumer.forename} ! Your latest reward is waiting in your app wallet #Slimthusiast 🍗",  # noqa: E501
                                "type": "PUSH",
                                "screen": "WALLET",
                                "rewardOffer": None,
                                "rewardTier": None,
                            },
                            {
                                "rewardEventKey": "ea5761530664449c80cc51f3fc601d89",
                                "name": "New Stamp Loyalty 1 OFFER",
                                "message": None,
                                "type": "OFFER",
                                "screen": None,
                                "rewardOffer": {
                                    "rewardOfferKey": "410779c0bfc985e7f87f11408ffe195e",
                                    "name": "New Stamp 1 - 3 Free Wings",
                                    "stampImageUrl": None,
                                },
                                "rewardTier": None,
                            },
                        ],
                    },
                    {
                        "rewardTierKey": "d1ba89995db245fab25a78ac8d1a4ee4",
                        "name": "New Stamp Loyalty 3",
                        "type": "REPEAT",
                        "pointValue": 3,
                        "autoTrigger": True,
                        "loyaltyScheme": None,
                        "rewardEvents": [
                            {
                                "rewardEventKey": "774dfdf598484519b838caa758a7e38f",
                                "name": "New Stamp Loyalty 3 OFFER",
                                "message": None,
                                "type": "OFFER",
                                "screen": None,
                                "rewardOffer": {
                                    "rewardOfferKey": "6e10c54986115b3fd3c8db020170a152",
                                    "name": "New Stamp 3 - Free Shake",
                                    "stampImageUrl": None,
                                },
                                "rewardTier": None,
                            },
                            {
                                "rewardEventKey": "a0482bd9eba440b4b40cf1366a68ca6a",
                                "name": "New Stamp Loyalty 3 PUSH",
                                "message": "Congratulations ${consumer.forename} ! Your latest reward is waiting in your app wallet #Slimthusiast 🍗",  # noqa: E501
                                "type": "PUSH",
                                "screen": "WALLET",
                                "rewardOffer": None,
                                "rewardTier": None,
                            },
                        ],
                    },
                    {
                        "rewardTierKey": "eca485ffd3214bf4981cda15d9440592",
                        "name": "New Stamp Loyalty 5",
                        "type": "REPEAT",
                        "pointValue": 5,
                        "autoTrigger": True,
                        "loyaltyScheme": None,
                        "rewardEvents": [
                            {
                                "rewardEventKey": "ab8997c099414326980de3cccabf1ee9",
                                "name": "New Stamp Loyalty 5 OFFER",
                                "message": None,
                                "type": "OFFER",
                                "screen": None,
                                "rewardOffer": {
                                    "rewardOfferKey": "5f6f1572962eb7993aa3b3fb3d18ed57",
                                    "name": "New Stamp 5 - Free Meal",
                                    "stampImageUrl": None,
                                },
                                "rewardTier": None,
                            },
                            {
                                "rewardEventKey": "755d53b697154f1a83e4b35e633fda05",
                                "name": "New Stamp Loyalty 5 PUSH",
                                "message": "Congratulations ${consumer.forename} ! Your latest reward is waiting in your app wallet #Slimthusiast 🍗",  # noqa: E501
                                "type": "PUSH",
                                "screen": "WALLET",
                                "rewardOffer": None,
                                "rewardTier": None,
                            },
                        ],
                    },
                ],
                "multipliers": [],
                "rewards": [
                    {
                        "pointValue": 1,
                        "offerKey": "410779c0bfc985e7f87f11408ffe195e",
                        "pushMessage": "Congratulations ${consumer.forename} ! Your latest reward is waiting in your app wallet #Slimthusiast 🍗",  # noqa: E501
                        "autoTrigger": True,
                    },
                    {
                        "pointValue": 3,
                        "offerKey": "6e10c54986115b3fd3c8db020170a152",
                        "pushMessage": "Congratulations ${consumer.forename} ! Your latest reward is waiting in your app wallet #Slimthusiast 🍗",  # noqa: E501
                        "autoTrigger": True,
                    },
                    {
                        "pointValue": 5,
                        "offerKey": "5f6f1572962eb7993aa3b3fb3d18ed57",
                        "pushMessage": "Congratulations ${consumer.forename} ! Your latest reward is waiting in your app wallet #Slimthusiast 🍗",  # noqa: E501
                        "autoTrigger": True,
                    },
                ],
                "cardImageUrl": "https://demoimages.podifi.com/images/6d625a6c3ddf479696f6f14cfe2cdf86/card/earn_some_tender_(1).jpg",  # noqa: E501
                "stampImageUrl": "https://demoimages.podifi.com/images/6d625a6c3ddf479696f6f14cfe2cdf86/stamp/Slims.gif",  # noqa: E501
                "state": "PUBLISHED",
                "stateChangedon": "2023-06-19T14:33:02Z",
                "penultimatePush": "Just one more visit to go for your next reward! #Earnthatchicken 🍗",
                "test": False,
                "externalId": "1586247",
                "collectionType": "ANY",
                "autoEnroll": True,
                "description": "Earn great rewards with our NEW Slims Stamp Card! Starting Monday 5th June.\r\nEarn Loyalty Rewards Quicker.",  # noqa: E501
                "termsAndConditions": {
                    "termsAndConditionsKey": None,
                    "name": None,
                    "details": "- Please check your wallet for all offer codes\r\n- Maximum of one stamp per day\r\n- Purchase of a meal is required to earn  \r\nstamps\r\n- Stamp card expires after 365 Days from start date\r\n- We reserve the right to withdraw this offer at any time\r\n- Offer for Free Milkshake does not apply in Slim Chickens Selly Oak \r\n- Stamps have no cash value and cannot be transferred\r\n- Valid only in Slim Chickens in the UK\r\n- Reward stamps may take upto 24hrs to enter your wallet\r\n- You have 45 Days to redeem all stamp offers &amp; then they will expire.\r\n- Weekly App Offer deals may be subject to availability across restaurants. \r\n- Weekly App Offers can only be sent if you have opened the app within the last 30 days before the offer date.\r\n- Your closest store on the app doesn't mean this is the closest store to use an offer.",  # noqa: E501
                    "accountKey": None,
                    "etag": None,
                },
                "stampsPerRow": -1,
                "type": "STAMP",
                "favourite": False,
                "exclusive": False,
                "rulesetKey": "",
                "resourceType": "loyaltyScheme",
                "location": "",
                "locations": [],
                "national": True,
                "issuance": [
                    {"startTime": "00:00", "endTime": "23:59", "day": "sunday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "monday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "tuesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "wednesday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "thursday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "friday"},
                    {"startTime": "00:00", "endTime": "23:59", "day": "saturday"},
                ],
                "publishedOn": "2023-06-19T14:33:02Z",
            },
            "objectives": [],
            "state": "DEFAULT",
        },
    ],
    "invites": [],
}


JOIN_RESPONSE_JSON_200 = {
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
        "attributes": {"optin2": "True"},
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

    def test_configure_outbound_auth(self):
        self.slim_chickens.credentials = {
            "username": "janedoe123@test.com",
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "janedoe@test.com",
            "password": "fakepass?",
            "dob": "1979-05-10T00:00:00Z",
            "attributes": {"optin2": "True"},
        }
        self.slim_chickens._configure_outbound_auth(username="testeruser", password="test-pass")
        auth_header = self.slim_chickens.headers["Authorization"]
        self.assertTrue(auth_header.startswith("Basic "))

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    def test_join_account_already_exists(self, mock_requests_session):
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
            "attributes": {"optin2": "True"},
        }
        self.slim_chickens.outbound_security["channel_key"] = "testing-key"
        resp = self.slim_chickens._account_already_exists()

        self.assertEqual(resp, False)

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    def test_join_account_already_exists_error(self, mock_requests_session):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"
        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(JOIN_RESPONSE_JSON_200),
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
            "attributes": {"optin2": "True"},
        }
        self.slim_chickens.outbound_security["channel_key"] = "testing-key"
        resp = self.slim_chickens._account_already_exists()
        self.assertEqual(resp, True)

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_create_account_happy_path(self, mock_signal, mock_requests_session):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"

        def custom_response(request, uri, headers):
            if custom_response.counter == 0:
                custom_response.counter += 1
                return (HTTPStatus.CONFLICT, headers, json.dumps({"errors": {"1055": "Password is required"}}))
            else:
                return (HTTPStatus.OK, headers, json.dumps(JOIN_RESPONSE_JSON_200))

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
        self.assertEqual(
            self.slim_chickens.credentials["merchant_identifier"], JOIN_RESPONSE_JSON_200["consumer"]["email"]
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("join-success"),
            call().send(self.slim_chickens, channel=self.slim_chickens.channel, slug=self.slim_chickens.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    def test_create_account_error_account_holder_exists(self, mock_requests_session):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"

        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(JOIN_RESPONSE_JSON_200),
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
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_create_account_unknown_error(self, mock_signal, mock_requests_session):
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
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_create_account_error_checking_if_account_exists(self, mock_signal, mock_requests_session):
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
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_create_account_weak_password_error(self, mock_signal, mock_requests_session):
        url = f"{self.slim_chickens.base_url}core/account/123/consumer"

        def custom_response(request, uri, headers):
            if custom_response.counter == 0:
                custom_response.counter += 1
                return HTTPStatus.CONFLICT, headers, json.dumps({"errors": {"1055": "Password is required"}})
            else:
                return HTTPStatus.CONFLICT, headers, json.dumps({"errors": {"1154": "Password is too weak"}})

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
        with self.assertRaises(WeakPasswordError) as e:
            self.slim_chickens.join()
        expected_calls = [  # The expected call stack for signal, in order
            call("join-fail"),
            call().send(self.slim_chickens, channel=self.slim_chickens.channel, slug=self.slim_chickens.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)
        self.assertEqual(e.exception.name, "Join password too weak")
        self.assertEqual(e.exception.code, 905)

    @httpretty.activate
    def test_balance_happy_path(self):
        self.slim_chickens.balance_vouchers = ADD_RESPONSE_NO_VOUCHER_JSON_200["wallet"]
        resp = self.slim_chickens.balance()
        self.assertEqual(
            resp,
            Balance(
                points=Decimal("0"),
                value=Decimal("0"),
                value_label="",
                reward_tier=0,
                balance=None,
                vouchers=[
                    Voucher(
                        state="inprogress",
                        issue_date=1687185182,
                        redeem_date=None,
                        expiry_date=1724194799,
                        code="747163178",
                        value=Decimal("0"),
                        target_value=None,
                        conversion_date=None,
                    )
                ],
            ),
        )

    @httpretty.activate
    def test_balance_happy_path_with_vouchers(self):
        self.slim_chickens.balance_vouchers = ADD_RESPONSE_VOUCHER_JSON_200["wallet"]
        resp = self.slim_chickens.balance()
        self.assertEqual(
            resp,
            Balance(
                points=Decimal("4"),
                value=Decimal("0"),
                value_label="",
                reward_tier=0,
                balance=None,
                vouchers=[
                    Voucher(
                        state="inprogress",
                        issue_date=1687185182,
                        redeem_date=None,
                        expiry_date=1724194799,
                        code="376819964",
                        value=Decimal("4"),
                        target_value=None,
                        conversion_date=None,
                    ),
                    Voucher(
                        state="issued",
                        issue_date=1687129200,
                        redeem_date=None,
                        expiry_date=1696546799,
                        code="----------",
                        value=None,
                        target_value=None,
                        conversion_date=None,
                    ),
                    Voucher(
                        state="issued",
                        issue_date=1687129200,
                        redeem_date=None,
                        expiry_date=1696805999,
                        code="----------",
                        value=None,
                        target_value=None,
                        conversion_date=None,
                    ),
                    Voucher(
                        state="issued",
                        issue_date=1687129200,
                        redeem_date=None,
                        expiry_date=1697756399,
                        code="----------",
                        value=None,
                        target_value=None,
                        conversion_date=None,
                    ),
                ],
            ),
        )

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_login_happy_path(self, mock_signal, mock_requests_session):
        url = f"{self.slim_chickens.base_url}search"

        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(ADD_RESPONSE_NO_VOUCHER_JSON_200),
                    status=HTTPStatus.OK,
                )
            ],
        )
        self.slim_chickens.outbound_security["user_name"] = "testuser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        resp = self.slim_chickens.login()
        self.assertEqual(resp, None)
        self.assertEqual(self.slim_chickens.balance_vouchers, ADD_RESPONSE_NO_VOUCHER_JSON_200["wallet"])
        expected_calls = [  # The expected call stack for signal, in order
            call("log-in-success"),
            call().send(self.slim_chickens, slug=self.slim_chickens.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_login_bad_credentials(self, mock_signal, mock_requests_session):
        url = f"{self.slim_chickens.base_url}search"
        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.UNAUTHORIZED,
            responses=[
                httpretty.Response(
                    body=json.dumps({"errors": {"0004": "Bad Credentials"}}),
                    status=HTTPStatus.UNAUTHORIZED,
                )
            ],
        )
        self.slim_chickens.outbound_security["user_name"] = "baduser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        # Journey type greater than zero = not a join
        self.slim_chickens.user_info["journey_type"] = 1
        with self.assertRaises(Exception) as e:
            self.slim_chickens.login()
        self.assertEqual(e.exception.name, "Invalid credentials")
        self.assertEqual(e.exception.code, 403)
        expected_calls = [  # The expected call stack for signal, in order
            call("log-in-fail"),
            call().send(self.slim_chickens, slug=self.slim_chickens.scheme_slug),
        ]
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.slimchickens.handle_failed_login")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_login_balance_request_from_join_401(self, mock_signal, mock_requests_session, mock_handle_failed_login):
        url = f"{self.slim_chickens.base_url}search"

        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({}),
                    status=401,
                )
            ],
        )

        self.slim_chickens.outbound_security["user_name"] = "testuser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        # Journey type greater than zero = not a join
        self.slim_chickens.user_info["journey_type"] = 1
        self.slim_chickens.user_info["from_join"] = True

        resp = self.slim_chickens.login_balance_request()

        self.assertEqual(resp, None)
        mock_handle_failed_login.assert_called()

    @httpretty.activate
    @mock.patch("app.agents.slimchickens.handle_failed_login")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.slimchickens.signal", autospec=True)
    def test_login_balance_request_from_hermes_401(self, mock_signal, mock_requests_session, mock_handle_failed_login):
        url = f"{self.slim_chickens.base_url}search"

        httpretty.register_uri(
            httpretty.POST,
            uri=url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({}),
                    status=401,
                )
            ],
        )

        self.slim_chickens.outbound_security["user_name"] = "testuser"
        self.slim_chickens.outbound_security["password"] = "password1"
        self.slim_chickens.outbound_security["channel_key"] = "1eceec2173454776b7d9a0f4a307c94b"
        self.slim_chickens.outbound_security["account_key"] = "123"
        # Journey type greater than zero = not a join
        self.slim_chickens.user_info["journey_type"] = 1

        with self.assertRaises(StatusLoginFailedError) as e:
            self.slim_chickens.login_balance_request()
        self.assertEqual(e.exception.name, "Invalid credentials")
        mock_handle_failed_login.assert_not_called()
