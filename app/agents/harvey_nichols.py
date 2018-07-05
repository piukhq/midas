from decimal import Decimal
from app.agents.exceptions import RegistrationError, STATUS_REGISTRATION_FAILED, ACCOUNT_ALREADY_EXISTS, UNKNOWN,\
    STATUS_LOGIN_FAILED, NO_SUCH_RECORD
from app.agents.base import ApiMiner
from gaia.user_token import UserTokenStore
from settings import REDIS_URL
import arrow
import random


class HarveyNichols(ApiMiner):

    token_store = UserTokenStore(REDIS_URL)

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
                self.send_opt_ins(self.identifier_type)


        else:
            self.handle_errors(json_result['outcome'])

    def send_opt_ins(self, customer_number, email_created, push_created, email=False, push=False):
        sm = HNOptInsSoapMessage(customer_number, email_created, push_created, email, push)
        soap_string = sm.optin_soap_message


class HNOptInsSoapMessage:

    def __init__(self, customer_id, email_created_ext, push_created_ext, email_optin=None, push_optin=None):
        email = self.set_value(email_optin)
        push = self.set_value(push_optin)
        email_created = self.format_date(email_created_ext)
        push_created = self.format_date(push_created_ext)

        self.sep = ""
        self.preferences = ''
        self.customer_id = customer_id
        random.seed()
        self.note_id = f"{random.randint(0, 999999999999):0>12}"
        self.notes = "Preference changes: "
        self.proforma = {}
        if email:
            self.proforma["EMAIL"] = (
                ("EMAIL_OPTIN", email, f"EMAIL_OPTIN set to {email}"),
                ("EMAIL_OPTIN_DATETIME", email_created, f"EMAIL_OPTIN_DATETIME set to {email_created}"),
                ("EMAIL_OPTIN_SOURCE", "BINK_APP", "EMAIL_OPTIN_SOURCE set to BINK_APP")
            )
            self.add_preferences("EMAIL", email_created)
        if push:
            self.proforma["PUSH"] = (("PUSH_OPTIN", push, f"PUSH_OPTIN set to {push}"),
                ("PUSH_OPTIN_DATETIME", push_created, f"PUSH_OPTIN_DATETIME set to {push_created}"),
                ("PUSH_OPTIN_SOURCE", "BINK_APP", "PUSH_OPTIN_SOURCE set to BINK_APP")
            )
            self.add_preferences("PUSH", push_created)

    @staticmethod
    def format_date(email_created_ext):
        arrow_date = arrow.get(email_created_ext)
        return arrow_date.format('YYYY-MM-DDTHH:mm:ss')

    @staticmethod
    def set_value(optin_value):
        if optin_value is None:
            return None
        if optin_value:
            return "true"
        else:
            return "false"

    def add_preferences(self, optin_type, created):

        for optin_item in self.proforma[optin_type]:
            self.notes = f'{self.notes}{self.sep}{optin_item[2]}'
            self.sep = " | "
            self.preferences = f'{self.preferences}' \
                               f'{self.preference_template(optin_type, optin_item[0], optin_item[1], created)}'

    def preference_template(self, optin_type, optin, value, created):
        return f"""<item key="{optin}">
    <retail:customerPreference>
        <retail:optionPathId>{optin_type}:{optin}</retail:optionPathId>
        <retail:created>{created}</retail:created>
        <retail:optionSetId type="customerPreferenceOptionSet" optionSetId="GDPR_CONSENT">
            <retail:groupId groupHierarchyId="All" groupTypeId="region">All</retail:groupId>
        </retail:optionSetId>           
        <retail:customerId>{self.customer_id}</retail:customerId>
        <retail:preferenceId>{self.customer_id}GDPR{optin_type}:{optin}</retail:preferenceId>
        <retail:value id="{optin_type}:{optin}">{value}</retail:value>    
    </retail:customerPreference>
</item>
"""

    @property
    def optin_soap_message(self):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://service.crm.enactor.com">
    <SOAP-ENV:Body>
        <retail:saveCustomerPreferenceMap xmlns:retail="http://www.enactor.com/retail">
            <retail:userId>ADMIN</retail:userId>
            <retail:customerPreferenceMap>
            {self.preferences}
            </retail:customerPreferenceMap>
        </retail:saveCustomerPreferenceMap>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

    @property
    def audit_note(self):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://service.crm.enactor.com">
    <SOAP-ENV:Body>
        <crm:saveCustomerNote xmlns:crm="http://www.enactor.com/crm" xmlns:core="http://www.enactor.com/core"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:retail="http://www.enactor.com/retail">
            <retail:customerNote>
                <retail:userId>ADMIN</retail:userId>
                <retail:customerId>{self.customer_id}</retail:customerId>
                <retail:isPrivate>false</retail:isPrivate>
                <retail:noteId>{self.note_id}</retail:noteId>
            <retail:notes></retail:notes>{self.notes}</retail:customerNote>
        </crm:saveCustomerNote>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

""