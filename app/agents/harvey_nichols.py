import json
from copy import deepcopy
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin

import arrow
from blinker import signal
from soteria.configuration import Configuration
from user_auth_token import UserTokenStore

import settings
from app.agents.base import Balance, BaseAgent, Transaction
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
from app.reporting import get_logger
from app.scheme_account import JourneyTypes
from app.tasks.resend_consents import send_consents

log = get_logger("harvey-nichols-agent")


class HarveyNichols(BaseAgent):
    CONSENTS_AUTH_KEY = "4y-tfKViQ&-u4#QkxCr29@-JR?FNcj"  # Authorisation key for Harvey Nichols consents
    AGENT_TRIES = 10  # Number of attempts to send to Agent must be > 0  (0 = no send , 1 send once, 2 = 1 retry)
    HERMES_CONFIRMATION_TRIES = 10  # no of attempts to confirm to hermes Agent has received consents
    token_store = UserTokenStore(settings.REDIS_URL)
    retry_limit = 9  # tries 10 times overall

    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        self.source_id = "harveynichols"
        self.credentials = self.user_info["credentials"]
        self.base_url = self.config.merchant_url
        self.sso_url = self._get_sso_url()
        self.integration_service = "SYNC"

    def _get_sso_url(self):
        sso_config = Configuration(
            "harvey-nichols-sso",
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        return sso_config.merchant_url

    def check_loyalty_account_valid(self):
        """
        Checks with HN to verify whether a valid loyalty account exists

        Don't go any further unless the account is valid
        """
        has_loyalty_account_url = urljoin(self.sso_url, "user/hasloyaltyaccount")
        data = {"email": self.credentials["email"], "password": self.credentials["password"]}
        headers = {"Accept": "application/json"}
        payload = deepcopy(data)
        payload["url"] = has_loyalty_account_url
        payload["password"] = "********"

        response = self.make_request(
            has_loyalty_account_url, method="post", headers=headers, timeout=10, audit=True, json=data
        )

        message = response.json()["auth_resp"]["message"]
        if message != "OK":
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self):
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
                    self.check_loyalty_account_valid()
                except (LoginError, AgentError):
                    signal("log-in-fail").send(self, slug=self.scheme_slug)
                    raise

        try:
            self.customer_number = self.credentials[self.identifier_type]
        except KeyError:
            sign_on_required = True

        if sign_on_required:
            log.info(f"SignOn required for Harvey Nichols for scheme account id = {self.scheme_id}")
            self._login()

    def call_balance_url(self):
        url = self.base_url + "/GetProfile"
        data = {"CustomerLoyaltyProfileRequest": {"token": self.token, "customerNumber": self.customer_number}}
        log.info(
            f"Call Harvey Nichols GetProfile, token ending: {self.token[-4:]},"
            f"customer num. ending = {self.customer_number[-4:]}"
        )
        balance_response = self.make_request(url, method="post", timeout=10, json=data)
        log.info(f"Harvey Nichols balance response = {balance_response.json()}")

        return balance_response.json()["CustomerLoyaltyProfileResult"]

    def balance(self) -> Optional[Balance]:
        result = self.call_balance_url()

        if result["outcome"] == "InvalidToken":
            self._login()
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

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception as ex:
            log.warning(f"{self} failed to get transactions: {repr(ex)}")
            return []

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

        return transaction_response.json()["CustomerListTransactionsResponse"]

    def parse_transaction(self, row: dict) -> Transaction:
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

    def transaction_history(self) -> list[Transaction]:
        result = self.call_transaction_url()

        if result["outcome"] == "InvalidToken":
            self._login()
            result = self.call_transaction_url()

        if result["outcome"] != "Success":
            self.handle_errors(result["outcome"])

        customer_transactions = [transaction["CustomerTransaction"] for transaction in result["transactions"]]
        transaction_types = ["Sale", "Refund"]
        sorted_transactions = [
            transaction for transaction in customer_transactions if transaction["type"] in transaction_types
        ]

        transactions = [self.parse_transaction(tx) for tx in sorted_transactions]
        return transactions

    def join(self):
        self.errors = {ACCOUNT_ALREADY_EXISTS: "AlreadyExists", STATUS_REGISTRATION_FAILED: "Invalid", UNKNOWN: "Fail"}
        url = self.base_url + "/SignUp"
        data = {
            "CustomerSignUpRequest": {
                "username": self.credentials["email"],
                "email": self.credentials["email"],
                "password": self.credentials["password"],
                "title": self.credentials["title"],
                "forename": self.credentials["first_name"],
                "surname": self.credentials["last_name"],
                "applicationId": "BINK_APP",
            }
        }
        if self.credentials.get("phone"):
            data["CustomerSignUpRequest"]["phone"] = self.credentials["phone"]

        payload = deepcopy(data)
        payload["CustomerSignUpRequest"].update({"url": url})

        self.join_response = self.make_request(url, method="post", timeout=10, audit=True, json=data)

        message = self.join_response.json()["CustomerSignUpResult"]["outcome"]

        if message == "Success":
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
            return {"message": "success"}

        signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
        self.handle_errors(message, exception_type=JoinError)

    def _login(self):
        """
        Retrieves user token and customer number, saving token in user token redis db.
        """
        url = self.base_url + "/SignOn"
        data = {
            "CustomerSignOnRequest": {
                "username": self.credentials["email"],
                "password": self.credentials["password"],
                "applicationId": "BINK_APP",
            }
        }

        # Add in email, expected by Atlas
        data["CustomerSignOnRequest"].update({"email": self.credentials["email"]})
        payload = deepcopy(data)
        payload["CustomerSignOnRequest"].update({"url": url})
        payload["CustomerSignOnRequest"].update({"password": "********"})

        self.login_response = self.make_request(url, method="post", timeout=10, audit=True, json=data)
        log.info(f"SignOn called for scheme account id = {self.scheme_id}, response = {self.login_response}")

        json_result = self.login_response.json()["CustomerSignOnResult"]
        if json_result["outcome"] == "Success":
            signal("log-in-success").send(self, slug=self.scheme_slug)
            self.customer_number = json_result["customerNumber"]
            self.token = json_result["token"]
            self.token_store.set(self.scheme_id, self.token)

            if self.identifier_type not in self.credentials:
                # self.identifier should only be set if identifier type is not passed in credentials
                self.identifier = {self.identifier_type: self.customer_number}

                if not self.credentials.get("consents"):
                    return

                self.create_journey = "join"
                # Use consents retry mechanism as explained in
                # https://books.bink.com/books/backend-development/page/retry-tasks
                hn_post_message = {"enactor_id": self.customer_number}
                confirm_retries = {}  # While hold the retry count down for each consent confirmation retried

                for consent in self.credentials["consents"]:
                    hn_post_message[consent["slug"]] = consent["value"]
                    confirm_retries[consent["id"]] = self.HERMES_CONFIRMATION_TRIES

                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                    "Auth-key": self.CONSENTS_AUTH_KEY,
                }
                consents_url = urljoin(self.sso_url, "preferences/create")
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
