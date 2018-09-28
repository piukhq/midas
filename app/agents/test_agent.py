from decimal import Decimal

import arrow

from app.agents.base import ApiMiner


class TestAgentHN(ApiMiner):

    def login(self, credentials):
        pass

    def balance(self):
        return {
            'points': Decimal('2000'),
            'value': Decimal('2000'),
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
                "points": Decimal('900'),
            },
            {
                "date": arrow.get('02/08/2018'),
                "description": 'test transaction 2: knightsbridge',
                "points": Decimal('300'),
            },
            {
                "date": arrow.get('01/07/2018'),
                "description": 'test transaction 3: knightsbridge',
                "points": Decimal('800'),
            }
        ]


class TestAgentIce(ApiMiner):

    def login(self, credentials):
        pass

    def balance(self):
        return {
            'points': Decimal('200.55'),
            'value': Decimal('200.55'),
            'value_label': '£200.55'
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return [
            {
                "date": arrow.get('11/09/2018'),
                "description": 'test transaction 1: North End Road',
                "points": Decimal('80'),
            },
            {
                "date": arrow.get('09/08/2018'),
                "description": 'test transaction 2: North End Road',
                "points": Decimal('100'),
            },
            {
                "date": arrow.get('23/07/2018'),
                "description": 'test transaction 3: North End Road',
                "points": Decimal('20.55'),
            }
        ]


class TestAgentCI(ApiMiner):

    def login(self, credentials):
        pass

    def balance(self):
        return {
            'points': Decimal('1500'),
            'value': Decimal('1500'),
            'value_label': '£1500'
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return [
            {
                "date": arrow.get('25/09/2018'),
                "description": 'test transaction 1',
                "points": Decimal('300'),
            },
            {
                "date": arrow.get('17/09/2018'),
                "description": 'test transaction 2',
                "points": Decimal('700'),
            },
            {
                "date": arrow.get('11/09/2018'),
                "description": 'test transaction 3',
                "points": Decimal('500'),
            }
        ]
