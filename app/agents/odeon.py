from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Odeon(Miner):
    def login(self, credentials):
        self.open_url('https://www.odeon.co.uk')

        login_form = self.browser.get_form('login-header')
        login_form['username'].value = credentials['email']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        error_box = self.browser.select('.error')
        if len(error_box) > 0:
            raise LoginError(STATUS_LOGIN_FAILED)

    def calculate_label(self, points):
        return self.calculate_tiered_reward(points, [
            (1200, 'Free movie ticket'),
            (1000, 'Family mix'),
            (800, 'Large hot dog combo'),
            (750, 'Large popcorn combo'),
            (700, 'Medium popcorn combo'),
            (400, 'Small popcorn'),
            (300, 'Small soft drink'),
        ])

    def balance(self):
        points = extract_decimal(self.browser.select('div.span7 span')[0].text)
        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.calculate_label(points),
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('div.attr')

        positive_points = get_points(data[2])
        negative_points = get_points(data[3])

        return {
            'date': arrow.get(data[0].contents[0].strip(), 'DD/MM/YYYY'),
            'description': data[1].select('b')[0].contents[0].strip(),
            'points': positive_points - negative_points
        }

    def scrape_transactions(self):
        self.open_url('https://www.odeon.co.uk/my-odeon/dashboard/my-opc/')
        return self.browser.select('div.points-transactions')[0].select('div.row')[1:]


def get_points(data):
    holder = data.select('b')[0]
    if len(holder.contents) > 0:
        return extract_decimal(holder.contents[0].strip())
    else:
        return Decimal(0)
