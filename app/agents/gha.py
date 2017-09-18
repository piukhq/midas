from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


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
        points = extract_decimal(self.browser.select('span.l-status-progress-value')[0].text)

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
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
