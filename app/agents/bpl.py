from app.agents.base import ApiMiner
from app.configuration import Configuration
from app.agents.exceptions import (
    AgentError, LoginError,
    GENERAL_ERROR,
    ACCOUNT_ALREADY_EXISTS,
    STATUS_REGISTRATION_FAILED
)
from app.encryption import hash_ids


class Trenette(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]["token"]
        self.callback_url = config.callback_url
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.headers = {"bpl-user-channel": self.channel, "Authorization": f"Token {self.auth}"}
        self.errors = {
            GENERAL_ERROR: ["MALFORMED_REQUEST", "INVALID_TOKEN", "INVALID_RETAILER", "FORBIDDEN"],
            ACCOUNT_ALREADY_EXISTS: ["ACCOUNT_EXISTS"],
            STATUS_REGISTRATION_FAILED: ["MISSING_FIELDS", "VALIDATION_FAILED"]
        }

    def register(self, credentials):
        payload = {
            "credentials": credentials,
            "marketing_preferences": [],
            "callback_url": self.callback_url,
            "third_party_identifier": hash_ids.encode(self.user_info['scheme_account_id']),
        }

        try:
            self.make_request(self.base_url, method="post", json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json()["error"], unhandled_exception_code=GENERAL_ERROR)
        else:
            self.expecting_callback = True

    def login(self, credentials):
        self.credentials = credentials
        message_uid = str(uuid4())
        record_uid = hash_ids.encode(self.scheme_id)
        integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()
        card_number = credentials['card_number']
        journey = self.user_info['journey_type']
        journey_type = Configuration.JOIN_HANDLER if journey == 0 else Configuration.VALIDATE_HANDLER

        if "merchant_identifier" not in credentials:
            endpoint = f"/v1/list/query_item/{self.RETAILER_ID}/assets/membership/token/{card_number}"

            membership_data = self._get_membership_response(endpoint=endpoint, journey_type=journey_type,
                                                            from_login=True,
                                                            integration_service=integration_service,
                                                            message_uid=message_uid,
                                                            record_uid=record_uid)


            # TODO: do we actually need all three of these
            self.credentials["merchant_identifier"] = membership_data["uuid"]
            self.identifier = {"merchant_identifier": membership_data["uuid"]}
            self.user_info["credentials"].update(self.identifier)
