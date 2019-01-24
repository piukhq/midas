from decimal import Decimal

import arrow

from app.agents.base import MerchantApi


class Cooperative(MerchantApi):
    API_KEY = 'awmHjJzzfV3YMUuJdcmd56PKRIzg6KAg1WKn94Ds'
    identifier_type = ['card_number', 'merchant_scheme_id2']

    def balance(self):
        value = Decimal(self.result['alt_value'])
        value_units = self.result['alt_unit']
        tier_list = {
            'Platinum': 0,
            'Black': 1
        }
        tier = tier_list[self.result['tier']]

        return {
            'points': Decimal(self.result['balance_value']),
            'value': value,
            'value_label': '{} {}'.format(value, value_units),
            'reward_tier': tier,
        }

    def scrape_transactions(self):
        return self.result['transactions']

    @staticmethod
    def parse_transactions(row):
        return {
            'date': arrow.get(row['timestamp']),
            'description': row['reference'],
            'points': Decimal(row['balance_value']),
        }

    def get_merchant_ids(self, credentials):
        merchant_ids = {
            'merchant_scheme_id1': credentials['email'],
            'merchant_scheme_id2': credentials.get('merchant_identifier')
        }

        return merchant_ids

    def apply_security_measures(self, json_data, security_service, security_credentials):
        request = super().apply_security_measures(json_data, security_service, security_credentials)

        request['headers']['Access Token'] = request['headers'].pop('Authorization')
        request['headers']['X-API-KEY'] = Cooperative.API_KEY

        return request
