from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, AgentError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Ihg(RoboBrowserMiner):
    def login(self, credentials):

        def error_message_check(message):
            known_error_messages = [
                'We cannot find the email address',
                'The IHG Rewards Club member number, email address or pin provided',
                'The page you are trying to view'
            ]

            if any(message.startswith(error) for error in known_error_messages):
                raise LoginError(STATUS_LOGIN_FAILED)

        self.open_url('https://www.ihg.com/rewardsclub/gb/en/account/home')

        login_url = 'https://www.ihg.com/rewardsclub/gb/en/sign-in/?fwdest=' \
                    'https://www.ihg.com/rewardsclub/gb/en/account/home'

        form_fields_html = self.browser.select('div.stand-out > div.form-element')
        for field in form_fields_html:
            field_text = field.select('label.field-label')[0].text
            if field_text.startswith('Email or Member #'):
                user_field = field['class'][2]

            elif field_text.startswith('PIN #'):
                password_field = field['class'][2]

            else:
                empty_form_field = field['class'][2]

        for field_class in user_field, password_field, empty_form_field:
            check = 'pPRfurr'

            if not field_class.startswith(check):
                raise AgentError('Login form classes should start with: "' + check + '". Not found on page')

        headers = {
            'Referer': login_url,
            'Origin': 'https://www.ihg.com'
        }

        data = {
            'formSubmit': 'true',
            'currentUrl': login_url,
            'cookieFlag': 'true',
            user_field: credentials['username'],
            password_field: credentials['pin'],
            empty_form_field: ''
        }

        self.browser.open(login_url, method='post', headers=headers, data=data)

        error_box = self.browser.select('p.error-server')
        long_pin_error_box = self.browser.select('div#tpiSignHeaderCont > p')
        if error_box:
            message = error_box[0].text.strip()
            error_message_check(message)

        elif long_pin_error_box:
            message = long_pin_error_box[0].text.strip()
            error_message_check(message)

        else:
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
