from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from decimal import Decimal
import base64
import arrow


class TheBodyShop(Miner):
    loyalty_data = None

    def login(self, credentials):
        url = 'https://crmemeaws-c.thebodyshop.com/api/v1/en-gb/customers/createsessionforloginwithchecks'
        params = {
            'callback': '',
            'callingSystem': 'ecomcore',
            'cardLoginId': ' ',
            'isAddressCityMandatory': 'false',
            'isAddressLine1Mandatory': 'false',
            'isAddressLine2Mandatory': 'false',
            'isAddressLine3Mandatory': 'false',
            'isAddressProvinceMandatory': 'false',
            'isDateOfBirthMandatory': 'false',
            'isEmailAddressMandatory': 'true',
            'isFirstNameMandatory': 'true',
            'isGenderMandatory': 'true',
            'isLastNameMandatory': 'true',
            'isMiddleNameMandatory': 'false',
            'isMobileNumberMandatory': 'false',
            'isNationalIdMandatory': 'false',
            'isPhoneNumberMandatory': 'false',
            'isPreferredLanguageMandatory': 'false',
            'isTitleMandatory': 'false',
            'loginEmail': credentials['email'],
            'password': credentials['password'],
            'socialLoginId': '',
            'socialProvider': '',
        }

        self.open_url(url, params=params)

        data = self.browser.response.json()

        success = data['isSuccess']
        if not success:
            error_code = data['errorCodes'][0]
            # error_data = data['errorData']

            if (error_code == 'ERROR_OUTPUT_LOGIN_EMAIL_NOT_FOUND' or
               error_code == 'ERROR_OUTPUT_LOGIN_PASSWORD_DOES_NOT_MATCH'):
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

        self.auth_token = base64.encodebytes(data['authenticationToken'].encode('utf-8')).decode('utf-8')

        # Get points and transaction data in one call.
        url = 'https://crmemeaws-c.thebodyshop.com/api/v1/en-gb/customers/loyaltymemberpointshistory'
        params = {
            'authtoken': self.auth_token,
            'callback': '',
            'callingSystem': 'ecomcore',
        }

        self.open_url(url, params=params)
        self.loyalty_data = self.browser.response.json()

    def balance(self):
        return {
            'points': Decimal(self.loyalty_data['currentPointBalance']),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        # Pulled from https://secure.thebodyshop.co.uk/js/loreal.loc.js.axd?v=LOC_JS_VERSION
        transaction_types = {
            'Accrual_Product': "Purchase",
            'Service_Enrolment': "Gift",
            'Redemption_Product': "Voucher",
            'Accrual_Gift': "Birthday Gift",
            'Accrual_ManualCredit': "Manual Credit",
        }

        return {
            'date': arrow.get(row['transactionDate']),
            'description': transaction_types[row['transactionType']],
            'points': Decimal(row['transactionPoints']),
        }

    def scrape_transactions(self):
        return self.loyalty_data['pointsTransactions']
