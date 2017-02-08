import arrow
import re

from app.agents.base import Miner
from app.agents.exceptions import STATUS_ACCOUNT_LOCKED, STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal


class Boots(Miner):
    login_result_pattern = re.compile(r'hello')
    login_locked_result_pattern = re.compile(r'Account locked')
    points_result_pattern = re.compile(r'You have <span class="bold_span">([0-9]+)</span> points')
    value_result_pattern =  re.compile(r'worth <span class="bold_span">£([0-9]+\.[0-9]+)</span>')
    def login(self, credentials):
        self.open_url('http://www.boots.com/LogonForm?catalogId=28501&myAcctMain=1&langId=-1&storeId=11352')

        login_form = self.browser.get_form('Logon')
        login_form['logonId'].value = credentials['email']
        login_form['logonPassword'].value = credentials['password']

        self.browser.submit_form(login_form)
        pretty_html = self.browser.parsed.prettify()
        result = self.login_result_pattern.findall(pretty_html)
        if len(result) > 0:
            if result[0] == 'hello':
                pass # Login success
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        else:
            result = self.login_locked_result_pattern.findall(pretty_html)
            if len(result) > 0:
                if result[0] == 'Account locked':
                    raise LoginError(STATUS_ACCOUNT_LOCKED)
            else:
                raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        elements = self.browser.select("p#advantageCardDetails")
        points = self.points_result_pattern.findall(str(elements[0]))
        true_points = extract_decimal(points[0])
        value = self.value_result_pattern.findall(str(elements[0]))
        true_value = extract_decimal(value[0])

        return {
            'points': true_points,
            'value': true_value,
            'value_label': '£{}'.format(true_value)
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")

        return {
            "date": arrow.get(items[0].contents[0], 'DD/MM/YYYY'),
            "description": items[1].contents[0],
            "points": extract_decimal(items[3].contents[0]),
        }

    def scrape_transactions(self):
        self.open_url('https://www.boots.com/ADCAccountSummary')
        return self.browser.select("#adcardPointStatement tr")[1:]
