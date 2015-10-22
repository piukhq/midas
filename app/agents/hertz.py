from app.agents.base import Miner
from robobrowser.forms import Form
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Hertz(Miner):
    def login(self, credentials):
        self.open_url('https://www.hertz.co.uk/rentacar/emember/modify/statementTab')

        post_params = {
            "loginCreateUserID": "false",
            "loginId": credentials['email'],
            "password": credentials['password'],
            "cookieMemberOnLogin": False,
            "loginForgotPassword": ""
        }

        self.browser.session.post(self.browser.url, post_params)

        selector = '.field-error-list li'
        self.check_error('/rentacar/member/login.do', ((selector, STATUS_LOGIN_FAILED, 'Member Number'),))

    def balance(self):
        point_holder = self.browser.select('#section.account-Info span strong')[0]
        return {
            'points': extract_decimal(point_holder.text)
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
