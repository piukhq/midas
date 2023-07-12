from http import HTTPStatus
from typing import Optional, Tuple
from urllib.parse import urlencode, urljoin

import sentry_sdk
from _decimal import Decimal
from blinker import signal
from soteria.configuration import Configuration

import settings
from app.agents.acteol import Acteol, log
from app.agents.schemas import Balance
from app.exceptions import BaseError, CardNumberError, NoSuchRecordError


class Itsu(Acteol):
    API_TIMEOUT = 10  # n_seconds until timeout for calls to Acteol's API
    N_TRANSACTIONS = 5  # Number of transactions to return from Acteol's API
    # Number of attempts to send consents to Agent must be > 0
    # (0 = no send , 1 send once, 2 = 1 retry)
    AGENT_CONSENT_TRIES = 10
    # no of attempts to confirm to hermes Agent has received consents
    HERMES_CONFIRMATION_TRIES = 10

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

    def _check_response_for_error(self, resp_json: dict):
        """
        Handle response error
        """
        errors = resp_json.get("Errors")
        if not errors:
            return
        if errors[0]["ErrorCode"] == 4:
            raise CardNumberError()
        else:
            raise Exception()

    def _find_customer_details(self) -> Tuple[str, str]:
        self.authenticate()
        api_url = urljoin(self.base_url, "/api/Customer/FindCustomerDetails")
        payload = {
            "SearchFilters": {"MemberNumber": self.credentials["card_number"]},
            "ResponseFilters": {"SupInfo": "true"},
        }

        resp = self.make_request(api_url, method="post", timeout=self.API_TIMEOUT, audit=True, json=payload)
        resp_json = resp.json()
        self._check_response_for_error(resp_json)
        resp_data = resp_json["ResponseData"][0]
        ctcid = str(resp_data["CtcID"])
        pepper_id = str(resp_data["ExternalIdentifier"]["ExternalID"])

        return ctcid, pepper_id

    def _patch_customer_details(self, ctcid) -> None:
        api_url = urljoin(self.base_url, "/api/Customer/Patch")
        payload = {"CtcID": ctcid, "SupInfo": [{"FieldName": "BinkActive", "FieldContent": "true"}]}
        resp = self.make_request(api_url, method="patch", timeout=self.API_TIMEOUT, json=payload)
        self._check_response_for_error(resp.json())

    def login(self) -> None:
        if (
            self.credentials["card_number"]
            and not self.user_info.get("from_join")
            and not self.credentials.get("merchant_identifier")
        ):
            try:
                ctcid, pepper_id = self._find_customer_details()
                self._patch_customer_details(ctcid)
                signal("log-in-success").send(self, slug=self.scheme_slug)
                self.identifier_type = [
                    "card_number",  # Not sure this is needed but the base class has one
                ]
                # Set up attributes needed for the creation of an active membership card
                self.identifier = {
                    "card_number": self.credentials["card_number"],
                    "merchant_identifier": pepper_id,
                }
                self.credentials.update({"merchant_identifier": pepper_id, "ctcid": ctcid})
            except BaseError:
                signal("log-in-fail").send(self, slug=self.scheme_slug)
                raise

    def _get_customer_details(self, ctcid: str) -> dict:
        api_url = urljoin(self.base_url, f"api/Loyalty/GetCustomerDetails?customerid={ctcid}")
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)
        if resp.status_code != HTTPStatus.OK:
            log.debug(f"Error while fetching customer details, reason: {resp.status_code} {resp.reason}")
            raise Exception  # The journey ends

        resp_json = resp.json()
        self._check_response_for_error(resp_json)
        return resp_json

    def balance(self) -> Optional[Balance]:
        # Ensure a valid API token
        self.authenticate()
        try:
            ctcid = self.credentials.get("ctcid")
            pepper_id = self.credentials.get("merchant_identifier")
            if not ctcid:
                # Find customer ctcid
                ctcid, pepper_id = self._find_customer_details()
            # Get customer details
            customer_details = self._get_customer_details(ctcid=ctcid)
        except BaseError as ex:
            sentry_issue_id = sentry_sdk.capture_exception(ex)
            log.debug(
                f"Balance Error: {ex.message}, Sentry Issue ID: {sentry_issue_id}, Scheme: {self.scheme_slug} "
                f"Scheme Account ID: {self.scheme_id}"
            )
            raise

        if not self._customer_fields_are_present(customer_details=customer_details):
            log.debug(
                (
                    "Expected fields not found in customer details during join: Email, CurrentMemberNumber, CustomerID "
                    f"for user ID: {self.credentials['merchant_identifier']}"
                )
            )
            raise NoSuchRecordError()

        self._check_deleted_user(resp_json=customer_details)
        points = Decimal(customer_details["LoyaltyPointsBalance"])

        self.update_hermes_credentials(pepper_id, customer_details)

        # Get all vouchers for this customer
        vouchers = self._get_vouchers(ctcid=ctcid, offer_id=settings.ITSU_VOUCHER_OFFER_ID)

        bink_mapped_vouchers = []  # Vouchers mapped to format required by Bink

        # Create an 'in-progress' voucher - the current, incomplete voucher
        in_progress_voucher = self._make_in_progress_voucher(points=points)
        bink_mapped_vouchers.append(in_progress_voucher)

        # Now create the other types of vouchers
        for voucher in vouchers:
            voucher["VoucherCode"] = "----------"
            if voucher.get("Disabled"):  # Ignore cancelled vouchers
                continue
            if bink_mapped_voucher := self._map_acteol_voucher_to_bink_struct(voucher=voucher):
                bink_mapped_vouchers.append(bink_mapped_voucher)

        return Balance(
            points=points,
            value=points,
            value_label="",
            vouchers=bink_mapped_vouchers,
        )
