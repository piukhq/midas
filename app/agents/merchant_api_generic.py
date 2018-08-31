from decimal import Decimal

import arrow

from app.agents.base import MerchantApi


class MerchantAPIGeneric(MerchantApi):
    def balance(self):
        return {
            "points": Decimal(self.result['balance']),
            "value": Decimal(0),
            "value_label": '',
        }

    def scrape_transactions(self):
        return self.result['transactions']

    @staticmethod
    def parse_transactions(row):
        return {
            "date": arrow.get(row['timestamp']),
            "description": row['reference'],
            "points": Decimal(row['value']),
        }
