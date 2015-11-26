import arrow

from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal


class Omni(Miner):
    def login(self, credentials):
        self.open_url('https://ssl.omnihotels.com/Omni?pagedst=SI')

        login_form = self.browser.get_form('navFormSI')
        login_form['loginName'].value = credentials['email']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        self.open_url('https://ssl.omnihotels.com/Omni?pagedst=SG6&splash=0&remember=on&ref_pagedst=&pagesrc=SI'
                      '&ref_pagesrc=')

        error_box = self.browser.select('p.has-error')
        if error_box and error_box[0].text.strip().startswith('Please check to make sure'):
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        points = extract_decimal(self.browser.select('div.accountSummary > div > div > div > span')[7].text)

        reward = self.calculate_tiered_reward(points, [
            (30, 'Black membership'),
            (10, 'Platinum membership'),
            (0, 'Gold membership'),
        ])

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': reward,
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
