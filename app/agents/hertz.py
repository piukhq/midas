from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from decimal import Decimal
import arrow
import json


class Hertz(Miner):
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
        return {
            'points': Decimal(response_data['data']['rewardsPoints'])
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
