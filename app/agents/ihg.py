from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Ihg(Miner):
    def login(self, credentials):
        self.open_url('http://www.ihg.com/rewardsclub/gb/en/sign-in/?'
                      'fwdest=https://www.ihg.com/rewardsclub/gb/en/account/home')

        login_form = self.browser.get_form('walletLoginForm')
        login_form['emailOrPcrNumber'] = credentials['username']
        login_form['password'] = credentials['pin']
        self.browser.submit_form(login_form)

        error_box = self.browser.select('#loginError > div.alert-content')
        if error_box:
            message = error_box[0].text.strip()
            failures = [
                'We cannot find the email address',
                'The IHG® Rewards Club Member Number, email address or PIN provided',
                'Your PIN must be 4-digits in length.'
            ]

            if any(message.startswith(x) for x in failures):
                raise LoginError(STATUS_LOGIN_FAILED)

        self.browser.submit_form(self.browser.get_form(action='https://www.ihg.com/rewardsclub/gb/en/account/home'))

    def balance(self):
        point_text = self.browser.select('#reflectionBg > div > div.value.large.withCommas')[0].text.strip()
        return {
            'points': extract_decimal(point_text),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['datePostedFormatted'], 'DD-MMM-YYYY'),
            'description': row['description'],
            'points': Decimal(row['totalPointValue']),
        }

    def scrape_transactions(self):
        self.open_url('https://www.ihg.com/rewardsclub/gb/en/ws/accountActivity/get'
                      '?activityType=ALL&duration=365&rows=10&page=1')
        data = self.browser.response.json()
        return data['accountActivityList']
