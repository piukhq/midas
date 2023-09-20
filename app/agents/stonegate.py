from urllib.parse import urlencode, urljoin

import argon2
from blinker import signal
from soteria.configuration import Configuration

from app.agents.acteol import Acteol
from app.agents.schemas import Balance, Transaction
from app.exceptions import AccountAlreadyExistsError, BaseError, JoinError

hasher = argon2.PasswordHasher()


class Stonegate(Acteol):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.oauth_token_timeout = 75600  # n_seconds in 21 hours
        self.integration_service = "SYNC"

    def get_auth_url_and_payload(self):
        url = urljoin(self.base_url, "token")
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "grant_type": "password",
            "username": self.outbound_security_credentials["username"],
            "password": self.outbound_security_credentials["password"],
        }
        payload = urlencode(payload)
        return url, payload

    def authenticate(self):
        if self.outbound_auth_service == Configuration.OPEN_AUTH_SECURITY:
            return
        if self.outbound_auth_service == Configuration.OAUTH_SECURITY:
            self._oauth_authentication()
        self.headers["Content-Type"] = "application/json"

    def _check_customer_exists(self, send_audit: bool = False) -> bool:
        api_url = urljoin(self.base_url, "api/Customer/FindCustomerDetails")
        payload = {"SearchFilters": {"Email": self.credentials["email"]}}
        resp = self.make_request(api_url, method="post", audit=send_audit, json=payload)
        resp_json = resp.json()
        errors = resp_json.get("Errors")
        if not errors:
            return True
        if errors[0]["ErrorCode"] == 4:
            return False
        else:
            raise JoinError()

    def _get_join_payload(self):
        hashed_password = hasher.hash(self.credentials["password"])
        marketing_optin = False
        if consents := self.credentials.get("consents", []):
            marketing_optin = consents[0]["value"]
        return {
            "PersonalInfo": {
                "FirstName": self.credentials["first_name"],
                "LastName": self.credentials["last_name"],
                "Email": self.credentials["email"],
            },
            "ExternalIdentifier": {"ExternalSource": "Bink"},
            "MarketingOptin": {"EmailOptin": marketing_optin},
            "SupInfo": [
                {
                    "FieldName": "HashPassword",
                    "FieldContent": hashed_password,
                },
                {"FieldName": "pll_bink", "FieldContent": "true"},
            ],
            "MemberNumber": {"GenerateMemberNumber": "true"},
        }

    def join(self):
        self.authenticate()
        if self._check_customer_exists():
            raise AccountAlreadyExistsError()

        url = urljoin(self.base_url, "api/Customer/Post")
        payload = self._get_join_payload()
        try:
            resp = self.make_request(url, method="post", audit=True, json=payload)
            resp_json = resp.json()
            if not resp_json["ResponseData"]["MemberNumber"]:
                raise JoinError()
            self.identifier = {"merchant_identifier": resp_json["ResponseData"]["MemberNumber"]}
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
        except BaseError as ex:
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
            raise ex

    def login(self):
        pass

    def balance(self):
        return Balance(
            points=0,
            value=0,
            value_label="",
            vouchers=[],
        )

    def transactions(self) -> list[Transaction]:
        return []
