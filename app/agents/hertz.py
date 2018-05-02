from decimal import ROUND_DOWN, Decimal

import arrow

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError


class Hertz(RoboBrowserMiner):
    point_conversion_rate = 1 / Decimal('900')
    account_data = None

    def login(self, credentials):
        data = {
            "loginCreateUserID": "false",
            "loginId": credentials['username'],
            "password": credentials['password'],
            "cookieMemberOnLogin": False,
            'enteredcaptcha': 'null',
            "loginForgotPassword": ""
        }

        self.browser.open('https://www.hertz.co.uk/rentacar/member/authentication', method='post', data=data)

        if self.browser.response.status_code != 200:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.browser.open('https://www.hertz.co.uk/rentacar/rest/member/rewards/statement')
        self.account_data = self.browser.response.json()

    def balance(self):
        points = Decimal(self.account_data['data']['totalPoints'])
        reward_qty = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.format_label(reward_qty, 'reward rental day'),
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['date'], 'DD MMM YYYY'),
            'description': '{} - {}'.format(row['desc'], row['type']),
            'points': Decimal(row['points']),
        }

    def scrape_transactions(self):
        transactions = []
        month = arrow.utcnow()
        for _ in range(3):
            url = 'https://www.hertz.co.uk/rentacar/rest/member/rewards/statement/{}'.format(month.format('YYYY-MM'))
            self.browser.open(url)
            transactions.extend(self.browser.response.json()['data'].get('transactions', []))
            month = month.replace(months=-1)

        return transactions
