import json
from decimal import Decimal

import arrow
import time

import requests
from gaia.user_token import UserTokenStore

from app.agents.base import MerchantApi, UnauthorisedError
from app.agents.exceptions import NOT_SENT, errors, UNKNOWN
from app.configuration import Configuration
from app.security.utils import get_security_agent
from app.utils import create_error_response
from settings import REDIS_URL


class Cooperative(MerchantApi):
    API_KEY = 'awmHjJzzfV3YMUuJdcmd56PKRIzg6KAg1WKn94Ds'
    AUTH_TOKEN_TIMEOUT = 3600
    new_request = None

    identifier_type = ['cardNumber', 'memberId']

    token_store = UserTokenStore(REDIS_URL)

    def balance(self):
        return {
            'points': Decimal(0),
            'value': 0,
            'value_label': '{} {}'.format(0, ''),
            'reward_tier': 0,
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
        return {}

    def apply_security_measures(self, json_data, security_service, security_credentials, refresh_token=True):
        auth_token_header = "Authorization"
        try:
            if refresh_token:
                raise self.token_store.NoSuchToken

            access_token = json.loads(self.token_store.get(self.scheme_id))

            if self._token_is_valid(access_token['timestamp']):
                self.request = {
                    "json": json.loads(json_data),
                    "headers": {
                        auth_token_header: "{} {}".format(
                            security_credentials['outbound']['credentials'][0]['value']['prefix'],
                            access_token['token'])
                    }
                }
            else:
                raise self.token_store.NoSuchToken

        except self.token_store.NoSuchToken:
            super().apply_security_measures(json_data, security_service, security_credentials)
            timestamp = time.time()

            self.request['headers'][auth_token_header] = self.request['headers']['Authorization']
            self.token_store.set(
                self.scheme_id,
                json.dumps({'token': self.request['headers'][auth_token_header], 'timestamp': timestamp})
            )

        self.request['headers']['X-API-KEY'] = Cooperative.API_KEY

    @staticmethod
    def _token_is_valid(timestamp):
        current_time = time.time()
        return (current_time - timestamp) > Cooperative.AUTH_TOKEN_TIMEOUT

    def _send_request(self):
        # To change the request contents, using a function, based on the type of journey.
        handler_type_to_updated_request = {
            Configuration.JOIN_HANDLER: self._update_join_request
        }

        handler_type_to_updated_request[self.config.handler_type[0]]()

        response = requests.post(self.config.merchant_url, **self.new_request)
        status = response.status_code

        if status == 200:
            inbound_security_agent = get_security_agent(Configuration.OPEN_AUTH_SECURITY)

            response_json = inbound_security_agent.decode(response.headers, response.text)

            self.log_if_redirect(response, response_json)
        elif status == 401:
            raise UnauthorisedError
        elif status in [503, 504, 408]:
            response_json = create_error_response(NOT_SENT, errors[NOT_SENT]['name'])
        else:
            response_json = create_error_response(UNKNOWN,
                                                  errors[UNKNOWN]['name'] + ' with status code {}'
                                                  .format(status))
        return response_json

    def _update_join_request(self):
        old_json = self.request['json']
        new_json = {
            'title': old_json['title'],
            'dateOfBirth': old_json['dob'],
            'firstName': old_json['first_name'],
            'lastName': old_json['last_name'],
            'email': old_json['email'],
            'address': {
                'addressLine1': old_json['address_1'],
                'city': old_json['town_city'],
                'postcode': old_json['postcode']
            }
        }

        self.new_request = self.request.copy()
        self.new_request['json'] = new_json
