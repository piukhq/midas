from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlsplit
import arrow


class ThePerfumeShop(RoboBrowserMiner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        form = 'https://www.theperfumeshop.com/j_spring_security_check'
        self.open_url(
            form,
            method='post',
            data={
                'j_username': credentials['email'],
                'j_password': credentials['password']
            })
        self.open_url('https://www.theperfumeshop.com/my-account/loyalty')

        parts = urlsplit(self.browser.url)
        if parts.path == '/login':
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        points_locate = 'p.p-points-balance--amount'
        points = extract_decimal(self.browser.select(points_locate)[0].text)
        reward_qty = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.format_label(reward_qty, '£5 voucher')
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        self.open_url('https://www.theperfumeshop.com/my-account/orders')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
