from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, STATUS_ACCOUNT_LOCKED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Lufthansa(Miner):
    def login(self, credentials):
        self.open_url('https://www.miles-and-more.com/online/myportal/mam/uk/account/account_statement')

        # Both the form's ID and its field names are partially scrambled.
        login_form = self.browser.get_form('PC_7_CO19VHUC6NQ4B0APSQO3UH2QM50n3046_mam-usm-cardnr-form')
        login_form['PC_7_CO19VHUC6NQ4B0APSQO3UH2QM50n3046_userId'] = credentials['card_number']
        login_form['PC_7_CO19VHUC6NQ4B0APSQO3UH2QM50n3046_password'] = credentials['pin']
        self.browser.submit_form(login_form)

        errors = [
            'Please check your Miles & More service card number',
            'Invalid PIN. Please try again',
            'Your login details are incorrect.'
        ]

        error_box = self.browser.select('span.alert-label')
        if len(error_box) > 0:
            for error in errors:
                if error_box[0].text.startswith(error):
                    raise LoginError(STATUS_LOGIN_FAILED)
        elif self.browser.url.startswith('https://www.miles-and-more.com/online/portal/mam/uk/homepage'):
            raise LoginError(STATUS_ACCOUNT_LOCKED)

    def balance(self):
        miles_elements = self.browser.select('div.account-status dl.dl-horizontal dd')
        award_miles = extract_decimal(miles_elements[0].text)
        status_miles = extract_decimal(miles_elements[1].text)
        return {
            'points': award_miles + status_miles,
            'value': Decimal('0'),
            'value_label': '{} miles'.format(award_miles + status_miles),
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')

        award_miles = ''.join([t.text for t in data[2].select('span')])
        if not award_miles:
            award_miles = '0'

        status_miles = ''.join([t.text for t in data[3].select('span')])
        if not status_miles:
            status_miles = '0'

        return {
            'date': arrow.get(data[0].text, 'DD/MM/YYYY'),
            'description': data[1].text,
            'points': extract_decimal(award_miles) + extract_decimal(status_miles)
        }

    def scrape_transactions(self):
        return self.browser.select('table tbody tr')
