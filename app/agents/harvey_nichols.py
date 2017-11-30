from decimal import Decimal
import arrow

from app.agents.base import ApiMiner


class HarveyNichols(ApiMiner):

    def login(self, credentials):
        self.identifier_type = 'card_number'

        if self.identifier_type not in credentials:
            self.identifier = '989080908'

        return True

    def balance(self):
        return {
            'points': Decimal('100'),
            'value': Decimal('0'),
            'value_label': '',
            'reward_tier': 0
        }

    @staticmethod
    def parse_transaction(row):
        return {'date': row[0],
                'description': row[1],
                'points': row[2]}

    def scrape_transactions(self):
        t = [[arrow.get(x), 'placeholder', Decimal(x)] for x in range(5)]
        return t

    def register(self, credentials):
        return {"message": "success"}
