from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class ThaiAirways(Miner):
    def login(self, credentials):
        url = 'http://www.thaiair.com/AIP_ROP/Logon'
        data = {
            'LanguagePreference': 'EN',
            'submit': '',
            'userid': credentials['username'],
            'pin': credentials['password'],
        }

        self.open_url(url, method='post', data=data)

        self.check_error('/AIP_ROP/rop/errorPage.jsp',
                         (('h1 > font.contentbody', STATUS_LOGIN_FAILED, 'Invalid membership number'),
                          ('h1 > font.contentbody', STATUS_LOGIN_FAILED, 'Incorrect Pin Number'), ))

    def balance(self):
        points = extract_decimal(self.browser.select('table.table_userDetail > tr > td > font > b')[2].text)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        '''
        url = 'http://www.thaiair.com/AIP_ROP/MileageStatement'
        data = {
            "mfwdType": "servlet",
            "mfwdLink": "AIP_ROP%2FMileageStatement",
            "period": "-11",
            "stmLanguagePref": "en",
        }
        '''
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
