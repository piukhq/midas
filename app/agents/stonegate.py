from decimal import Decimal
from urllib.parse import urlencode, urljoin
from uuid import uuid4

import argon2
from blinker import signal
from soteria.configuration import Configuration

from app.agents.acteol import Acteol
from app.agents.schemas import Balance, Transaction
from app.exceptions import AccountAlreadyExistsError, BaseError, CardNumberError, JoinError

hasher = argon2.PasswordHasher()


class Stonegate(Acteol):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.oauth_token_timeout = 75600  # n_seconds in 21 hours
        self.integration_service = "SYNC"
        self._points_balance = 0
        self.audit_config = {
            "type": "json",
            "audit_sensitive_keys": ["SupInfo"],
        }

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

    def _check_customer_exists(self, send_audit: bool = True) -> bool:
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
        try:
            if self._check_customer_exists():
                raise AccountAlreadyExistsError()

            self.message_uid = str(uuid4())
            url = urljoin(self.base_url, "api/Customer/Post")
            payload = self._get_join_payload()
            resp = self.make_request(url, method="post", audit=True, json=payload)
            resp_json = resp.json()
            if not resp_json["ResponseData"]["MemberNumber"]:
                raise JoinError()
            self.identifier = {
                "merchant_identifier": resp_json["ResponseData"]["MemberNumber"],
                "card_number": resp_json["ResponseData"]["MemberNumber"],
            }
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
        except BaseError as ex:
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
            raise ex

    def _find_customer_details(self, filters, send_audit: bool = False) -> dict:
        self.authenticate()
        api_url = urljoin(self.base_url, "api/Customer/FindCustomerDetails")
        payload = {
            "SearchFilters": filters,
            "ResponseFilters": {"LoyaltyDetails": True, "StaffInfo": True, "SupInfo": True},
            "BrandID": "Bink",
        }
        resp = self.make_request(api_url, method="post", audit=send_audit, json=payload)
        resp_json = resp.json()
        errors = resp_json.get("Errors")
        if not errors:
            return resp_json["ResponseData"][0]
        if errors[0]["ErrorCode"] == 4:
            return {}
        else:
            raise Exception()

    def _patch_customer_details(self, ctc_id) -> None:
        api_url = urljoin(self.base_url, "api/Customer/Patch")
        payload = {
            "CtcID": ctc_id,
            "DataProcess": {
                "ProcessMydata": True,
            },
            "ModifiedDate": "2023-06-08T09:11:39.8328971+01:00",
            "SupInfo": [{"FieldName": "pll_bink", "FieldContent": "true"}],
        }
        resp = self.make_request(api_url, method="patch", json=payload)
        self._check_response_for_error(resp.json())

    def login(self):
        if self.credentials.get("card_number"):
            try:
                response_data = self._find_customer_details(
                    send_audit=True, filters={"MemberNumber": self.credentials["card_number"]}
                )
                if not response_data:
                    signal("request-fail").send(
                        self,
                        slug=self.scheme_slug,
                        channel=self.channel,
                        error=CardNumberError,
                    )
                    raise CardNumberError
                ctc_id = response_data["CtcID"]
                self._points_balance = int(response_data["LoyaltyDetails"]["LoyaltyPointsBalance"])
                self._patch_customer_details(ctc_id)

                signal("log-in-success").send(self, slug=self.scheme_slug)

                # Set up attributes needed for the creation of an active membership card
                self.identifier = {
                    "card_number": self.credentials["card_number"],
                    "merchant_identifier": self.credentials["card_number"],
                }
                self.credentials.update({"merchant_identifier": self.credentials["card_number"]})
            except BaseError:
                signal("log-in-fail").send(self, slug=self.scheme_slug)
                raise

    def balance(self):
        return Balance(
            points=Decimal(self._points_balance),
            value=Decimal(0),
            value_label="",
            vouchers=[],
        )

    def transactions(self) -> list[Transaction]:
        return []


    def loyalty_card_removed(self) -> None:
        pll_mixr = False

        response_data = self._find_customer_details(
            send_audit=True, filters={"MemberNumber": self.credentials["card_number"]}
        )
        if not response_data:
            raise StatusLoginFailedError
        ctc_id = response_data["CtcID"]

        api_url = urljoin(self.base_url, "api/Customer/Patch")
        payload = {
            "CtcID": ctc_id,
            "DataProcess": {
                "ProcessMydata": True,
            },
            "ModifiedDate": "2023-06-08T09:11:39.8328971+01:00",
            "SupInfo": [{"FieldName": "pll_bink", "FieldContent": "false"}],
        }
        self.make_request(api_url, method="patch", json=payload)
