from typing import Optional, Tuple
from urllib.parse import urljoin
from uuid import uuid4

import requests
from _decimal import Decimal
from blinker import signal
from soteria.configuration import Configuration

import settings
from app import db
from app.agents.acteol import Acteol
from app.agents.schemas import Balance, Transaction
from app.exceptions import AccountAlreadyExistsError, BaseError, CardNumberError, JoinError
from app.journeys.view import JourneyTypes
from app.models import RetryTaskStatuses
from app.retry_util import get_task


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
        self._points_balance = Decimal(0)

    def get_audit_payload(self, kwargs, url):
        payload = super().get_audit_payload(kwargs, url)
        cred = payload.get("credentials", [{}])[0]
        payload["email"] = cred.get("id", "")  # Atlas does not except None use empty string
        return payload

    def get_auth_url_and_payload(self):
        url = urljoin(self.base_url, "token")
        payload = {
            "grant_type": "password",
            "username": self.outbound_security_credentials["username"],
            "password": self.outbound_security_credentials["password"],
        }
        return url, payload

    def authenticate(self):
        if self.outbound_auth_service == Configuration.OPEN_AUTH_SECURITY:
            return
        if self.outbound_auth_service == Configuration.OAUTH_SECURITY:
            self._oauth_authentication()

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

    def _find_customer_details(self, send_audit: bool = False) -> dict:
        self.authenticate()
        api_url = urljoin(self.base_url, "api/Customer/FindCustomerDetails")
        payload = {
            "SearchFilters": {"MemberNumber": self.credentials["card_number"]},
            "ResponseFilters": {"SupInfo": "true", "LoyaltyDetails": "true"},
        }

        resp = self.make_request(api_url, method="post", timeout=self.API_TIMEOUT, audit=send_audit, json=payload)
        resp_json = resp.json()
        self._check_response_for_error(resp_json)
        resp_data = resp_json["ResponseData"][0]

        return resp_data

    def _patch_customer_details(self, ctcid) -> None:
        api_url = urljoin(self.base_url, "api/Customer/Patch")
        payload = {"CtcID": ctcid, "SupInfo": [{"FieldName": "BinkActive", "FieldContent": "true"}]}
        resp = self.make_request(api_url, method="patch", timeout=self.API_TIMEOUT, json=payload)
        self._check_response_for_error(resp.json())

    def _update_hermes_credentials(self) -> None:
        api_url = urljoin(
            settings.HERMES_URL,
            f"schemes/accounts/{self.user_info['scheme_account_id']}/credentials",
        )
        headers = {
            "Content-type": "application/json",
            "Authorization": "token " + settings.SERVICE_API_KEY,
            "bink-user-id": str(self.user_info["bink_user_id"]),
        }
        requests.put(  # Don't want to call any signals for internal calls
            api_url, data=self.identifier, headers=headers, timeout=self.API_TIMEOUT
        )

    def login(self) -> None:
        if self.credentials["card_number"] and not self.user_info.get("from_join"):
            try:
                customer_details = self._find_customer_details(send_audit=True)
                signal("log-in-success").send(self, slug=self.scheme_slug)
            except BaseError:
                signal("log-in-fail").send(self, slug=self.scheme_slug)
                raise

            pepper_id = str(customer_details["ExternalIdentifier"]["ExternalID"])
            ctcid = str(customer_details["CtcID"])
            self._points_balance = Decimal(customer_details["LoyaltyDetails"]["LoyaltyPointsBalance"])

            self.set_identifiers(pepper_id, self.credentials["card_number"])
            self.credentials.update({"merchant_identifier": pepper_id, "ctcid": ctcid})

            # Don't call the patch customer details if this is a balance request - journey type UPDATE (id = 3)
            if not self.journey_type == JourneyTypes.UPDATE:
                self._patch_customer_details(ctcid)

            self._update_hermes_credentials()

    def _get_bink_mapped_vouchers(self) -> list:
        offer_id = settings.ITSU_VOUCHER_OFFER_ID
        if offer_id < 1:
            raise Exception(
                f"Invalid value {offer_id} in environment variable "
                f"ITSU_VOUCHER_OFFER_ID. Needs to be bigger than {offer_id}"
            )
        # Ensure a valid API token
        self.authenticate()
        if ctcid := self.credentials.get("ctcid"):
            body = {"CustomerID": ctcid, "OfferID": offer_id}
        else:
            body = {"CustomerID": str(self._find_customer_details(send_audit=True)["CtcID"]), "OfferID": offer_id}
        api_url = urljoin(self.base_url, "api/Voucher/GetAllByCustomerIDByParams")
        resp = self.make_request(api_url, method="post", timeout=self.API_TIMEOUT, json=body)
        resp_json = resp.json()

        # The API can return a list if there's an error.
        self._check_voucher_response_for_errors(resp_json)

        vouchers = resp_json["voucher"]

        bink_mapped_vouchers = []  # Vouchers mapped to format required by Bink

        # Create an 'in-progress' voucher - the current, incomplete voucher
        in_progress_voucher = self._make_in_progress_voucher(points=self._points_balance)
        bink_mapped_vouchers.append(in_progress_voucher)

        # Now create the other types of vouchers
        for voucher in vouchers:
            voucher["VoucherCode"] = "----------"
            if voucher.get("Disabled"):  # Ignore cancelled vouchers
                continue
            if bink_mapped_voucher := self._map_acteol_voucher_to_bink_struct(voucher=voucher):
                bink_mapped_vouchers.append(bink_mapped_voucher)

        return bink_mapped_vouchers

    def balance(self) -> Optional[Balance]:
        return Balance(
            points=self._points_balance,
            value=self._points_balance,
            value_label="",
            vouchers=self._get_bink_mapped_vouchers(),
        )

    def call_pepper_for_card_number(self, pepper_id: str, pepper_base_url: str) -> str:
        self.message_uid = str(uuid4())
        api_url = f"{pepper_base_url}/users/{pepper_id}/loyalty"
        payload: dict = {}
        resp = self.make_request(api_url, method="post", timeout=self.API_TIMEOUT, audit=True, json=payload)
        resp_json = resp.json()
        card_number = resp_json.get("externalLoyaltyMemberNumber", None)
        return card_number

    def set_identifiers(self, pepper_id, card_number):
        self.identifier_type = [
            "card_number",  # Not sure this is needed but the base class has one
        ]
        # Set up attributes needed for the creation of an active membership card
        self.identifier = {
            "card_number": card_number,
            "merchant_identifier": pepper_id,
        }
        self.credentials["card_number"] = card_number
        self.credentials["merchant_identifier"] = pepper_id

    def pepper_get_by_id(self, email: str, pepper_base_url: str) -> str:
        pepper_id = ""
        api_url = f"{pepper_base_url}/users?credentialId={email}&limit=3"
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT, audit=False)
        resp_json = resp.json()
        resp_items = resp_json.get("items", [])
        if len(resp_items) == 1:
            pepper_id = resp_items[0].get("id", "")
        return pepper_id

    def pepper_add_user_payload(self) -> dict:
        consents = self.credentials.get("consents", [])
        marketing_optin = False
        if consents:
            marketing_optin = consents[0]["value"]

        return {
            "firstName": self.credentials["first_name"],
            "lastName": self.credentials["last_name"],
            "credentials": [
                {
                    "provider": "EMAIL",
                    "id": self.credentials["email"],
                    "token": self.credentials["password"],
                }
            ],
            "hasAgreedToShareData": True,
            "hasAgreedToReceiveMarketing": marketing_optin,
        }

    def handle_join_account_exists(self, resp: dict, pepper_base_url: str) -> str:
        """
        Checking if this is a first time join, or we are in a retry process.
        If in retry, and pepper returns the account already associated, this mean the pepper id
        was not retrieved on the earlier attempt. We can get the pepper id for the join currently in a retry.
        If a new join, and the account already exists, then we raise the AccountAlreadyExistsError, no retrying.
        If something else fails during any of this process and we can't retry, fail this join.
        """
        with db.session_scope() as session:
            task = get_task(session, self.user_info["scheme_account_id"])
            retry_status = task.status

        code = resp.get("code", "")
        message = resp.get("message", "")
        if retry_status == RetryTaskStatuses.RETRYING and code == "Validation" and "already associated" in message:
            pepper_id = self.pepper_get_by_id(self.credentials["email"], pepper_base_url)
        elif code == "Validation" and "already associated" in message:
            raise AccountAlreadyExistsError()
        else:
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=JoinError)
            raise JoinError()
        return pepper_id

    def pepper_add_user(self, pepper_base_url) -> Tuple[str, str]:
        """
        Calls pepper and adds a new user returning the user id
        The add user call only works once if it returns a Validation error saying already associated
        then we try to get the user id calling pepper_get_by_id which try to find users by their email
        :param pepper_base_url: pepper service base url
        :return: pepper_id the id returned by pepper when user is added
        """
        card_number = ""
        api_url = urljoin(pepper_base_url, "/users?autoActivate=true&awaitExternalAccountSync=true")
        payload = self.pepper_add_user_payload()
        try:
            resp = self.make_request(api_url, method="post", timeout=20, audit=True, json=payload)
            resp_json = resp.json()
            pepper_id = resp_json.get("id", "")
            card_number = resp_json.get("externalLoyaltyMemberNumber", "")
        except BaseError as ex:
            try:
                if ex.exception.response.status_code == 422:
                    pepper_id = self.handle_join_account_exists(ex.exception.response.json(), pepper_base_url)
                else:
                    raise ex from ex
            except AttributeError:
                raise ex from ex
        return pepper_id, card_number

    def set_pepper_config(self) -> str:
        """
        Gets config for itsu-pepper from Europa
        Overwrites the base self.headers from ITSU Acteol to Pepper config

        - we will need to add code to save and restore the Acteol headers if we need to call Acteol after Pepper

        :return: url of pepper service
        """
        config = Configuration(
            "itsu-pepper",
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
            settings.AZURE_AAD_TENANT_ID,
        )
        # The join task instantiates the class with Acteol config; in case we need them, will not overwrite with pepper
        pepper_base_url = config.merchant_url
        pepper_outbound_security_credentials = config.security_credentials["outbound"]["credentials"][0]["value"]

        self.headers = {
            "Authorization": f"Token {pepper_outbound_security_credentials['authorization']}",
            "x-api-version": "10",
            "x-application-id": pepper_outbound_security_credentials["application-id"],
            "x-client-platform": "BINK",
        }
        return pepper_base_url

    def join(self):
        """join uses Pepper and not Acteol. Watch out for conflicts with the base class
        We will set up configuration for pepper but not overwrite Aceteol europa credentials in case we need
        to call Acteol as well.
        """
        pepper_base_url = self.set_pepper_config()
        pepper_id, card_number = self.pepper_add_user(pepper_base_url)

        if pepper_id and not card_number:
            card_number = self.call_pepper_for_card_number(pepper_id, pepper_base_url)

        if pepper_id and card_number:
            self.set_identifiers(pepper_id, card_number)
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
        else:
            signal("join-fail").send(
                self,
                slug=self.scheme_slug,
                channel=self.channel,
                error=JoinError,
            )
            raise JoinError()

    def transactions(self) -> list[Transaction]:
        # No transactions available for Itsu, return empty list to prevent exception being raised.
        return []
