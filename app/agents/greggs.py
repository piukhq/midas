from app.agents.base import Miner
from app.agents.exceptions import LoginError, PASSWORD_EXPIRED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal
from collections import Counter
import arrow


class Greggs(Miner):
    def login(self, credentials):
        self.open_url('https://api.greggs.co.uk/1.0/user/login', method='post', json=credentials)

        response = self.browser.response.json()
        if response['error'] == 'invalid_grant':
            if response['error_description'] == 'Migrated user':
                raise LoginError(PASSWORD_EXPIRED)
            else:
                raise LoginError(UNKNOWN)

    def balance(self):
        self.open_url('https://www.greggs.co.uk/my-account/my-coffees#content_start')
        coffees = self.browser.select('ul#coffee li')
        points = Decimal(len([x for x in coffees if 'done' in x.attrs['class']]))

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '{}/7 coffees'.format(points),
            'balance': extract_decimal(self.browser.select('p.current_balance_amount strong span')[0].text),
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')

        """
        Calling most_common sorts the Counter's contents, ensuring the order of items in the description of a single
        transaction never changes.
        """
        item_counts = Counter(data[2].contents[0::2]).most_common()

        return {
            'date': arrow.get('{} {}'.format(data[0].text, data[1].text), 'DD/MM/YYYY h:mma'),
            'description': ', '.join('{} x{}'.format(item, qty) for (item, qty) in item_counts),
            'points': Decimal('0'),
        }

    def scrape_transactions(self):
        self.open_url('https://www.greggs.co.uk/my-account/purchase-history#content_start')

        data = self.browser.select('#page_account_purchase_history > table > tbody > tr')

        if data[0].select('td')[0].text == 'You have no purchase history for this month':
            return []

        return data
