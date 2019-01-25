from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from decimal import Decimal
import arrow


class Paperchase(RoboBrowserMiner):
    def login(self, credentials):
        form = 'https://www.paperchase.com/en_gb//treat-me/ajax/login'
        headers = {"X-Requested-With": "XMLHttpRequest"}
        self.open_url(
            form,
            method='post',
            json={
                'username': credentials['email'],
                'password': credentials['password']
            },
            headers=headers)
        json = self.browser.response.json()

        if json['errors']:
            if json['message'] == 'Invalid login or password.':
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

    def balance(self):
        self.open_url('https://www.paperchase.co.uk/treat-me/balance/account/')
        stamps = self.browser.select('div#spend-more-block-id > div.future-promo > div.promo-stamp > span.spent')
        num_spent = len(stamps)

        return {
            'points': Decimal(num_spent),
            'value': Decimal('0'),
            'value_label': '{}/10 stamps towards your next treat'.format(num_spent),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # self.open_url('https://www.paperchase.co.uk/sales/order/history')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
