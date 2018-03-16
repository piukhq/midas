import re

from decimal import Decimal
from urllib.parse import urlsplit

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, AgentModifiedError
from app.utils import extract_decimal


class Hyatt(RoboBrowserMiner):

    def get_csrf(self):
        self.open_url('https://www.hyatt.com/home')
        form = self.browser.get_form(action='https://www.hyatt.com/auth/web/login')
        return form['csrf'].value

    def is_login_failed(self):
        parts = urlsplit(self.browser.url)
        expected_url = '/home'
        return expected_url != parts.path

    def login(self, credentials):
        data = dict(
            error_url='https://world.hyatt.com/content/gp/en/signin-error.html',
            temporary_url='https://world.hyatt.com/content/gp/en/signin-temp.html',
            return_url='https://www.hyatt.com/home',
            csrf=self.get_csrf(),
            username=credentials['username'],
            last_name=credentials['last_name'],
            password=credentials['password'],
            remember='false',
            language='en-US'
        )

        self.browser.open('https://www.hyatt.com/auth/web/login', method='POST', data=data,
                          headers={
                              'Referer': 'https://www.hyatt.com/',
                          })

        if self.is_login_failed():
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        # data is in the header
        self.open_url('https://www.hyatt.com/home')
        selector = '.admin-row .dd-menu .pc2 > dl.definition-table'
        points_table = self.browser.select(selector)

        if len(points_table) != 2:
            raise AgentModifiedError('End-site has been modified')

        data_table = str(points_table[1]).replace('\n', '')
        expr = '<dt>Current\sPoints:</dt><dd>(\d+)</dd>'
        searched = re.search(expr, data_table, re.IGNORECASE)

        if len(searched.groups()) != 1:
            raise AgentModifiedError('End-site has been modified')

        points = searched.group(1)  # matched points data

        return {
            'points': extract_decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    def scrape_transactions(self):
        return None
