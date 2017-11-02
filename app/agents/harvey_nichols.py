from decimal import Decimal
from app.agents.base import ApiMiner


class HarveyNichols(ApiMiner):

    def login(self, credentials):
        pass

    def balance(self):
        return {
            'points': Decimal('150'),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
