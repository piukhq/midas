from urllib.parse import urlencode
from decimal import Decimal

import sentry_sdk
import requests
from requests.exceptions import Timeout

from app.agents.base import ApiMiner
from app.agents.exceptions import LoginError, UNKNOWN, STATUS_LOGIN_FAILED, END_SITE_DOWN


class Avios(ApiMiner):

    def login(self, credentials):
        self.faking_login = False

        if 'card_number' not in credentials:
            sentry_sdk.capture_message('No card_number in Avios agent! Check the card_number_regex on Hermes.')
            self.faking_login = True
            return

        url = 'https://api.avios.com/v1/programmes/ATRP/accounts/{0}'.format(credentials['card_number'])
        query = {
            # 'date-of-birth': arrow.get(credentials['date_of_birth'], 'DD/MM/YYYY').format('YYYY-MM-DD'),
            # below date of birth currently works so above commented out
            'date-of-birth': '1900-01-01',
            'family-name': credentials['last_name'],
            'api_key': 'snkd3k4pvr5agqeeprs7ytqp',
        }

        self.headers['Accept'] = 'application/json'
        self.headers['X-Forward-For'] = '172.128.25.24'

        try:
            self.response = requests.get('{0}?{1}'.format(url, urlencode(query)), headers=self.headers, timeout=5)
            self.response_json = self.response.json()
            self.response.raise_for_status()

        except (AttributeError, Timeout) as e:
            sentry_sdk.capture_exception(e)
            raise LoginError(END_SITE_DOWN)

        except Exception:
            error_code = self.response_json['error']['code']
            sentry_sdk.capture_message('Avios API login failed! Status code: {} :: Error code: {}'.format(
                self.response.status_code,
                error_code))

            errors = ['ACCOUNT_NOT_FOUND', 'CUSTOMER_DETAILS_INVALID', 'REQUEST_INVALID', 'INVALID_MEMBER']
            if error_code in errors:
                raise LoginError(STATUS_LOGIN_FAILED)

            else:
                raise LoginError(UNKNOWN)

    def balance(self):
        if self.faking_login:
            # we return a fake balance of 0, this will update when we fix the regex and chronos pulls the real balance
            return {
                'points': Decimal('0'),
                'value': Decimal('0'),
                'value_label': '',
            }

        return {
            'points': Decimal(self.response_json['loyaltyProgramAccount']['balance']['amount']),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
