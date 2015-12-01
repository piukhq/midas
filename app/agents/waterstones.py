from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow
import re


class Waterstones(Miner):
    order_id_re = re.compile(r"Order #(.*) \(Placed ")

    def login(self, credentials):
        self.open_url('https://www.waterstones.com/signin')

        login_form = self.browser.get_form('loginForm')
        login_form['email'].value = credentials['email']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = 'p.error'
        self.check_error('/signin', ((selector, STATUS_LOGIN_FAILED, 'Your login details are invalid'),))

    def balance(self):
        self.open_url('https://www.waterstones.com/account/waterstonescard')
        points = extract_decimal(self.browser.select('div.span4 span')[0].text)
        value = extract_decimal(self.browser.select('div.span12 h2')[0].text)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['date'], 'Do MMMM YYYY'),
            'description': row['description'],
            'points': Decimal(row['points']),
        }

    def get_order_details(self, order):
        order_id = self.order_id_re.findall(order.select('p.order-number')[0].text)[0]
        self.open_url('https://www.waterstones.com/account/vieworder/orderid/{}'.format(order_id))

        date = self.browser.select('div.order-row > p.order-number')[0].text.strip()
        description = self.browser.select('div.title > a.link-invert')[0].text.strip()
        points = self.browser.select('div.order-info-section > p > b')[0].text.strip()

        return {
            'date': date,
            'description': description,
            'points': points,
        }

    def scrape_transactions(self):
        self.open_url('https://www.waterstones.com/account/orders')

        orders = self.browser.select(
            'body > div > div.row.main-page > div > div > div.span12.alpha.omega.section > div')
        return [self.get_order_details(order) for order in orders]
