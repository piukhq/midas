from decimal import Decimal

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
        'points': Decimal('0')
    },
    '111111': {
        'len_transactions': 1,
        'credentials': {
            'email': 'one@testbink.com',
            'password': 'Password01',
            'last_name': 'one',
            'postcode': 'rg1 1aa'
        },
        'points': Decimal('20.10')
    },
    '555555': {
        'len_transactions': 5,
        'credentials': {
            'email': 'five@testbink.com',
            'password': 'Password01',
            'last_name': 'five',
            'postcode': 'rg5 5aa'
        },
        'points': Decimal('380.01')
    },
    '666666': {
        'len_transactions': 6,
        'credentials': {
            'email': 'six@testbink.com',
            'password': 'Password01',
            'last_name': 'six',
            'postcode': 'rg6 6aa'
        },
        'points': Decimal('1480')
    },
    '123456': {
        'len_transactions': 6,
        'credentials': {
            'email': 'sixdigitpoints@testbink.com',
            'password': 'pa$$w&rd01!',
            'last_name': 'million',
            'postcode': 'mp6 0bb'
        },
        'points': Decimal('123456')
    },
    '234567': {
        'len_transactions': 6,
        'credentials': {
            'email': 'sevendigitpoints@testbink.com',
            'password': 'Password01',
            'last_name': 'seven-digits, smith\'s',
            'postcode': 'mp7 1bb'
        },
        'points': Decimal(1234567)
    },
}


transactions = [
    {
        "date": arrow.get('01/07/2018 14:24:15', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 1 item',
        "points": Decimal('20.71'),
    },
    {
        "date": arrow.get('02/08/2018 12:11:30', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 3 items',
        "points": Decimal('100.01'),
    },
    {
        "date": arrow.get('03/09/2018 22:05:45', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 5 items',
        "points": Decimal('200'),
    },
    {
        "date": arrow.get('04/09/2018 16:55:00', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 2 items',
        "points": Decimal('50'),
    },
    {
        "date": arrow.get('04/09/2018 07:35:10', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 1 item',
        "points": Decimal('10'),
    },
    {
        "date": arrow.get('05/09/2018 11:30:50', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 20 items',
        "points": Decimal('1100'),
    },
]


def get_user(card_number):
    try:
        return users[card_number]
    except (KeyError, TypeError):
        raise LoginError(STATUS_LOGIN_FAILED)


class TestAgentHN(ApiMiner):
    retry_limit = None

    def login(self, credentials):
        for user, info in users.items():
            check_email = info['credentials']['email']
            check_password = info['credentials']['password']
            if credentials['email'] == check_email and credentials['password'] == check_password:
                self.user_info = info
                self.customer_number = user
                break

        else:
            raise LoginError(STATUS_LOGIN_FAILED)

        card_number_mapping = {
            '000000': '0000000000000',
            '111111': '1111111111111',
            '555555': '5555555555555',
            '666666': '6666666666666',
            '123456': '1020304056666',
            '234567': '1020304057777',
        }
        self.customer_number = card_number_mapping[self.customer_number]

        if credentials.get('card_number') != self.customer_number:
            self.identifier = {'card_number': self.customer_number}

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
    retry_limit = None
    point_conversion_rate = Decimal('1')

    def login(self, credentials):
        card_number = credentials.get('card_number') or credentials.get('barcode')
        card_number_mapping = {
            '0000000000000000000': '000000',
            '1111111111111111111': '111111',
            '5555555555555555555': '555555',
            '6666666666666666666': '666666',
            '1020304050607086666': '123456',
            '1020304050607087777': '234567',
        }
        try:
            card_number = card_number_mapping[card_number]
        except (KeyError, TypeError):
            raise LoginError(STATUS_LOGIN_FAILED)

        self.user_info = get_user(card_number)
        login_credentials = (credentials['last_name'].lower(), credentials['postcode'].lower())
        auth_check = (self.user_info['credentials']['last_name'], self.user_info['credentials']['postcode'])

        if login_credentials != auth_check:
            raise LoginError(STATUS_LOGIN_FAILED)

        return

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points)

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
    retry_limit = None
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        card_number = credentials.get('card_number') or credentials.get('barcode')
        card_number_mapping = {
            '00000000': '000000',
            '11111111': '111111',
            '55555555': '555555',
            '66666666': '666666',
            '1026666': '123456',
            '1027777': '234567',
        }
        try:
            card_number = card_number_mapping[card_number]
        except (KeyError, TypeError):
            raise LoginError(STATUS_LOGIN_FAILED)

        self.user_info = get_user(card_number)
        if credentials['email'].lower() != self.user_info['credentials']['email']:
            raise LoginError(STATUS_LOGIN_FAILED)

        return

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points)

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
