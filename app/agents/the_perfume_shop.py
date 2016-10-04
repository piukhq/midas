from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN
import arrow


class ThePerfumeShop(Miner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        self.open_url('https://www.theperfumeshop.com/my-account/loyalty')

        login_form = self.browser.get_form('loginForm')
        login_form['j_username'].value = credentials['email']
        login_form['j_password'].value = credentials['password']
        self.browser.submit_form(login_form)
        print(self.browser.url)

        self.check_error('/login',
                         (('span.message-box.error.show', STATUS_LOGIN_FAILED, 'There was an error'), ))

    def balance(self):
        points = extract_decimal(self.browser.select('p.p-points-balance--amount')[0].text)
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
        # self.open_url('https://www.theperfumeshop.com/my-account/orders')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
