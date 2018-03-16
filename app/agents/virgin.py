import re
import arrow

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal


class Virgin(RoboBrowserMiner):
    point_value_pattern = re.compile(r'"smBalance":"(\d+)"')
    login_result_pattern = re.compile(r'"loggedIn":[a-z]+')

    def login(self, credentials):
        self.open_url('https://www.virginatlantic.com/custlogin/loginPage.action')
        form = self.browser.get_form('loginForm_LoginPage')

        form['username'].value = credentials['username']
        form['password'].value = credentials['password']
        self.browser.submit_form(form)

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
        items = row.find_all('td')
        date_locator = items[0].contents[1]
        description_locator = items[2].contents[1]
        points_locator = items[3].contents[3]
        return {
            'date': arrow.get(date_locator.strip(), 'DD MMMM YYYY'),
            'description': description_locator.strip(),
            'points': extract_decimal(points_locator.text),
        }

    def scrape_transactions(self):
        self.open_url('https://www.virginatlantic.com/acctactvty/manageacctactvty.action')
        table = self.browser.select('table.activityTable')[0]
        rows = table.select('tr')[1:]
        return rows
