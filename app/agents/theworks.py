import json
import uuid
from decimal import Decimal
from typing import Any, Optional

import arrow
from blinker import signal
from soteria.configuration import Configuration

import settings
from app import db
from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.exceptions import AccountAlreadyExistsError, BaseError, CardNumberError, JoinError
from app.reporting import get_logger
from app.retry_util import get_task
from app.scheme_account import JourneyTypes

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
        self.audit_config = {
            "type": "jsonrpc",
            "audit_sensitive_keys": [2, 3],  # positions containing sensitive fields sanitised for audit
            "audit_keys_mapping": {
                # key: positions containing searchable fields for atlas - value: atlas-readable field names
                "REQUEST": {6: "email", 8: "first_name", 10: "last_name"},
                "RESPONSE": {6: "card_number"},
            },
        }
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
                transaction_code,  # customer password
                "",  # customer mobile
                "",  # customer company
                "",  # security code
                new_card_request,  # new card request
            ],
        }

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

        self.identifier = {
            "card_number": json_response["iso_serial"],
            "barcode": json_response["iso_serial"],
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
