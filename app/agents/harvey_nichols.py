from decimal import Decimal
from app.agents.exceptions import RegistrationError, STATUS_REGISTRATION_FAILED, ACCOUNT_ALREADY_EXISTS, UNKNOWN,\
    STATUS_LOGIN_FAILED, NO_SUCH_RECORD
from app.agents.base import ApiMiner
from gaia.user_token import UserTokenStore
from settings import REDIS_URL
from app.tasks.resend import ReTryTaskStore
import arrow
import json
import requests


class HarveyNichols(ApiMiner):

    token_store = UserTokenStore(REDIS_URL)

    BASE_URL = 'http://89.206.220.40:8080/WebCustomerLoyalty/services/CustomerLoyalty'
    CONSENTS_URL ='http://10.215.110.101:8090/' \
                  'axis2/services/CRMCustomerDataService.CRMCustomerDataServiceHttpSoap11Endpoint/'

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
                'applicationId': 'BINK_APP'
            }
        }
        if credentials.get('phone'):
            data['CustomerSignUpRequest']['phone'] = credentials['phone']

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
                'applicationId': "BINK_APP"
            }
        }

        self.login_response = self.make_request(url, method='post', timeout=10, json=data)
        json_result = self.login_response.json()['CustomerSignOnResult']

        if json_result['outcome'] == 'Success':
            self.customer_number = json_result['customerNumber']
            self.token = json_result['token']
            self.token_store.set('user-token-store:{}'.format(self.scheme_id), self.token)

            if self.identifier_type not in credentials:
                # self.identifier should only be set if identifier type is not passed in credentials
                self.identifier = {self.identifier_type: json_result['customerNumber']}
                optin_data = {
                    "url": self.CONSENTS_URL,
                    "customer_number": self.customer_number,
                    "consents": credentials['consents'],
                    "confimred": 0,
                    "retries": 10,
                    "state": "Consents",
                    "errors": []
                }
                sent, message = try_harvey_nic_optins(optin_data)
                if not sent:
                    optin_data["errors"].append(message)
                    task = ReTryTaskStore()
                    task.set_task("app.agents.harvey_nichols", "try_harvey_nic_optins", optin_data)
        else:
            self.handle_errors(json_result['outcome'])


def try_harvey_nic_optins(optin_data):
    """This function sends the Harvey Nichols - changed rest interface to draft "spec" sent by email:

    curl -k -H "Accept: application/json" -X POST -d '{"enactor_id":"123456789",
     "email_optin":true|false, "push_optin":true|false}' https://$endpoint/preferences/create

    i.e. the json post '{"enactor_id":"123456789", "email_optin":true|false, "push_optin":true|false}

    Note the consent slug must be call email_optin and push_optin

    If successful assume response 200 to 204 is received then for each consent id put consent_confirmed to
    Hermes

    The routine should manage state of process so that only when complete of fatal error will it return true
    It is therefore possible to continue retries if an internal log status message fails
    :param optin_data:
    :return:  Tuple:
                continue_status: True to terminate any retries, False to continue to rety
                response_list:  list of logged errors (successful one will not be wriiten to redis)
    """

    try:
        hn_post_message = {"enactor_id": optin_data["customer_number"]}
        hn_headers = {"Content-Type": "application/json; charset=utf-8"}
        confirm_ids = []

        for consent in optin_data["consents"]:
            hn_post_message[consent['slug']] = consent['value']
            confirm_ids.append(consent['id'])

        if optin_data["state"] == "Consents":

            resp = requests.post(optin_data["url"], data=json.dumps(hn_post_message), timeout=10,
                                 headers=hn_headers)
            if resp.status_code not in (200, 201, 202, 204):
                return False, f"{optin_data['state']}: Error Code {resp.status_code}"
            else:
                optin_data["state"] = "Confirm"

        if optin_data["state"] == "Confirm":
            for user_consent_id in confirm_ids:
                resp = requests.put(f'{HERMES_URL}/schemes/userconsent/confirmed/{user_consent_id}', timeout=10)
                if resp.status_code == 200:
                    optin_data['confimed'] += 1
                else:
                    break

            if optin_data['confimed'] == len(optin_data["consents"]):
                optin_data["state"] = "done"
                return True, "done"
            else:
                return False, f"{optin_data['state']}: Error Code {resp.status_code}"

        return False, "Internal Error"
    except AttributeError as e:
        # If data is invalid or missing parameters no point in retrying so abort
        return True, f"{optin_data['state']}: Attribute error {str(e)}"
    except IOError as e:
        return False, f"{optin_data['state']}: IO error {str(e)}"


