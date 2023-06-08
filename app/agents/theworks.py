import json
import uuid
from decimal import Decimal, DecimalException
from typing import Any, Optional

import arrow
from blinker import signal
from requests import Response
from soteria.configuration import Configuration

from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.exceptions import (
    AccountAlreadyExistsError,
    BaseError,
    CardNotRegisteredError,
    CardNumberError,
    EndSiteDownError,
    JoinError,
    NotSentError,
    RetryLimitReachedError,
    UnknownError,
)
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES

RETRY_LIMIT = 3

log = get_logger("the_works")


class TheWorks(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        urls = self.config.merchant_url.split(",")
        self.base_url = urls[0]
        self.base_url_failover = urls[1]
        self.source_id = "givex"
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
        self.money_balance = None
        self.parsed_transactions = None
        # So the expected transaction code and rpc message id can be used in unit tests they are set in the class
        # instance for use in the first call to Give X and reset for the next call.
        self.rpc_id = str(uuid.uuid4())
        self.transaction_uuid = str(uuid.uuid4())

    def _make_request(self, method, request_data, audit=False):
        try:
            resp = self.make_request(url=self.base_url, method=method, json=request_data, audit=audit)
        except (RetryLimitReachedError, EndSiteDownError, NotSentError):
            try:
                resp = self.make_request(url=self.base_url_failover, method="post", json=request_data, audit=audit)
            except (RetryLimitReachedError, EndSiteDownError, NotSentError) as e:
                raise e

        return resp

    def _parse_join_response(self, resp: Response):
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
        return self.give_x_payload(
            "dc_946",
            [
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
                "",  # customer password
                "",  # customer mobile
                "",  # customer company
                "",  # security code
                new_card_request,  # new card request
            ],
        )

    def join(self) -> Any:
        try:
            if self.credentials.get("card_number"):
                self.audit_config["audit_keys_mapping"]["REQUEST"].update({4: "card_number"})
            request_data = self._join_payload()
            resp = self._make_request(method="post", request_data=request_data, audit=True)
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

    def login(self) -> Any:
        try:
            # GiveX has no login but transaction dc_995 returns the balance or error status so can verify the account.
            # The one call also gets the transactions and balance which is saved for later and avoids multiple requests
            # Our apps don't allow the display of 2 Give X balances i.e. Points are periodically converted to money so
            # there is a money balance as well as a points balance
            # This code is based on the proposed solution of returning current money balance on every transaction with
            # the running points balance.
            # Only points is given in Balance response
            request_data = self.give_x_payload("dc_995", [self.credentials.get("card_number"), "", "", "Points"])
            resp = self._make_request(method="post", request_data=request_data)
            result, account_status = self.give_x_response(resp)

            if account_status == "0":
                error_or_balance = result[2]
                try:
                    self.money_balance = Decimal(error_or_balance).quantize(TWO_PLACES)
                    self.points_balance = Decimal(result[4]).quantize(Decimal("1."))
                    self.parsed_transactions = [self._parse_transaction(tx) for tx in result[5]]
                    signal("log-in-success").send(self, slug=self.scheme_slug)
                except DecimalException:
                    log.warning(
                        f"{self}:transaction history dc_995 returned"
                        f" 0 account status but with an error message: {error_or_balance}"
                    )
                    raise UnknownError()
            elif account_status == "285":
                raise CardNotRegisteredError()
            elif account_status == "2":
                raise CardNumberError()
            else:
                log.warning(f"{self}: login to Account failed with status = {account_status}")
                raise UnknownError()

        except BaseError:
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            raise

    def transactions(self) -> list[Transaction]:
        if self.parsed_transactions is not None:
            try:
                return self.hash_transactions(self.parsed_transactions)
            except Exception as ex:
                log.warning(f"{self} failed to get transactions: {repr(ex)}")
                return []
        else:
            return []

    def _parse_transaction(self, transaction: list) -> Transaction:
        date = arrow.get(f"{transaction[0]} {transaction[1]}", "YYYY-MM-DD HH:mm:ss")
        return Transaction(
            date=date,
            description=f"Available balance: £{self.money_balance}",
            points=Decimal(transaction[3]).quantize(Decimal("1.")),
        )

    def balance(self) -> Optional[Balance]:
        if self.points_balance is not None:
            return Balance(
                points=self.points_balance,
                value=Decimal(0),
                value_label="",
            )
        else:
            return None

    def give_x_payload(self, method: str, add_params: list) -> dict:
        return {
            "jsonrpc": "2.0",
            "method": method,  # request method
            "id": self.rpc_id,
            "params": [
                "en",  # language code
                self.transaction_uuid,  # transaction code
                self.outbound_security_credentials["user_id"],  # user id
                self.outbound_security_credentials["password"],  # password
            ]
            + add_params,
        }

    def give_x_response(self, resp: Response) -> tuple[list, str]:
        json_resp = json.loads(resp.content.decode("utf-8").replace("'", '"'))
        result = json_resp["result"]
        id = json_resp["id"]
        account_status = result[1]
        if id != self.rpc_id:
            log.warning(f"The works: response had message id = {id} should be {self.rpc_id}")
            account_status = -1

        if result[0] != self.transaction_uuid:
            log.warning(
                f"The works: response had wrong transaction id = {result[1]}" f" should be {self.transaction_uuid}"
            )
            account_status = -2

        self.rpc_id = str(uuid.uuid4())
        self.transaction_uuid = str(uuid.uuid4())
        return result, account_status
