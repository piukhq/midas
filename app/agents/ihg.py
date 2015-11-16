from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class IHG(Miner):
    def login(self, credentials):
        url = 'https://www.ihg.com/rewardsclub/gb/en/sign-in/?fwdest=https://www.ihg.com/rewardsclub/gb/en/account/home'
        data = {
            "formSubmit": "true",
            "currentUrl": ("https%3A%2F%2Fwww.ihg.com%2Frewardsclub%2Fgb%2Fen%2Fsign-in%2F%3Ffwdest%3Dhttps%3A%2F%2Fwww"
                           ".ihg.com%2Frewardsclub%2Fgb%2Fen%2Faccount%2Fhome"),
            "emailOrPcrNumber": credentials['email'],
            "password": credentials['pin'],
            "signInButton": "Sign+In",
        }

        self.browser.open(url, method='post', data=data)

        message = 'We cannot find the email address you entered in our system.'
        error_message = self.browser.select('#loginError > div.alert-content')
        if error_message and error_message[0].text.strip().startswith(message):
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

    def transactions(self):
        self.open_url('https://www.ihg.com/rewardsclub/gb/en/ws/accountActivity/get'
                      '?activityType=ALL&duration=365&rows=10&page=1')
        data = self.browser.response.json()

        return [self.hashed_transaction(row) for row in data['accountActivityList']]
