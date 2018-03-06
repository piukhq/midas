from decimal import Decimal

import arrow

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Quidco(RoboBrowserMiner):
    transaction_rows = []

    def login(self, credentials):
        self.open_url('https://www.quidco.com/sign-in/?sign_in_redirect_path=%2Factivity%2F')

        login_form = self.browser.get_form('sign-in-page-form')
        login_form['username'].value = credentials['username']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = 'div.alert'
        self.check_error('/sign-in/', ((selector, STATUS_LOGIN_FAILED, 'Invalid username'),))

        # check for the interstitial page.
        interstitial = self.browser.select('.mixpanel-interstitial-continue')
        if interstitial:
            self.browser.follow_link(interstitial[0])

        # Every second row is a hidden element we can't parse, so skip it.
        self.open_url("https://www.quidco.com/activity/")
        self.transaction_rows = self.browser.select('.activity-row')[1:]

    def balance(self):
        self.open_url('https://www.quidco.com/ajax/main_nav/get_cashback_summary')
        points = Decimal(self.browser.response.json()['total_cashback_earned'])
        return {
            'points': points,
            'value': points,
            'value_label': '£{}'.format(points),
        }

    @staticmethod
    def parse_transaction(row):
        data = [
            item
            for item in row.text.replace(' ', '').split('\n')
            if item
        ]

        return {
            'date': arrow.get(data[0], 'DDMMMYY'),
            'description': "%s, status: %s" % (data[1], data[4]),
            'points': extract_decimal(data[3]),
        }

    def scrape_transactions(self):
        return self.transaction_rows
