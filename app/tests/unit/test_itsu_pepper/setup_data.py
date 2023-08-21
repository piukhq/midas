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
EXPECTED_PEPPER_ID = "64d498865e2b5f4d03c2a70e"
EXPECTED_CARD_NUMBER = "1105763052"

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
        {"provider": "EMAIL", "id": "test_mm_1@bink.com", "token": "userspassword1"},
    ],
    "hasAgreedToShareData": True,
    "hasAgreedToReceiveMarketing": True,
}


EXPECTED_ITSU_PEPPER_HEADERS = {
    "Content-Type": "application/json",
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
        "email": "test_mm_1@bink.com",
        "password": "userspassword1",
        "consents": [{"id": 11738, "slug": "email_marketing", "value": True, "created_on": "1996-09-26T00:00:00"}],
    },
}

MESSAGE = {
    "loyalty_plan": "itsu",
    "message_uid": "32799979732e2",
    "request_id": 234,
}
