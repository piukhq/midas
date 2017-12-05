from decimal import Decimal
from app.agents.exceptions import RegistrationError, STATUS_REGISTRATION_FAILED, ACCOUNT_ALREADY_EXISTS, UNKNOWN,\
    STATUS_LOGIN_FAILED, NO_SUCH_RECORD
from app.agents.base import ApiMiner
from gaia.user_token import UserTokenStore
from settings import USER_TOKEN_REDIS_URL


class HarveyNichols(ApiMiner):

    token_store = UserTokenStore(USER_TOKEN_REDIS_URL)

    BASE_URL = 'http://89.206.220.40:8080/WebCustomerLoyalty/services/CustomerLoyalty'

    def login(self, credentials):
        self.identifier_type = 'card_number'
        self.errors = {
            NO_SUCH_RECORD: 'NoSuchRecord',
            STATUS_LOGIN_FAILED: ['Invalid', 'AuthFailed'],
            UNKNOWN: 'Fail'
        }

        # get token from redis if we have one, otherwise login to get one
        try:
            self.customer_number = credentials[self.identifier_type]
            self.token = self.token_store.get(self.scheme_id)
        except (KeyError, self.token_store.NoSuchToken):
            self._login(credentials)

        self.result = self.call_balance_url()

        if self.result['outcome'] == 'InvalidToken':
            self._login(credentials)
            self.result = self.call_balance_url()

        if self.result['outcome'] != 'Success':
            self.handle_errors(self.result['outcome'])

    def call_balance_url(self):
        url = self.BASE_URL + '/GetProfile'
        data = {
            "CustomerLoyaltyProfileRequest": {
                'token': self.token,
                'customerNumber': self.customer_number,
            }
        }
        self.balance_response = self.make_request(url, method='post', json=data)
        return self.balance_response.json()['CustomerLoyaltyProfileResult']

    def balance(self):
        tiers_list = {
            'BRONZE': 0,
            'SILVER': 1,
            'GOLD': 2,
            'BLACK': 3
        }
        tier = tiers_list[self.result['loyaltyTierId']]

        return {
            'points': Decimal(self.result['pointsBalance']),
            'value': Decimal('0'),
            'value_label': '',
            'rewards_tier': tier
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []

    def register(self, credentials):
        self.errors = {
            ACCOUNT_ALREADY_EXISTS: 'AlreadyExists',
            STATUS_REGISTRATION_FAILED: 'Invalid',
            UNKNOWN: 'Fail'
        }
        url = self.BASE_URL + '/SignUp'
        data = {
            "CustomerSignUpRequest": {
                'username': credentials['email'],
                'email': credentials['email'],
                'password': credentials['password'],
                'title': credentials['title'],
                'forename': credentials['first_name'],
                'surname': credentials['last_name'],
                'phone': credentials['phone'],
                'applicationId': 'CX_MOB'
            }
        }

        self.register_response = self.make_request(url, method='post', json=data)
        message = self.register_response.json()['CustomerSignUpResult']['outcome']

        if message == 'Success':
            return {"message": "success"}

        self.handle_errors(message, exception_type=RegistrationError)

    def _login(self, credentials):
        """
        Retrieves user token and customer number, saving token in user token redis db.
        """
        url = self.BASE_URL + '/SignOn'
        data = {
            "CustomerSignOnRequest": {
                'username': credentials['email'],
                'password': credentials['password'],
                'applicationId': "CX_MOB"
            }
        }

        self.login_response = self.make_request(url, method='post', json=data)
        json_result = self.login_response.json()['CustomerSignOnResult']

        if json_result['outcome'] == 'Success':
            self.customer_number = json_result['customerNumber']
            self.token = json_result['token']
            self.token_store.set(self.scheme_id, self.token)

            if self.identifier_type not in credentials:
                # self.identifier should only be set if identifier type is not passed in credentials
                self.identifier = json_result['customerNumber']

        else:
            self.handle_errors(json_result['outcome'])
