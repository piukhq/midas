import json
import uuid
from decimal import Decimal
from typing import Any, Optional

import arrow
from soteria.configuration import Configuration

from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.exceptions import AccountAlreadyExistsError, BaseError, JoinError
from app.reporting import get_logger

RETRY_LIMIT = 3
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

    @staticmethod
    def _parse_join_response(resp):
        resp = json.loads(resp.content.decode("utf-8").replace("'", '"'))
        result = resp["result"]
        account_status = result[1]
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
        elif account_status == "182":
            raise AccountAlreadyExistsError()
        else:
            raise JoinError()

    def _join_payload(self):
        consents = self.credentials.get("consents", [])
        marketing_optin = False
        if consents:
            marketing_optin = consents[0]["value"]
        consents_user_choice = "t" if marketing_optin else "f"
        new_card_request = "f" if self.credentials.get("card_number") else "t"
        transaction_code = str(uuid.uuid4())
        return {
            "jsonrpc": "2.0",
            "method": "dc_946",  # request method
            "id": 1,
            "params": [
                "en",  # language code
                transaction_code,  # transaction code
                self.outbound_security_credentials["user_id"],  # user id
                self.outbound_security_credentials["password"],  # password
                "",  # givex number
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
                transaction_code,  # customer password
                "",  # customer mobile
                "",  # customer company
                "",  # security code
                new_card_request,  # new card request
            ],
        }

    def join(self) -> Any:
        try:
            request_data = self._join_payload()
            resp = self.make_request(url=self.base_url, method="post", json=request_data)
        except BaseError:
            raise

        json_response = self._parse_join_response(resp)

        self.identifier = {
            "card_number": json_response["iso_serial"],
        }
        self.credentials.update(self.identifier)

    def login(self) -> Any:
        return

    def transactions(self) -> list[Transaction]:
        return []

    def transaction_history(self) -> list[Transaction]:
        return []

    def parse_transaction(self, transaction: dict) -> Transaction:
        return Transaction(
            date=arrow.now(),
            points=Decimal("0"),
            description="description",
        )

    def balance(self) -> Optional[Balance]:
        return Balance(
            points=Decimal("0"),
            value=Decimal("0"),
            value_label="",
            vouchers=[],
        )
