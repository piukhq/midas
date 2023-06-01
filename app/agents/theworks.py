import json
import uuid
from decimal import Decimal, DecimalException
from typing import Any, Optional

import arrow
from blinker import signal
from soteria.configuration import Configuration


from app.scheme_account import TWO_PLACES

import settings
from app import db

from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.exceptions import AccountAlreadyExistsError, BaseError, CardNumberError, JoinError
from app.reporting import get_logger
from app.retry_util import get_task
from app.scheme_account import JourneyTypes


RETRY_LIMIT = 3
NO_PLACES = Decimal('1.')

log = get_logger("the_works")


class TheWorks(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        self.source_id = "givex"
        self.base_url = self.config.merchant_url
        self.integration_service = "SYNC"
        self.oauth_token_timeout = 3599
        self.outbound_security_credentials = self.config.security_credentials["outbound"]["credentials"][0]["value"]
        self.outbound_auth_service = self.config.security_credentials["outbound"]["service"]
        self.credentials = self.user_info["credentials"]
        self.errors = {}
        self.audit_config = {
            "type": "jsonrpc",
            "audit_sensitive_keys": [2, 3],  # positions containing sensitive fields sanitised for audit
            "audit_keys_mapping": {
                # key: positions containing searchable fields for atlas - value: atlas-readable field names
                "REQUEST": {6: "email", 8: "first_name", 10: "last_name"},
                "RESPONSE": {6: "card_number"},
            },
        }
        self.points_balance = None
        self.balance_expiry = None
        self.money_balance = None
        self.balance_error = None
        self.parsed_transactions = None
        self.login_called = False
        # in order to make test cases work these are set once assuming only one call to give x
        # per instance.  We may want to revise test cases to allow these to be reset
        self.rpc_id = str(uuid.uuid4())
        self.transaction_uuid = str(uuid.uuid4())

        if self.user_info["journey_type"] == JourneyTypes.JOIN:
            with db.session_scope() as session:
                task = get_task(db_session=session, scheme_account_id=self.user_info["scheme_account_id"])
                if task.attempts >= 2:
                    self.config = Configuration(
                        f"{scheme_slug}-failover",
                        Configuration.JOIN_HANDLER,
                        settings.VAULT_URL,
                        settings.VAULT_TOKEN,
                        settings.CONFIG_SERVICE_URL,
                        settings.AZURE_AAD_TENANT_ID,
                    )
                    self.base_url = self.config.merchant_url


    def _parse_join_response(self, resp):
        result, account_status = self.give_x_response(resp)
        if account_status == "0":
            return {
            "transaction_code": result[0],
            "result": account_status,
            "customer_id": result[2],
            "customer_first_name": result[3],
            "customer_last_name": result[4],
            "customer_reg_date": result[5],
            "iso_serial": result[6],
            "loyalty_enroll_id": result[7],
            "login_token": result[8],
            "customer_reference": result[9],
        }
        elif account_status in ("182", "67"):
            raise AccountAlreadyExistsError()
        elif account_status == "2":
            raise CardNumberError()
        else:
            raise JoinError()


    def _join_payload(self):
        consents = self.credentials.get("consents", [])
        marketing_optin = False
        if consents:
            marketing_optin = consents[0]["value"]
        consents_user_choice = "t" if marketing_optin else "f"
        new_card_request = "f" if self.credentials.get("card_number") else "t"
        return self.give_x_payload(946, [
            self.credentials["card_number"] if self.credentials.get("card_number") else "",  # givex number
            "CUSTOMER",  # customer type
            self.credentials["email"],  # customer login
            "",  # customer title
            self.credentials["first_name"],  # customer first name
            "",  # customer middle name
            self.credentials["last_name"],  # customer last name
            "",  # customer gender
            "",  # customer birthday
            "",  # customer address
            "",  # customer address 2
            "",  # customer city
            "",  # customer province
            "",  # customer county
            "",  # customer country
            "",  # postal code
            "",  # phone number
            "0",  # customer discount
            consents_user_choice,  # promotion optin
            self.credentials["email"],  # customer email
            str(uuid.uuid4()),  # customer password
            "",  # customer mobile
            "",  # customer company
            "",  # security code
            new_card_request,  # new card request
        ])

    def join(self) -> Any:
        try:
            if self.credentials.get("card_number"):
                self.audit_config["audit_keys_mapping"]["REQUEST"].update({4: "card_number"})
            request_data = self._join_payload()
            resp = self.make_request(url=self.base_url, method="post", json=request_data, audit=True)
            json_response = self._parse_join_response(resp)
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
        except BaseError:
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
            raise

        card_number = (
            self.credentials["card_number"] if self.credentials.get("card_number") else json_response["iso_serial"]
        )

        self.identifier = {
            "card_number": card_number,
            "barcode": card_number,
        }
        self.credentials.update(self.identifier)

    def _balance_result(self, error_or_balance) -> None:
        try:
            self.money_balance = Decimal(error_or_balance).quantize(TWO_PLACES)
        except DecimalException:
            self.balance_error = error_or_balance
            raise

    def _parse_balance_response(self, resp: BaseAgent.make_request):
        result, account_status = self.give_x_response(resp)
        if account_status == "0":
            self._balance_result(result[2])
            self.balance_expiry = result[4]
            self.points_balance = Decimal(result[3]).quantize(NO_PLACES)
        else:
            raise BaseError

    def _get_balance(self):
        request_data = self.give_x_payload(994, [self.credentials.get("card_number")])
        try:
            resp = self.make_request(url=self.base_url, method="post", json=request_data)
        except BaseError:
            raise
        self._parse_balance_response(resp)

    def login(self) -> Any:
        self.login_called = True
        failed = False
        try:
            self._get_transaction_history()
        except BaseError:
            failed = True

        if failed or self.balance_error is not None:
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            raise
        else:
            signal("log-in-success").send(self, slug=self.scheme_slug)
        return

    def _get_transaction_history(self):
        request_data = self.give_x_payload(995, [
            self.credentials.get("card_number"),
            "",
            "",
            "Points"
        ])
        try:
            resp = self.make_request(url=self.base_url, method="post", json=request_data)
        except BaseError:
            raise
        self.parsed_transactions = self._parse_transactions(resp)

    def transactions(self) -> list[Transaction]:
        if not self.login_called:
            try:
                self._get_transaction_history()
            except BaseError:
                raise
        if self.parsed_transactions is not None and self.balance_error is None:
            try:
                return self.hash_transactions(self.parsed_transactions)
            except Exception as ex:
                log.warning(f"{self} failed to get transactions: {repr(ex)}")
                return []
        else:
            return []

    def transaction_history(self) -> list[Transaction]:
        request_data = self.give_x_payload(995, [
            self.credentials.get("card_number"),
            "",
            "",
            "Points"
        ])
        try:
            resp = self.make_request(url=self.base_url, method="post", json=request_data)
        except BaseError:
            raise

        return self._parse_transactions(resp)

    def _parse_transactions(self, resp: BaseAgent.make_request) -> [Transaction]:
        result, account_status = self.give_x_response(resp)
        if account_status == "0":
            self._balance_result(result[2])
            self.points_balance = Decimal(result[4]).quantize(NO_PLACES)
            return [self._parse_transaction(tx) for tx in result[5]]
        else:
            raise BaseError

    def _parse_transaction(self,transaction: list) -> Transaction:
        date = arrow.get(f"{transaction[0]} {transaction[1]}", 'YYYY-MM-DD HH:mm:ss')
        return Transaction(
            date=date,
            description=f"£{self.money_balance}",
            points=Decimal(transaction[3]).quantize(NO_PLACES),
        )

    def balance(self) -> Optional[Balance]:
        if not self.login_called:
            try:
                self._get_balance()
            except BaseError:
                raise
        if self.points_balance is not None and self.balance_error is None:
            return Balance(
                points=self.points_balance,
                value=Decimal(0),
                value_label="",
            )
        else:
            return None

    def give_x_payload(self, method: int, add_params: list) -> dict:
        return {
            "jsonrpc": "2.0",
            "method": f"dc_{method}",  # request method
            "id": self.rpc_id,
            "params": [
                "en",  # language code
                self.transaction_uuid,  # transaction code
                self.outbound_security_credentials["user_id"],  # user id
                self.outbound_security_credentials["password"], # password
            ] + add_params
        }

    def give_x_response(self, resp: BaseAgent.make_request) -> (list, str):
        json_resp = json.loads(resp.content.decode("utf-8").replace("'", '"'))
        result = json_resp["result"]
        id = json_resp["id"]
        account_status = result[1]
        if id != self.rpc_id:
            log.warning(f"The works: response had message id = {id} should be {self.rpc_id}")
            account_status = -1

        if result[0] != self.transaction_uuid:
            log.warning(f"The works: response had wrong transaction id = {result[1]}"
                        f" should be {self.transaction_uuid}")
            account_status = -2

        self.rpc_id = str(uuid.uuid4())
        self.transaction_uuid = str(uuid.uuid4())
        return result, account_status
        # @todo could look as parsing common error codes here when doing the add error journey

