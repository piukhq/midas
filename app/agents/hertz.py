from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from decimal import Decimal, ROUND_DOWN
import arrow
import json


class Hertz(Miner):
    point_conversion_rate = 1 / Decimal('900')

    def login(self, credentials):
        data = {
            "loginCreateUserID": "false",
            "loginId": credentials['email'],
            "password": credentials['password'],
            "cookieMemberOnLogin": False,
            "loginForgotPassword": ""
        }

        self.browser.open('https://www.hertz.co.uk/rentacar/member/authentication', method='post', data=data)

        if self.browser.response.status_code != 200:
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        self.browser.open('https://www.hertz.co.uk/rentacar/member/account/navigation?_=1445528212900')

        response_data = json.loads(self.browser.response.text)
        points = Decimal(response_data['data']['rewardsPoints'])
        reward_qty = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.format_label(reward_qty, 'reward rental day'),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
