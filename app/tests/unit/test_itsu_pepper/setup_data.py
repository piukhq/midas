from soteria.configuration import Configuration

SECRET_ITSU_ACTEOL_JOIN = [{"value": {"password": "MBX1pmb2uxh5vzc@ucp", "username": "acteol.itsu.test@bink.com"}}]

SECRET_ITSU_PEPPER_JOIN = [{"value": {"authorization": "627b9ee5c0aebf0e54a3b3dc", "application-id": "bink-03dxtvc8"}}]

CONFIG_JSON_ITSU_BODY = {
    "merchant_url": "https://atreemouat.xxxitsucomms.co.uk/",
    "retry_limit": 3,
    "log_level": 0,
    "callback_url": "",
    "country": "uk",
    "security_credentials": {
        "inbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": 3,
                    "storage_key": "a_storage_key",
                    "value": {"password": "paSSword", "username": "username@bink.com"},
                },
            ],
        },
        "outbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": 3,
                    "storage_key": "a_storage_key",
                    "value": {"password": "paSSword", "username": "username@bink.com"},
                },
            ],
        },
    },
}

PEPPER_MERCHANT_URL = "https://beta-api.xxxpepperhq.com"
EXPECTED_PEPPER_ID = "64e34958d8623591d87cb554"
EXPECTED_CARD_NUMBER = "7425763994"
USER_EMAIL = "test_mm_3@bink.com"
USER_PASSWORD = "userspassword"

CONFIG_JSON_PEPPER_BODY = {
    "merchant_url": PEPPER_MERCHANT_URL,
    "retry_limit": 3,
    "log_level": 0,
    "callback_url": "",
    "country": "uk",
    "security_credentials": {
        "inbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": 3,
                    "storage_key": "a_pepper_storage_key",
                    "value": {"password": "paSSword", "username": "username@bink.com"},
                },
            ],
        },
        "outbound": {
            "service": Configuration.OAUTH_SECURITY,
            "credentials": [
                {
                    "credential_type": 3,
                    "storage_key": "a_pepper_storage_key",
                    "value": {"password": "paSSword", "username": "username@bink.com"},
                },
            ],
        },
    },
}

EXPECTED_PEPPER_PAYLOAD = {
    "firstName": "Fake",
    "lastName": "Name",
    "credentials": [
        {"provider": "EMAIL", "id": USER_EMAIL, "token": USER_PASSWORD},
    ],
    "hasAgreedToShareData": True,
    "hasAgreedToReceiveMarketing": True,
}

EXPECTED_ACCOUNT_EXISTS_RESPONSE = {
    "code": "Validation",
    "message": f"{USER_EMAIL} is already associated with an account",
}

EXPECTED_ACCOUNT_SETUP_RESPONSE_NO_USER_NUMBER = {
    "_id": EXPECTED_PEPPER_ID,
    "tenantId": "627b9ee450c8850d3b5bc30b",
    "firstName": "Fake",
    "lastName": "Name",
    "favouriteProducts": [],
    "subscribed": True,
    "roles": ["USER"],
    "demo": False,
    "points": 2,
    "balance": 0,
    "defaultTip": None,
    "hasPaymentCard": False,
    "hasProfilePhoto": False,
    "contacts": [],
    "favouriteLocations": [],
    "primaryPlatform": "UNKNOWN",
    "reviewCandidate": "false",
    "isRegisteredForPushNotifications": False,
    "hasAgreedToShareData": True,
    "hasAgreedToReceiveMarketing": True,
    "deleted": False,
    "addresses": [],
    "state": "ACTIVE",
    "fullName": "Fake Name",
    "created": "2023-08-21T11:14:07.036Z",
    "updatedAt": "2023-08-21T11:14:07.036Z",
    "loyaltyProvider": "ATREEMO",
    "additionalInformation": [],
    "id": EXPECTED_PEPPER_ID,
}

EXPECTED_ACCOUNT_SETUP_RESPONSE_WITH_USER_NUMBER = {
    "_id": EXPECTED_PEPPER_ID,
    "tenantId": "627b9ee450c8850d3b5bc30b",
    "firstName": "Fake",
    "lastName": "Name",
    "favouriteProducts": [],
    "subscribed": True,
    "roles": ["USER"],
    "demo": False,
    "points": 2,
    "balance": 0,
    "defaultTip": None,
    "hasPaymentCard": False,
    "hasProfilePhoto": False,
    "contacts": [],
    "favouriteLocations": [],
    "primaryPlatform": "UNKNOWN",
    "reviewCandidate": "false",
    "isRegisteredForPushNotifications": False,
    "hasAgreedToShareData": True,
    "hasAgreedToReceiveMarketing": True,
    "deleted": False,
    "addresses": [],
    "state": "ACTIVE",
    "fullName": "Fake Name",
    "created": "2023-08-21T11:24:09.028Z",
    "updatedAt": "2023-08-21T11:24:09.651Z",
    "loyaltyProvider": "ATREEMO",
    "externalLoyaltyId": EXPECTED_PEPPER_ID,
    "externalLoyaltyMemberNumber": EXPECTED_CARD_NUMBER,
    "additionalInformation": [],
    "id": EXPECTED_PEPPER_ID,
}

EXPECTED_USER_LOOKUP_RESPONSE = {
    "items": [
        {
            "_id": EXPECTED_PEPPER_ID,
            "tenantId": "627b9ee450c8850d3b5bc30b",
            "firstName": "Fake",
            "lastName": "Name",
            "subscribed": True,
            "roles": ["USER"],
            "defaultTip": None,
            "hasPaymentCard": False,
            "hasProfilePhoto": False,
            "contacts": [],
            "primaryPlatform": "UNKNOWN",
            "isRegisteredForPushNotifications": False,
            "hasAgreedToShareData": True,
            "hasAgreedToReceiveMarketing": True,
            "deleted": False,
            "state": "ACTIVE",
            "fullName": "Fake Name",
            "created": "2023-08-21T11:24:09.028Z",
            "updatedAt": "2023-08-21T11:24:09.651Z",
            "externalLoyaltyId": EXPECTED_PEPPER_ID,
            "loyaltyProvider": "ATREEMO",
            "additionalInformation": [],
            "id": EXPECTED_PEPPER_ID,
        }
    ],
    "page": {"count": 1, "limit": 3, "startKey": "eyJfaWQiOiI2NGUzNDk1OGQ4NjIzNTkxZDg3Y2I1NTQifQ"},
}

EXPECTED_USER_LOOKUP_UNKNOWN_RESPONSE = {"items": [], "page": {"count": 0, "limit": 3}}


EXPECTED_CARD_NUMBER_RESPONSE = {
    "_id": EXPECTED_PEPPER_ID,
    "tenantId": "627b9ee450c8850d3b5bc30b",
    "firstName": "Fake",
    "lastName": "Name",
    "favouriteProducts": [],
    "subscribed": True,
    "roles": ["USER"],
    "demo": False,
    "points": 2,
    "balance": 0,
    "defaultTip": None,
    "hasPaymentCard": False,
    "hasProfilePhoto": False,
    "contacts": [],
    "favouriteLocations": [],
    "primaryPlatform": "UNKNOWN",
    "reviewCandidate": "false",
    "isRegisteredForPushNotifications": False,
    "hasAgreedToShareData": True,
    "hasAgreedToReceiveMarketing": True,
    "deleted": False,
    "addresses": [],
    "state": "ACTIVE",
    "fullName": "Fake Name",
    "created": "2023-08-21T11:24:09.028Z",
    "updatedAt": "2023-08-21T11:24:09.651Z",
    "externalLoyaltyId": EXPECTED_PEPPER_ID,
    "externalLoyaltyMemberNumber": EXPECTED_CARD_NUMBER,
    "loyaltyProvider": "ATREEMO",
    "additionalInformation": [],
    "id": EXPECTED_PEPPER_ID,
}


EXPECTED_ITSU_PEPPER_HEADERS = {
    "Authorization": "Token 627b9ee5c0aebf0e54a3b3dc",
    "x-api-version": "10",
    "x-application-id": "bink-03dxtvc8",
    "x-client-platform": "BINK",
}

USER_INFO = {
    "scheme_account_id": 1235,
    "channel": "test",
    "journey_type": Configuration.JOIN_HANDLER,
    "credentials": {
        "first_name": "Fake",
        "last_name": "Name",
        "email": USER_EMAIL,
        "password": USER_PASSWORD,
        "consents": [{"id": 11738, "slug": "email_marketing", "value": True, "created_on": "1996-09-26T00:00:00"}],
    },
}

MESSAGE = {
    "loyalty_plan": "itsu",
    "message_uid": "32799979732e2",
    "request_id": 234,
}
