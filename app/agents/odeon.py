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

    def balance(self):
        point_holder = self.browser.select('div.span5 span')[0]
        return {
            'points': extract_decimal(point_holder.text)
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

    def transactions(self):
        self.open_url('https://www.odeon.co.uk/my-odeon/dashboard/my-opc/')
        rows = self.browser.select('div.points-transactions')[0].select('div.row')[1:]
        return [self.hashed_transaction(row) for row in rows]


def get_points(data):
    holder = data.select('b')[0]
    if len(holder.contents) > 0:
        return extract_decimal(holder.contents[0].strip())
    else:
        return Decimal(0)