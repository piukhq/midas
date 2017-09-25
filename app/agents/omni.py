from decimal import Decimal

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal


class Omni(RoboBrowserMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        try:
            logged_in_sign = self.browser.select('h3 a')[0].text
            if logged_in_sign == "Sign Out":
                self.is_login_successful = True
        except:
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):
        self.open_url('https://ssl.omnihotels.com/Omni?pagedst=SI')

        login_form = self.browser.get_form('navFormSI')
        login_form['loginName'].value = credentials['email']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        self.check_if_logged_in()

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

    def scrape_transactions(self):
        return []
