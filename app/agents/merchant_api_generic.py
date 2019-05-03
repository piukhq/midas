from decimal import Decimal

import arrow

from app.agents.base import MerchantApi
from app.utils import TWO_PLACES


class MerchantAPIGeneric(MerchantApi):
    retry_limit = 9    # tries 10 times overall

    def balance(self):
        value = Decimal(self.result['balance']).quantize(TWO_PLACES)
        return {
            "points": value,
            "value": value,
            "value_label": '£{}'.format(value),
        }

    def scrape_transactions(self):
        return self.result['transactions']

    @staticmethod
    def parse_transaction(row):
        return {
            "date": arrow.get(row['timestamp']),
            "description": row['reference'],
            "points": Decimal(row['value']),
        }
