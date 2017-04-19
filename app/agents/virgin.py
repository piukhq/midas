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
        items = row.find_all("td")
        return {
            'date': Virgin.clean_date(items[0].contents[0]),
            'description': Virgin.clean_description(items[1].text),
            'points': extract_decimal(items[2].contents[0].strip()),
        }

    @staticmethod
    def clean_date(date):
        date = arrow.get(date.strip(), "DD/MM/YY")
        return date

    @staticmethod
    def clean_description(description):
        description = description.replace('\xa0►\xa0', " > ")
        return description.strip()

    def scrape_transactions(self):
        self.open_url("https://www.virginatlantic.com/myprofile/displayMySkyMiles.action")
        return self.browser.select('.myAccountStatement')
