from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, STATUS_ACCOUNT_LOCKED
from app.utils import extract_decimal
import arrow


class Lufthansa(Miner):
    def login(self, credentials):
        self.open_url('https://www.miles-and-more.com/online/myportal/mam/uk/account/account_statement?l=en'
                      '&cid=1000243&WT.mc_id=MmhpabMpar0314arwal')

        login_form = self.browser.get_form('PC_7_A0SO5GGCQUEA20A15AJ3TA3QK20n3046_mam-usm-cardnr-form')
        login_form['PC_7_A0SO5GGCQUEA20A15AJ3TA3QK20n3046_userId'].value = credentials['card_number']
        login_form['PC_7_A0SO5GGCQUEA20A15AJ3TA3QK20n3046_password'].value = credentials['pin']

        self.browser.submit_form(login_form)

        error_box = self.browser.select('span.alert-label')
        if len(error_box) > 0 and error_box[0].text.startswith('Please check your Miles & More service card number'):
            raise LoginError(STATUS_LOGIN_FAILED)
        elif self.browser.url.startswith('https://www.miles-and-more.com/online/portal/mam/uk/homepage'):
            raise LoginError(STATUS_ACCOUNT_LOCKED)

    def balance(self):
        miles_elements = self.browser.select('div.account-status dl.dl-horizontal dd')
        award_miles = extract_decimal(miles_elements[0].text)
        status_miles = extract_decimal(miles_elements[1].text)
        return {
            'points': award_miles + status_miles
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

    def transactions(self):
        rows = self.browser.select('table tbody tr')
        return [self.hashed_transaction(row) for row in rows]