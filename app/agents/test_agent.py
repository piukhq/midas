from decimal import Decimal, ROUND_DOWN

import arrow

from app.agents.base import ApiMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED


users = {
    '000000': {
        'len_transactions': 0,
        'credentials': {
            'email': 'zero@testbink.com',
            'password': 'Password01',
            'last_name': 'zero',
            'postcode': 'rg0 0aa'
        },
        'points': Decimal(0)
    },
    '111111': {
        'len_transactions': 1,
        'credentials': {
            'email': 'one@testbink.com',
            'password': 'Password01',
            'last_name': 'one',
            'postcode': 'rg1 1aa'
        },
        'points': Decimal(20)
    },
    '555555': {
        'len_transactions': 5,
        'credentials': {
            'email': 'five@testbink.com',
            'password': 'Password01',
            'last_name': 'five',
            'postcode': 'rg5 5aa'
        },
        'points': Decimal(380)
    },
    '666666': {
        'len_transactions': 6,
        'credentials': {
            'email': 'six@testbink.com',
            'password': 'Password01',
            'last_name': 'six',
            'postcode': 'rg6 6aa'
        },
        'points': Decimal(1480)
    },
    '123456': {
        'len_transactions': 6,
        'credentials': {
            'email': 'sixdigitpoints@testbink.com',
            'password': 'Password01',
            'last_name': 'million',
            'postcode': 'mp6 0bb'
        },
        'points': Decimal(123456)
    },
    '234567': {
        'len_transactions': 6,
        'credentials': {
            'email': 'sevendigitpoints@testbink.com',
            'password': 'Password01',
            'last_name': 'smith',
            'postcode': 'mp7 1bb'
        },
        'points': Decimal(1234567)
    },
}


transactions = [
    {
        "date": arrow.get('01/07/2018', 'DD/MM/YYYY'),
        "description": 'Test transaction: 1 item',
        "points": Decimal('20'),
    },
    {
        "date": arrow.get('02/08/2018', 'DD/MM/YYYY'),
        "description": 'Test transaction: 3 items',
        "points": Decimal('100'),
    },
    {
        "date": arrow.get('03/09/2018', 'DD/MM/YYYY'),
        "description": 'Test transaction: 5 items',
        "points": Decimal('200'),
    },
    {
        "date": arrow.get('04/09/2018', 'DD/MM/YYYY'),
        "description": 'Test transaction: 2 items',
        "points": Decimal('50'),
    },
    {
        "date": arrow.get('04/09/2018', 'DD/MM/YYYY'),
        "description": 'Test transaction: 1 item',
        "points": Decimal('10'),
    },
    {
        "date": arrow.get('05/09/2018', 'DD/MM/YYYY'),
        "description": 'Test transaction: 20 items',
        "points": Decimal('1100'),
    },
]


def get_user(credentials):
    try:
        card_number = credentials.get('card_number') or credentials.get('barcode')
        return users[card_number]
    except (KeyError, TypeError):
        raise LoginError(STATUS_LOGIN_FAILED)


class TestAgentHN(ApiMiner):

    def login(self, credentials):
        self.user_info = get_user(credentials)
        login_credentials = (credentials['email'].lower(), credentials['password'])
        auth_check = (self.user_info['credentials']['email'], self.user_info['credentials']['password'])

        if login_credentials != auth_check:
            raise LoginError(STATUS_LOGIN_FAILED)

        return

    def balance(self):
        return {
            'points': self.user_info['points'],
            'value': Decimal(0),
            'value_label': '',
            'reward_tier': 1
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]


class TestAgentIce(ApiMiner):
    point_conversion_rate = Decimal('1')

    def login(self, credentials):
        self.user_info = get_user(credentials)
        login_credentials = (credentials['last_name'].lower(), credentials['postcode'].lower())
        auth_check = (self.user_info['credentials']['last_name'], self.user_info['credentials']['postcode'])

        if login_credentials != auth_check:
            raise LoginError(STATUS_LOGIN_FAILED)

        return

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': self.user_info['points'],
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]


class TestAgentCI(ApiMiner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        self.user_info = get_user(credentials)
        if credentials['email'].lower() != self.user_info['credentials']['email']:
            raise LoginError(STATUS_LOGIN_FAILED)

        return

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': self.user_info['points'],
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]
