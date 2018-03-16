from decimal import Decimal

import arrow

from app.agents.base import MerchantApi


class BasicMerchant(MerchantApi):
    def balance(self):
        return {
            'points': Decimal(self.result['balance']['unit']),
            'value': Decimal(self.result['balance']['value']),
            'value_label': '',
        }

    def scrape_transactions(self):
        return self.result['transactions']

    @staticmethod
    def parse_transactions(row):
        return {
            "date": arrow.get(row['timestamp']),
            "description": row['reference'],
            "points": Decimal(row['unit']),
        }
