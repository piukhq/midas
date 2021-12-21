import json
from copy import deepcopy
from decimal import Decimal
from typing import Mapping, Optional
from urllib.parse import urljoin
from uuid import uuid4

import arrow
from blinker import signal
from soteria.configuration import Configuration
from user_auth_token import UserTokenStore

import settings
from app.agents.base import ApiMiner, Balance, Transaction
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    NO_SUCH_RECORD,
    STATUS_LOGIN_FAILED,
    STATUS_REGISTRATION_FAILED,
    UNKNOWN,
    AgentError,
    JoinError,
    LoginError,
)
from app.audit import AuditLogType, RequestAuditLog
from app.encryption import AESCipher, get_aes_key, hash_ids
from app.reporting import get_logger
from app.scheme_account import JourneyTypes
from app.tasks.resend_consents import send_consents

log = get_logger("harvey-nichols-agent")


class HarveyNichols(ApiMiner):
    CONSENTS_AUTH_KEY = "4y-tfKViQ&-u4#QkxCr29@-JR?FNcj"  # Authorisation key for Harvey Nichols consents
    AGENT_TRIES = 10  # Number of attempts to send to Agent must be > 0  (0 = no send , 1 send once, 2 = 1 retry)
    HERMES_CONFIRMATION_TRIES = 10  # no of attempts to confirm to hermes Agent has received consents
    token_store = UserTokenStore(settings.REDIS_URL)
    retry_limit = 9  # tries 10 times overall

    def __init__(self, retry_count, user_info, scheme_slug=None):
        slugs = [scheme_slug, "harvey-nichols-sso"]
        configurations = [
            Configuration(
                slug, Configuration.JOIN_HANDLER, settings.VAULT_URL, settings.VAULT_TOKEN, settings.CONFIG_SERVICE_URL
            )
            for slug in slugs
        ]

        self.base_url = configurations[0].merchant_url
        self.hn_sso_url = configurations[1].merchant_url
        super().__init__(retry_count, user_info, scheme_slug)
        self.audit_logger.filter_fields = self.encrypt_sensitive_fields

    @staticmethod
    def encrypt_sensitive_fields(req_audit_logs: list[RequestAuditLog]) -> list[RequestAuditLog]:
        aes = AESCipher(get_aes_key("aes-keys"))

        # Values stored in AuditLog objects are references so they should be copied before modifying
        # in case the values are also used elsewhere.
        req_audit_logs_copy = deepcopy(req_audit_logs)
        for audit_log in req_audit_logs_copy:
            if audit_log.audit_log_type == AuditLogType.REQUEST and isinstance(audit_log.payload, Mapping):
                try:
                    customer_request_type = (
                        "CustomerSignUpRequest"
                        if "CustomerSignUpRequest" in audit_log.payload.keys()
                        else "CustomerSignOnRequest"
                    )
                    audit_log.payload[customer_request_type]["password"] = aes.encrypt(
                        audit_log.payload[customer_request_type]["password"]
                    ).decode()
                except KeyError as e:
                    log.warning(f"Unexpected payload format for Harvey Nichols audit log - Missing key: {e}")

        return req_audit_logs_copy

    def check_loyalty_account_valid(self, credentials):
        """
        Checks with HN to verify whether a valid loyalty account exists

        Don't go any further unless the account is valid
        """
        has_loyalty_account_url = urljoin(self.hn_sso_url, "user/hasloyaltyaccount")
        message_uid = str(uuid4())
        data = {"email": credentials["email"], "password": credentials["password"]}
        headers = {"Accept": "application/json"}
        record_uid = hash_ids.encode(self.scheme_id)
        integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()
        payload = deepcopy(data)
        payload["url"] = has_loyalty_account_url
        payload["password"] = "********"

        response = self.make_request(has_loyalty_account_url, method="post", headers=headers, timeout=10, json=data)
        signal("record-http-request").send(
            self,
            slug=self.scheme_slug,
            endpoint=response.request.path_url,
            latency=response.elapsed.total_seconds(),
            response_code=response.status_code,
        )

        message = response.json()["auth_resp"]["message"]
        if message != "OK":
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):
        self.credentials = credentials
        self.identifier_type = "card_number"

        if self.journey_type == JourneyTypes.LINK.value:
            self.errors = {
                STATUS_LOGIN_FAILED: ["NoSuchRecord", "Invalid", "AuthFailed"],
                UNKNOWN: ["Fail"],
            }
        else:
            self.errors = {
                NO_SUCH_RECORD: ["NoSuchRecord"],
                STATUS_LOGIN_FAILED: ["Invalid", "AuthFailed"],
                UNKNOWN: ["Fail"],
            }

        # For LINK journeys we should check to see if we can login by
        # checking the web only endpoint (MER-317) and stop if it's a Web-only
        # account. If there's a token in redis, we have previously logged in and
        # so should be able to login again.
        sign_on_required = False
        log.info(f"Login in for Harvey Nichols for scheme account id = {self.scheme_id}")
        try:
            self.token = self.token_store.get(self.scheme_id)
        except self.token_store.NoSuchToken:
            sign_on_required = True
            if self.journey_type == JourneyTypes.LINK.value:
                try:
                    self.check_loyalty_account_valid(self.credentials)
                except (LoginError, AgentError):
                    signal("log-in-fail").send(self, slug=self.scheme_slug)
                    raise

        try:
            self.customer_number = credentials[self.identifier_type]
        except KeyError:
            sign_on_required = True

        if sign_on_required:
            log.info(f"SignOn required for Harvey Nichols for scheme account id = {self.scheme_id}")
            self._login(credentials)

    def call_balance_url(self):
        url = self.base_url + "/GetProfile"
        data = {"CustomerLoyaltyProfileRequest": {"token": self.token, "customerNumber": self.customer_number}}
        log.info(
            f"Call Harvey Nichols GetProfile, token ending: {self.token[-4:]},"
            f"customer num. ending = {self.customer_number[-4:]}"
        )
        balance_response = self.make_request(url, method="post", timeout=10, json=data)
        log.info(f"Harvey Nichols balance response = {balance_response.json()}")
        signal("record-http-request").send(
            self,
            slug=self.scheme_slug,
            endpoint=balance_response.request.path_url,
            latency=balance_response.elapsed.total_seconds(),
            response_code=balance_response.status_code,
        )
        return balance_response.json()["CustomerLoyaltyProfileResult"]

    def balance(self) -> Optional[Balance]:
        result = self.call_balance_url()

        if result["outcome"] == "InvalidToken":
            self._login(self.credentials)
            result = self.call_balance_url()

        if result["outcome"] != "Success":
            self.handle_errors(result["outcome"])

        tiers_list = {"SILVER": 1, "GOLD": 2, "PLATINUM": 3, "BLACK": 4}
        tier = tiers_list[result["loyaltyTierId"]]

        return Balance(
            points=Decimal(result["pointsBalance"]),
            value=Decimal("0"),
            value_label="",
            reward_tier=tier,
        )

    def call_transaction_url(self):
        url = self.base_url + "/ListTransactions"
        from_date = arrow.get("2001/01/01").format("YYYY-MM-DDTHH:mm:ssZ")
        to_date = arrow.utcnow().format("YYYY-MM-DDTHH:mm:ssZ")
        data = {
            "CustomerListTransactionsRequest": {
                "token": self.token,
                "customerNumber": self.customer_number,
                "fromDate": from_date,
                "toDate": to_date,
                "pageOffset": 0,
                "pageSize": 20,
                "maxHits": 10,
            }
        }

        transaction_response = self.make_request(url, method="post", timeout=10, json=data)
        signal("record-http-request").send(
            self,
            slug=self.scheme_slug,
            endpoint=transaction_response.request.path_url,
            latency=transaction_response.elapsed.total_seconds(),
            response_code=transaction_response.status_code,
        )
        return transaction_response.json()["CustomerListTransactionsResponse"]

    def parse_transaction(self, row: dict) -> Optional[Transaction]:
        if type(row["value"]) == int:
            money_value = abs(row["value"])
            formatted_money_value = " £{:.2f}".format(Decimal(money_value / 100))
        else:
            formatted_money_value = ""

        return Transaction(
            date=arrow.get(row["date"]),
            description="{}: {}{}".format(row["type"], row["locationName"], formatted_money_value),
            points=Decimal(row["pointsValue"]),
        )

    def scrape_transactions(self) -> list[dict]:
        result = self.call_transaction_url()

        if result["outcome"] == "InvalidToken":
            self._login(self.credentials)
            result = self.call_transaction_url()

        if result["outcome"] != "Success":
            self.handle_errors(result["outcome"])

        transactions = [transaction["CustomerTransaction"] for transaction in result["transactions"]]
        transaction_types = ["Sale", "Refund"]
        sorted_transactions = [transaction for transaction in transactions if transaction["type"] in transaction_types]

        return sorted_transactions

    def join(self, credentials):
        message_uid = str(uuid4())
        self.errors = {ACCOUNT_ALREADY_EXISTS: "AlreadyExists", STATUS_REGISTRATION_FAILED: "Invalid", UNKNOWN: "Fail"}
        url = self.base_url + "/SignUp"
        data = {
            "CustomerSignUpRequest": {
                "username": credentials["email"],
                "email": credentials["email"],
                "password": credentials["password"],
                "title": credentials["title"],
                "forename": credentials["first_name"],
                "surname": credentials["last_name"],
                "applicationId": "BINK_APP",
            }
        }
        if credentials.get("phone"):
            data["CustomerSignUpRequest"]["phone"] = credentials["phone"]

        record_uid = hash_ids.encode(self.scheme_id)
        integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()

        payload = deepcopy(data)
        payload["CustomerSignUpRequest"].update({"url": url})

        self.join_response = self.make_request(url, method="post", timeout=10, json=data)
        signal("record-http-request").send(
            self,
            slug=self.scheme_slug,
            endpoint=self.join_response.request.path_url,
            latency=self.join_response.elapsed.total_seconds(),
            response_code=self.join_response.status_code,
        )

        message = self.join_response.json()["CustomerSignUpResult"]["outcome"]

        if message == "Success":
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.user_info["channel"])
            return {"message": "success"}

        signal("join-fail").send(self, slug=self.scheme_slug, channel=self.user_info["channel"])
        self.handle_errors(message, exception_type=JoinError)

    def _login(self, credentials):
        """
        Retrieves user token and customer number, saving token in user token redis db.
        """
        message_uid = str(uuid4())
        url = self.base_url + "/SignOn"
        data = {
            "CustomerSignOnRequest": {
                "username": credentials["email"],
                "password": credentials["password"],
                "applicationId": "BINK_APP",
            }
        }

        record_uid = hash_ids.encode(self.scheme_id)
        integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()
        # Add in email, expected by Atlas
        data["CustomerSignOnRequest"].update({"email": credentials["email"]})
        payload = deepcopy(data)
        payload["CustomerSignOnRequest"].update({"url": url})
        payload["CustomerSignOnRequest"].update({"password": "********"})

        self.login_response = self.make_request(url, method="post", timeout=10, json=data)
        log.info(f"SignOn called for scheme account id = {self.scheme_id}, response = {self.login_response}")
        signal("record-http-request").send(
            self,
            slug=self.scheme_slug,
            endpoint=self.login_response.request.path_url,
            latency=self.login_response.elapsed.total_seconds(),
            response_code=self.login_response.status_code,
        )

        json_result = self.login_response.json()["CustomerSignOnResult"]
        if json_result["outcome"] == "Success":
            signal("log-in-success").send(self, slug=self.scheme_slug)
            self.customer_number = json_result["customerNumber"]
            self.token = json_result["token"]
            self.token_store.set(self.scheme_id, self.token)

            if self.identifier_type not in credentials:
                # self.identifier should only be set if identifier type is not passed in credentials
                self.identifier = {self.identifier_type: self.customer_number}

                if not credentials.get("consents"):
                    return

                self.create_journey = "join"
                # Use consents retry mechanism as explained in
                # https://books.bink.com/books/backend-development/page/retry-tasks
                hn_post_message = {"enactor_id": self.customer_number}
                confirm_retries = {}  # While hold the retry count down for each consent confirmation retried

                for consent in credentials["consents"]:
                    hn_post_message[consent["slug"]] = consent["value"]
                    confirm_retries[consent["id"]] = self.HERMES_CONFIRMATION_TRIES

                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                    "Auth-key": self.CONSENTS_AUTH_KEY,
                }
                consents_url = urljoin(self.hn_sso_url, "preferences/create")
                send_consents(
                    {
                        "url": consents_url,  # set to scheme url for the agent to accept consents
                        "headers": headers,  # headers used for agent consent call
                        "message": json.dumps(hn_post_message),  # set to message body encoded as required
                        "agent_tries": self.AGENT_TRIES,  # max number of attempts to send consents to agent
                        "confirm_tries": confirm_retries,  # retries for each consent confirmation sent to hermes
                        "id": self.customer_number,  # used for identification in error messages
                        "callback": "app.agents.harvey_nichols"  # If present identifies the module containing the
                        # function "agent_consent_response"
                        # callback_function can be set to change default function
                        # name.  Without this the HTML repsonse status code is used
                    }
                )

        else:
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            self.handle_errors(json_result["outcome"])


def agent_consent_response(resp):
    response_data = json.loads(resp.text)
    if response_data.get("response") == "success" and response_data.get("code") == 200:
        return True, ""
    return False, f'harvey nichols returned {response_data.get("response","")}, code:{response_data.get("code","")}'
