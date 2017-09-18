from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class SpaceNK(RoboBrowserMiner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        query = 'https://cws.givex.com/cws/spacenk_uk/consumer/clp/balance_check.py'
        data = {
            '_FUNCTION_': 'balance',
            'history_type': 'loyalty',
            'cardnum': credentials['barcode'],
            'balance_check': 'Check+Balance',
            'form_submit': 't',
        }

        self.open_url(query, method='post', data=data)

        error = self.browser.select('span.errorText')
        if len(error) > 0 and 'Invalid N.dulge Card number.' in error[0].text:
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        elements = self.browser.select('#main table tr td.structured-list-value')
        value = extract_decimal(elements[1].text)
        return {
            'points': extract_decimal(elements[2].text),
            'value': value,
            'value_label': '£{}'.format(value),
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
