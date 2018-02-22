import arrow

from decimal import Decimal

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Gha(RoboBrowserMiner):

    def login(self, credentials):
        url = 'https://www.gha.com/member/login'
        data = {
            'login': credentials['username'],
            'password': credentials['password'],
            'redirect_view': 'reservations',
        }
        self.open_url(url, data=data, method='post')

        self.check_error('/member/login',
                         (('div.Message--error > p', STATUS_LOGIN_FAILED, 'We found errors in the following:'), ))

    def balance(self):
        self.open_url('https://www.gha.com/member/dashboard')
        span = self.browser.select('span.chart__info-strong')[0]
        points = extract_decimal(span.text)

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
