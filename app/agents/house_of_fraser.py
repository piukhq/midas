from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
import re


class HouseOfFraser(Miner):
    error_message_pattern = re.compile(r'showErrorMsg\("","(.*)"\)')

    def login(self, credentials):
        self.open_url('https://www.houseoffraser.co.uk/on/demandware.store/Sites-hof-Site/default/Login-Show')

        login_form = self.browser.get_form('dwfrm_login')
        login_form['dwfrm_login_username'].value = credentials['email']
        login_form['dwfrm_login_password'].value = credentials['password']
        self.browser.submit_form(login_form, login_form.submit_fields['dwfrm_login_login'])

        # The error message box on the page is filled out with javascript.
        error_message = self.error_message_pattern.findall(self.browser.parsed.text)
        if error_message:
            if error_message[0].startswith('Uh oh. The email/password combination'):
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

    def balance(self):
        self.open_url('https://www.houseoffraser.co.uk/on/demandware.store/Sites-hof-Site/default/Loyalty-ViewSummary')
        loyalty_data_elements = self.browser.select('td.hof-title.text-align-right.compact')
        value = extract_decimal(loyalty_data_elements[1].text.strip())
        return {
            'points': extract_decimal(loyalty_data_elements[0].text.strip()),
            'value': value,
            'value_label': '£{}'.format(value),
        }

    def transactions(self):
        return None
