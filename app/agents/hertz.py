from decimal import ROUND_DOWN, Decimal

import arrow

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError


class Hertz(RoboBrowserMiner):
    point_conversion_rate = 1 / Decimal('900')
    account_data = None

    def login(self, credentials):
        data = {
            "loginCreateUserID": "false",
            "loginId": credentials['username'],
            "password": credentials['password'],
            "cookieMemberOnLogin": False,
            'enteredcaptcha': 'null',
            "loginForgotPassword": ""
        }

        self.browser.open('https://www.hertz.co.uk/rentacar/member/authentication', method='post', data=data)

        if self.browser.response.status_code != 200:
            raise LoginError(STATUS_LOGIN_FAILED)

        # It is found that with User_Agent is passed via requests (and hence Robo browser) that Hertz page fails to
        # respond and times out.  This seems to be a combination of Requests and Hertz.  It cannot be simulated
        # in postman which works with same header!  The fix sets the the header to None so it will not be sent when
        # requesting the statement. The login URL is not adversely affected by the user agent but other urls appear to
        # be. (released on hotfix/1.9.4-SCRAPE-146-Hertz-Agent branch  ie See Jira SCRAPE-146 for issues and comments)
        self.browser.session.headers['User-Agent'] = None

        self.browser.open('https://www.hertz.co.uk/rentacar/rest/member/rewards/statement')
        self.account_data = self.browser.response.json()

    def balance(self):
        points = Decimal(self.account_data['data']['totalPoints'])
        reward_qty = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.format_label(reward_qty, 'reward rental day'),
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['date'], 'DD MMM YYYY'),
            'description': '{} - {}'.format(row['desc'], row['type']),
            'points': Decimal(row['points']),
        }

    def scrape_transactions(self):
        transactions = []
        month = arrow.utcnow()
        for _ in range(3):
            url = 'https://www.hertz.co.uk/rentacar/rest/member/rewards/statement/{}'.format(month.format('YYYY-MM'))
            self.browser.open(url)
            transactions.extend(self.browser.response.json()['data'].get('transactions', []))
            month = month.replace(months=-1)

        return transactions
