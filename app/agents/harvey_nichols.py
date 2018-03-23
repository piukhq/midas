from decimal import Decimal
from app.agents.exceptions import RegistrationError, STATUS_REGISTRATION_FAILED, ACCOUNT_ALREADY_EXISTS, UNKNOWN,\
    STATUS_LOGIN_FAILED, NO_SUCH_RECORD
from app.agents.base import ApiMiner
from gaia.user_token import UserTokenStore
from settings import USER_TOKEN_REDIS_URL
import arrow


class HarveyNichols(ApiMiner):

    token_store = UserTokenStore(USER_TOKEN_REDIS_URL)

    BASE_URL = 'http://89.206.220.40:8080/WebCustomerLoyalty/services/CustomerLoyalty'

    def login(self, credentials):
        self.credentials = credentials
        self.identifier_type = 'card_number'
        self.errors = {
            NO_SUCH_RECORD: ['NoSuchRecord'],
            STATUS_LOGIN_FAILED: ['Invalid', 'AuthFailed'],
            UNKNOWN: ['Fail']
        }

        # get token from redis if we have one, otherwise login to get one
        try:
            self.customer_number = credentials[self.identifier_type]
            self.token = self.token_store.get(self.scheme_id)
        except (KeyError, self.token_store.NoSuchToken):
            self._login(credentials)

    def call_balance_url(self):
        url = self.BASE_URL + '/GetProfile'
        data = {
            "CustomerLoyaltyProfileRequest": {
                'token': self.token,
                'customerNumber': self.customer_number,
            }
        }
        balance_response = self.make_request(url, method='post', timeout=10, json=data)
        return balance_response.json()['CustomerLoyaltyProfileResult']

    def balance(self):
        result = self.call_balance_url()

        if result['outcome'] == 'InvalidToken':
            self._login(self.credentials)
            result = self.call_balance_url()

        if result['outcome'] != 'Success':
            self.handle_errors(result['outcome'])

        tiers_list = {
            'SILVER': 0,
            'GOLD': 1,
            'PLATINUM': 2,
            'BLACK': 3
        }
        tier = tiers_list[result['loyaltyTierId']]

        return {
            'points': Decimal(result['pointsBalance']),
            'value': Decimal('0'),
            'value_label': '',
            'reward_tier': tier
        }

    def call_transaction_url(self):
        url = self.BASE_URL + '/ListTransactions'
        from_date = arrow.get('2001/01/01').format('YYYY-MM-DDTHH:mm:ssZ')
        to_date = arrow.utcnow().format('YYYY-MM-DDTHH:mm:ssZ')
        data = {
            "CustomerListTransactionsRequest": {
                'token': self.token,
                'customerNumber': self.customer_number,
                "fromDate": from_date,
                "toDate": to_date,
                "pageOffset": 0,
                "pageSize": 20,
                "maxHits": 10
            }
        }

        transaction_response = self.make_request(url, method='post', timeout=10, json=data)
        return transaction_response.json()['CustomerListTransactionsResponse']

    @staticmethod
    def parse_transaction(row):
        if type(row['value']) == int:
            money_value = '£{:.2f}'.format(Decimal(row['value'] / 100))
        else:
            money_value = ''

        return {
            "date": arrow.get(row['date']),
            "description": row['type'] + ': ' + row['locationName'] + ' ' + money_value,
            "points": Decimal(row['pointsValue']),
        }

    def scrape_transactions(self):
        result = self.call_transaction_url()

        if result['outcome'] == 'InvalidToken':
            self._login(self.credentials)
            result = self.call_transaction_url()

        if result['outcome'] != 'Success':
            self.handle_errors(result['outcome'])

        transactions = [transaction['CustomerTransaction'] for transaction in result['transactions']]
        transaction_types = ['Sale']
        sorted_transactions = [transaction for transaction in transactions if transaction['type'] in transaction_types]

        return sorted_transactions

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

        self.register_response = self.make_request(url, method='post', timeout=10, json=data)
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

        self.login_response = self.make_request(url, method='post', timeout=10, json=data)
        json_result = self.login_response.json()['CustomerSignOnResult']

        if json_result['outcome'] == 'Success':
            self.customer_number = json_result['customerNumber']
            self.token = json_result['token']
            self.token_store.set(self.scheme_id, self.token)

            if self.identifier_type not in credentials:
                # self.identifier should only be set if identifier type is not passed in credentials
                self.identifier = {self.identifier_type: json_result['customerNumber']}

        else:
            self.handle_errors(json_result['outcome'])
