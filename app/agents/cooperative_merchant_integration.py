import json
import time
from decimal import Decimal

import arrow
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
    AUTH_TOKEN_HEADER = "Authorization"

    new_request = None
    identifier_type = ['cardNumber', 'memberId']
    merchant_identifier_mapping = {
        'memberId': 'merchant_identifier',
    }

    token_store = UserTokenStore(REDIS_URL)

    def __init__(self, retry_count, user_info, scheme_slug=None, config=None, consents_data=None):
        super().__init__(retry_count, user_info, scheme_slug, config, consents_data)

        # To change the request contents, using a function, based on the type of journey.
        self.handler_type_to_updated_request = {
            Configuration.JOIN_HANDLER: self._update_join_request,
            Configuration.VALIDATE_HANDLER: self._update_validate_request,
            Configuration.UPDATE_HANDLER: self._update_balance_request
        }
        # For journey specific error handling.
        self.handler_type_to_error_handler = {
            Configuration.JOIN_HANDLER: self._join_error_handler,
            Configuration.VALIDATE_HANDLER: self._validate_error_handler,
            Configuration.UPDATE_HANDLER: self._balance_error_handler
        }
        self.scope = None

        # Coop API requires a different scope parameter for each oauth call
        self.journey_to_scope = {
            Configuration.UPDATE_HANDLER: 'membership-api/get-balance',
            Configuration.VALIDATE_HANDLER: 'membership-api/verify-member',
            Configuration.JOIN_HANDLER: ['membership-api/register-members', 'membership-api/check-card']
        }

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

    def apply_security_measures(self, json_data, security_service, security_credentials, refresh_token=False):
        self.scope = self._get_scope()
        try:
            if refresh_token:
                raise self.token_store.NoSuchToken

            access_token = self._get_auth_token()

            if self._token_is_valid(access_token['timestamp']):
                self.request = {
                    "json": json.loads(json_data),
                    "headers": {
                        self.AUTH_TOKEN_HEADER: "{} {}".format(
                            security_credentials['outbound']['credentials'][0]['value']['prefix'],
                            access_token['token'])
                    }
                }
            else:
                raise self.token_store.NoSuchToken

        except self.token_store.NoSuchToken:
            self._refresh_auth_token(json_data, security_service, security_credentials)

        self.request['headers']['X-API-KEY'] = Cooperative.API_KEY

    @staticmethod
    def _token_is_valid(timestamp):
        current_time = time.time()
        return (current_time - timestamp) < Cooperative.AUTH_TOKEN_TIMEOUT

    def _get_auth_token(self):
        return json.loads(self.token_store.get(f'{self.scheme_id}:{self.scope}'))

    def _refresh_auth_token(self, json_data, security_service, security_credentials):
        security_credentials['outbound']['credentials'][0]['value']['payload']['scope'] = self.scope
        super().apply_security_measures(json_data, security_service, security_credentials)

        timestamp = time.time()

        self.request['headers'][self.AUTH_TOKEN_HEADER] = self.request['headers']['Authorization']

        key = f"{self.scheme_id}:{self.scope}"
        token_data = json.dumps({'token': self.request['headers'][self.AUTH_TOKEN_HEADER], 'timestamp': timestamp})
        self.token_store.set(key, token_data)

    def _get_scope(self):
        handler_type = self.config.handler_type[0]

        if handler_type != Configuration.JOIN_HANDLER:
            scope = self.journey_to_scope[handler_type]
        else:
            # Must call verify if it is a ghost card
            if self.user_info['credentials'].get('card_number'):
                scope = self.journey_to_scope[handler_type][1]
            else:
                scope = self.journey_to_scope[handler_type][0]

        return scope

    def _send_request(self):
        handler_type = self.config.handler_type[0]
        return self.handler_type_to_updated_request[handler_type]()

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

        response = requests.post(self.config.merchant_url, **self.new_request)
        handler_type = self.config.handler_type[0]

        return self.handler_type_to_error_handler[handler_type](response)

    def _join_error_handler(self, response):
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

    def _update_validate_request(self):
        handler_type = self.config.handler_type[0]
        old_json = self.request['json']
        new_json = {
            'cardNumber': old_json['title'],
            'dateOfBirth': old_json['dob'],
            'postcode': old_json['first_name']
        }

        self.new_request = self.request.copy()
        self.new_request['json'] = new_json
        response = requests.post(self.config.merchant_url, **self.new_request)
        response_json = self.handler_type_to_error_handler[handler_type](response)
        member_id = json.loads(response_json)['memberId']


        self.balance_config = Configuration(self.scheme_slug, Configuration.UPDATE_HANDLER)
        balance_url = self.balance_config.merchant_url.format(member_id)
        response = requests.get(balance_url, headers=self.request['headers'])

        balance_handler_type = self.balance_config.handler_type[0]
        return self.handler_type_to_error_handler[balance_handler_type](response)

    def _validate_error_handler(self, response):
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

    def _update_balance_request(self):
        handler_type = self.config.handler_type[0]
        old_json = self.request['json']
        member_id = old_json['merchant_scheme_id1']

        balance_url = self.config.merchant_url.format(member_id)
        response = requests.post(balance_url, headers=self.request['headers'])
        return self.handler_type_to_error_handler[handler_type](response)

    def _balance_error_handler(self, response):
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
