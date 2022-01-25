from decimal import Decimal
from typing import Optional

import arrow

from app.agents.base import Balance, MerchantApi, Transaction
from app.scheme_account import TWO_PLACES


class MerchantAPIGeneric(MerchantApi):
    def balance(self) -> Optional[Balance]:
        value = Decimal(self.result["balance"]).quantize(TWO_PLACES)
        return Balance(
            points=value,
            value=value,
            value_label="£{}".format(value),
        )

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception:
            return []

    def transaction_history(self) -> list[Transaction]:
        return [self.parse_transaction(tx) for tx in self.result["transactions"]]

    def parse_transaction(self, row: dict) -> Transaction:
        return Transaction(
            date=arrow.get(row["timestamp"]),
            description=row["reference"],
            points=Decimal(row["value"]),
        )
