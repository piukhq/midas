from decimal import Decimal

import arrow

from app.agents.base import ApiMiner


class TestAgentHN(ApiMiner):

    def login(self, credentials):
        pass

    def balance(self):
        return {
            'points': Decimal(2000),
            'value': Decimal(2000),
            'value_label': '',
            'reward_tier': 1
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return [
            {
                "date": arrow.get('03/09/2018'),
                "description": 'test transaction 1: knightsbridge',
                "points": Decimal(900),
            },
            {
                "date": arrow.get('02/08/2018'),
                "description": 'test transaction 2: knightsbridge',
                "points": Decimal(300),
            },
            {
                "date": arrow.get('01/07/2018'),
                "description": 'test transaction 3: knightsbridge',
                "points": Decimal(800),
            }
        ]


class TestAgentIce(ApiMiner):

    def login(self, credentials):
        pass

    def balance(self):
        return {
            'points': '200',
            'value': '200',
            'value_label': '£{}'.format(200)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []


class TestAgentCI(ApiMiner):

    def login(self, credentials):
        pass

    def balance(self):
        return {
            'points': '1500',
            'value': '1500',
            'value_label': '£{}'.format(200)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
