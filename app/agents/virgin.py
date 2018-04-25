from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Virgin(RoboBrowserMiner):
    is_login_successful = False
    json_response = None

    def check_if_logged_in(self):
        self.json_response = self.browser.response.json()

        if self.json_response['loggedIn']:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        self.browser.open('https://www.virginatlantic.com/')

        login_form = self.browser.get_form(action='https://www.virginatlantic.com/custlogin/login.action')
        login_form['username'] = credentials['username']
        login_form['password'] = credentials['password']
        self.browser.submit_form(login_form)

        self.browser.open('https://www.virginatlantic.com/custlogin/getDashBrdData.action', method='post')

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        points = self.json_response['smBalance']

        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all('td')
        return {
            'date': Virgin.clean_date(items[0].contents[0]),
            'description': Virgin.clean_description(items[1].text),
            'points': extract_decimal(items[2].contents[0].strip()),
        }

    @staticmethod
    def clean_date(date):
        date = arrow.get(date.strip(), 'DD/MM/YY')
        return date

    @staticmethod
    def clean_description(description):
        description = description.replace('\xa0►\xa0', ' > ')
        return description.strip()

    def scrape_transactions(self):
        self.open_url('https://www.virginatlantic.com/myprofile/displayMySkyMiles.action')
        return self.browser.select('.myAccountStatement')
