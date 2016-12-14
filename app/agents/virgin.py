import re
from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Virgin(Miner):
    point_value_pattern = re.compile(r'"smBalance":"(\d+)"')
    login_result_pattern = re.compile(r'"loggedIn":[a-z]+')

    def login(self, credentials):
        data = credentials
        self.browser.open('https://www.virginatlantic.com/custlogin/login.action', method='post', data=data)
        self.open_url('https://www.virginatlantic.com')

        pretty_html = self.browser.parsed.prettify()
        result = self.login_result_pattern.findall(pretty_html)[0]
        if result[-5:] == 'false':
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        pretty_html = self.browser.parsed.prettify()

        points = self.point_value_pattern.findall(pretty_html)[0]

        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row.contents[1].text.strip(), 'DD MMM YYYY'),
            'description': row.contents[3].text.strip(),
            'points': extract_decimal(row.contents[5].text.strip()),
        }

    def scrape_transactions(self):
        return self.browser.select('#account table.centerTable.tableCopy.borderPurple.boxContainer tr')[1:]
