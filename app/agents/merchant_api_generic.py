from decimal import Decimal

import arrow

from app.agents.base import MerchantApi
from app.scheme_account import TWO_PLACES


class MerchantAPIGeneric(MerchantApi):
    def balance(self):
        value = Decimal(self.result["balance"]).quantize(TWO_PLACES)
        return {
            "points": value,
            "value": value,
            "value_label": "£{}".format(value),
        }

    def scrape_transactions(self):
        return self.result["transactions"]

    def parse_transaction(self, row):
        return {
            "date": arrow.get(row["timestamp"]),
            "description": row["reference"],
            "points": Decimal(row["value"]),
        }
