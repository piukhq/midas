from uuid import uuid1
from decimal import Decimal

from cryptography.fernet import Fernet

from app.agents.exceptions import (
    LoginError, RegistrationError,
    STATUS_REGISTRATION_FAILED,
    ACCOUNT_ALREADY_EXISTS,
    UNKNOWN,
    STATUS_LOGIN_FAILED,
    NO_SUCH_RECORD,
)
from app.utils import JourneyTypes
from app.agents.base import ApiMiner
from gaia.user_token import UserTokenStore
from settings import REDIS_URL, ATLAS_CREDENTIAL_KEY
from app.tasks.resend_consents import send_consents
import arrow
import json


class HarveyNichols(ApiMiner):
    BASE_URL = "https://loyalty.harveynichols.com/WebCustomerLoyalty/services/CustomerLoyalty"
    CONSENTS_URL = "https://hn_sso.harveynichols.com/preferences/create"
    HAS_LOYALTY_ACCOUNT_URL = "https://hn_sso.harveynichols.com/user/hasloyaltyaccount"

    CONSENTS_AUTH_KEY = "4y-tfKViQ&-u4#QkxCr29@-JR?FNcj"  # Authorisation key for Harvey Nichols consents
    AGENT_TRIES = 10  # Number of attempts to send to Agent must be > 0  (0 = no send , 1 send once, 2 = 1 retry)
    HERMES_CONFIRMATION_TRIES = 10  # no of attempts to confirm to hermes Agent has received consents
    token_store = UserTokenStore(REDIS_URL)
    retry_limit = 9  # tries 10 times overall

    encryption_key = Fernet(ATLAS_CREDENTIAL_KEY)

    def check_loyalty_account_valid(self, credentials):
        """
        Checks with HN to verify whether a valid loyalty account exists

        Don't go any further unless the account is valid
        """
        data = {"email": credentials["email"], "password": credentials["password"]}
        headers = {"Accept": "application/json"}
        response = self.make_request(
            self.HAS_LOYALTY_ACCOUNT_URL, method="post", headers=headers, timeout=10, json=data)
        message = response.json()["auth_resp"]["message"]
        if message != 'OK':
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
        try:
            self.token = self.token_store.get(self.scheme_id)
        except self.token_store.NoSuchToken:
            sign_on_required = True
            if self.journey_type == JourneyTypes.LINK.value:
                self.check_loyalty_account_valid(self.credentials)

        try:
            self.customer_number = credentials[self.identifier_type]
        except KeyError:
            sign_on_required = True

        if sign_on_required:
            self._login(credentials)

    def call_balance_url(self):
        url = self.BASE_URL + "/GetProfile"
        data = {"CustomerLoyaltyProfileRequest": {"token": self.token, "customerNumber": self.customer_number}}
        balance_response = self.make_request(url, method="post", timeout=10, json=data)
        return balance_response.json()["CustomerLoyaltyProfileResult"]

    def balance(self):
        result = self.call_balance_url()

        if result["outcome"] == "InvalidToken":
            self._login(self.credentials)
            result = self.call_balance_url()

        if result["outcome"] != "Success":
            self.handle_errors(result["outcome"])

        tiers_list = {"SILVER": 1, "GOLD": 2, "PLATINUM": 3, "BLACK": 4}
        tier = tiers_list[result["loyaltyTierId"]]

        return {
            "points": Decimal(result["pointsBalance"]),
            "value": Decimal("0"),
            "value_label": "",
            "reward_tier": tier,
        }

    def call_transaction_url(self):
        url = self.BASE_URL + "/ListTransactions"
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

    @staticmethod
    def parse_transaction(row):
        if type(row["value"]) == int:
            money_value = abs(row["value"])
            formatted_money_value = " £{:.2f}".format(Decimal(money_value / 100))
        else:
            formatted_money_value = ""

        return {
            "date": arrow.get(row["date"]),
            "description": "{}: {}{}".format(row["type"], row["locationName"], formatted_money_value),
            "points": Decimal(row["pointsValue"]),
        }

    def scrape_transactions(self):
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

    def register(self, credentials):
        message_uid = str(uuid1())
        self.errors = {ACCOUNT_ALREADY_EXISTS: "AlreadyExists", STATUS_REGISTRATION_FAILED: "Invalid", UNKNOWN: "Fail"}
        url = self.BASE_URL + "/SignUp"
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

        payload = data.copy()
        payload['CustomerSignUpRequest']['password'] = self.encryption_key.encrypt(
            payload['CustomerSignUpRequest']['password'].encode())

        self.audit_logger.add_request(
            payload=data,
            scheme_slug=self.scheme_slug,
            message_uid=message_uid,
            record_uid=None,
            handler_type=None,
            integration_service=None
        )

        self.register_response = self.make_request(url, method="post", timeout=10, json=data)

        self.audit_logger.add_response(
            response=self.register_response,
            message_uid=message_uid,
            record_uid=None,
            scheme_slug=self.scheme_slug,
            handler_type=None,
            integration_service=None,
            status_code=self.register_response.status_code,
            response_body=self.register_response.text,
        )
        self.audit_logger.send_to_atlas()

        message = self.register_response.json()["CustomerSignUpResult"]["outcome"]

        if message == "Success":
            return {"message": "success"}

        self.handle_errors(message, exception_type=RegistrationError)

    def _login(self, credentials):
        """
        Retrieves user token and customer number, saving token in user token redis db.
        """
        url = self.BASE_URL + "/SignOn"
        data = {
            "CustomerSignOnRequest": {
                "username": credentials["email"],
                "password": credentials["password"],
                "applicationId": "BINK_APP",
            }
        }

        self.login_response = self.make_request(url, method="post", timeout=10, json=data)
        json_result = self.login_response.json()["CustomerSignOnResult"]

        if json_result["outcome"] == "Success":
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

                send_consents(
                    {
                        "url": self.CONSENTS_URL,  # set to scheme url for the agent to accept consents
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
            self.handle_errors(json_result["outcome"])


def agent_consent_response(resp):
    response_data = json.loads(resp.text)
    if response_data.get("response") == "success" and response_data.get("code") == 200:
        return True, ""
    return False, f'harvey nichols returned {response_data.get("response","")}, code:{response_data.get("code","")}'
