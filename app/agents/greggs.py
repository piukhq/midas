from app.agents.base import Miner
from app.agents.exceptions import LoginError, END_SITE_DOWN, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
from collections import Counter
import arrow


class Greggs(Miner):
    def login(self, credentials):
        url = 'https://www.greggs.co.uk/Security/login?BackURL=%2Fhome%2F&ajax=1'
        self.open_url(url)

        if self.browser.response.status_code != 200:
            raise LoginError(END_SITE_DOWN)

        login_form = self.browser.get_form(id='AccountLoginForm_LoginForm')
        login_form['Email'].value = credentials['email']
        login_form['Password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = '#AccountLoginForm_LoginForm_error'
        self.check_error('/Security/login', ((selector, STATUS_LOGIN_FAILED, "The details you entered don't seem"),))

    def balance(self):
        self.open_url('https://www.greggs.co.uk/my-account/my-coffees#content_start')
        coffees = self.browser.select('ul#coffee li')
        points = Decimal(len([x for x in coffees if 'done' in x.attrs['class']]))

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '{}/7 towards a free coffee'.format(points),
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
        return self.browser.select('#page_account_purchase_history > table > tbody > tr')
