from soteria.configuration import Configuration

SECRET_ACTEOL_JOIN = [{"value": {"password": "MBX1pmb2uxh5vzc@ucp", "username": "acteol.test@bink.com"}}]

MERCHANT_URL = "https://atreemouat.xxxitsucomms.co.uk"

CONFIG_JSON_STONEGATE_BODY = {
    "merchant_url": MERCHANT_URL,
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
