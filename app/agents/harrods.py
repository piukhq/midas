from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import json
import arrow


class Harrods(Miner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        query = 'https://www.harrods.com/UIServices/Account/AccountService.svc/Signin'
        data = {
            'email': credentials['email'],
            'password': credentials['password'],
        }

        self.browser.open(query, method='post', json=data)
        response = json.loads(self.browser.response.text)

        if not response['d']['isValid']:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.open_url('https://www.harrods.com/Pages/Account/Secure/AccountHome.aspx')

    def balance(self):
        points = extract_decimal(self.browser.select('div.myaccount_option_boxes_inner p')[2].contents[10])
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value)
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        # self.open_url('https://www.harrods.com/Pages/Account/Secure/StatementTransactions.aspx')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]