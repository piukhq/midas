from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal


class Esprit(RoboBrowserMiner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        self.open_url('https://www.esprit.co.uk/my-esprit/epoints')

        login_form = self.browser.get_form('login_form')
        login_form['username'].value = credentials['username']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        selector = 'p.loginErrors__error'
        self.check_error('/myaccount/check',
                         ((selector, STATUS_LOGIN_FAILED, 'The combination of Esprit Friends number'),))

    def balance(self):
        points = extract_decimal(self.browser.select('#epoint-status h3.page_subtitle span')[0].text)
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
