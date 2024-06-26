import random
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import arrow

from app.agents.base import MockedMiner
from app.agents.schemas import Balance, Transaction, Voucher
from app.exceptions import GeneralError, PreRegisteredCardError
from app.vouchers import VoucherState, voucher_state_names

GHOST_CARD_PREFIX = "0"


class MockPerformance(MockedMiner):
    point_conversion_rate = Decimal("1")

    def login(self):
        if not self.credentials.get("card_number"):
            self.identifier = {"card_number": f"1{uuid4()}"}
            return

        if self.credentials["card_number"].startswith(GHOST_CARD_PREFIX):
            raise PreRegisteredCardError()

        return

    def balance(self) -> Optional[Balance]:
        points = Decimal(random.randint(1, 50))
        self.calculate_point_value(points)

        return Balance(
            points=points,
            value=points,
            value_label=f"£{points}",
        )

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception:
            return []

    def parse_transaction(self, row: dict) -> Transaction:
        return Transaction(
            date=row["date"],
            description=row["description"],
            points=row["points"],
        )

    def transaction_history(self) -> list[Transaction]:
        transactions = []
        for count in range(5):
            transactions.append(
                {
                    "date": arrow.utcnow().shift(days=-count).format("YYYY-MM-DD HH:mm:ss"),
                    "description": f"Test Transaction: {uuid4()}",
                    "points": Decimal(random.randint(1, 50)),
                }
            )
            transactions_list = [self.parse_transaction(raw_tx) for raw_tx in transactions]

        return transactions_list

    def join(self):
        if "failure" in self.credentials["password"].lower():
            raise GeneralError()

        return {"message": "success"}


class MockPerformanceVoucher(MockedMiner):
    def login(self):
        if not self.credentials.get("card_number"):
            self.identifier = {"card_number": f"1{uuid4()}"}
            return

        if self.credentials.get("card_number", "").startswith(GHOST_CARD_PREFIX):
            raise PreRegisteredCardError()

        return

    def balance(self) -> Optional[Balance]:
        value = Decimal(random.randint(1, 50))
        vouchers = []
        for count in range(2):
            date = arrow.now().shift(days=-count).int_timestamp
            vouchers.append(
                Voucher(
                    state=voucher_state_names[VoucherState.ISSUED],
                    issue_date=date,
                    redeem_date=date,
                    expiry_date=date,
                    code=str(uuid4()),
                    value=Decimal(random.randint(1, 50)),
                )
            )

        return Balance(
            points=value,
            value=value,
            value_label="",
            vouchers=vouchers,
        )

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception:
            return []

    def parse_transaction(self, row: dict) -> Optional[Transaction]:
        return None

    def transaction_history(self) -> list[Transaction]:
        return []

    def join(self):
        if "failure" in self.credentials["password"].lower():
            raise GeneralError()

        return {"message": "success"}
