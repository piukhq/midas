from decimal import Decimal
import random
from time import sleep

import arrow

from app.agents.base import ApiMiner, MerchantApi
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, RegistrationError, ACCOUNT_ALREADY_EXISTS, \
    STATUS_REGISTRATION_FAILED, UNKNOWN, CARD_NUMBER_ERROR, END_SITE_DOWN

users = {
    '000000': {
        'len_transactions': 0,
        'credentials': {
            'email': 'zero@testbink.com',
            'password': 'Password01',
            'last_name': 'zero',
            'postcode': 'rg0 0aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('0')
    },
    '111111': {
        'len_transactions': 1,
        'credentials': {
            'email': 'one@testbink.com',
            'password': 'Password01',
            'last_name': 'one',
            'postcode': 'rg1 1aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('20.10')
    },
    '555555': {
        'len_transactions': 5,
        'credentials': {
            'email': 'five@testbink.com',
            'password': 'Password01',
            'last_name': 'five',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    '666666': {
        'len_transactions': 6,
        'credentials': {
            'email': 'six@testbink.com',
            'password': 'Password01',
            'last_name': 'six',
            'postcode': 'rg6 6aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('1480')
    },
    '123456': {
        'len_transactions': 6,
        'credentials': {
            'email': 'sixdigitpoints@testbink.com',
            'password': 'pa$$w&rd01!',
            'last_name': 'million',
            'postcode': 'mp6 0bb',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('123456')
    },
    '234567': {
        'len_transactions': 6,
        'credentials': {
            'email': 'sevendigitpoints@testbink.com',
            'password': 'Password01',
            'last_name': 'seven-digits, smith\'s',
            'postcode': 'mp7 1bb',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal(1234567)
    },
    # QA Automated Test Fixtures
    '222220': {
        'len_transactions': 0,
        'credentials': {
            'email': 'auto_zero@testbink.com',
            'password': 'Password01',
            'last_name': 'qa',
            'postcode': 'qa1 1qa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('0')
    },
    '222225': {
        'len_transactions': 5,
        'credentials': {
            'email': 'auto_five@testbink.com',
            'password': 'Password01',
            'last_name': 'qa',
            'postcode': 'qa1 1qa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    # NEW FIXTURES
    '900001': {
        'len_transactions': 0,
        'credentials': {
            'email': 'perfuser01@testbink.com',
            'password': 'Password01',
            'last_name': 'perfuser01',
            'postcode': 'rg0 0aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('0')
    },
    '900002': {
        'len_transactions': 5,
        'credentials': {
            'email': 'perfuser02@testbink.com',
            'password': 'Password02',
            'last_name': 'perfuser02',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    '900003': {
        'len_transactions': 5,
        'credentials': {
            'email': 'perfuser03@testbink.com',
            'password': 'Password03',
            'last_name': 'perfuser03',
            'postcode': 'mp6 0bb',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('123456')
    },
    '900004': {
        'len_transactions': 5,
        'credentials': {
            'email': 'perfuser04@testbink.com',
            'password': 'Password04',
            'last_name': 'perfuser04',
            'postcode': 'mp7 1bb',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('1234567')
    },
    '900005': {
        'len_transactions': 0,
        'credentials': {
            'email': 'perfuser05@testbink.com',
            'password': 'Password05',
            'last_name': 'perfuser05',
            'postcode': 'rg0 0aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('0')
    },
    '900006': {
        'len_transactions': 1,
        'credentials': {
            'email': 'perfuser06@testbink.com',
            'password': 'Password06',
            'last_name': 'perfuser06',
            'postcode': 'rg1 1aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('20.10')
    },
    '900007': {
        'len_transactions': 5,
        'credentials': {
            'email': 'perfuser07@testbink.com',
            'password': 'Password07',
            'last_name': 'perfuser07',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    '900008': {
        'len_transactions': 0,
        'credentials': {
            'email': 'perfuser08@testbink.com',
            'password': 'Password08',
            'last_name': 'perfuser08',
            'postcode': 'rg0 0aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('0')
    },
    '900009': {
        'len_transactions': 5,
        'credentials': {
            'email': 'perfuser09@testbink.com',
            'password': 'Password09',
            'last_name': 'perfuser09',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    '900010': {
        'len_transactions': 1,
        'credentials': {
            'email': 'perfuser10@testbink.com',
            'password': 'Password10',
            'last_name': 'perfuser10',
            'postcode': 'mp6 0bb',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('20.10')
    },
    '900011': {
        'len_transactions': 6,
        'credentials': {
            'email': 'perfuser11@testbink.com',
            'password': 'Password11',
            'last_name': 'perfuser11',
            'postcode': 'mp7 1bb',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('1234567')
    },
    '900012': {
        'len_transactions': 0,
        'credentials': {
            'email': 'perfuser12@testbink.com',
            'password': 'Password12',
            'last_name': 'perfuser12',
            'postcode': 'rg0 0aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('0')
    },
    '900013': {
        'len_transactions': 1,
        'credentials': {
            'email': 'perfuser13@testbink.com',
            'password': 'Password13',
            'last_name': 'perfuser13',
            'postcode': 'rg1 1aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('20.10')
    },
    '900014': {
        'len_transactions': 5,
        'credentials': {
            'email': 'perfuser14@testbink.com',
            'password': 'Password14',
            'last_name': 'perfuser14',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    '900015': {
        'len_transactions': 0,
        'credentials': {
            'email': 'perfuser15@testbink.com',
            'password': 'Password15',
            'last_name': 'perfuser15',
            'postcode': 'rg0 0aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('0')
    },
    '900016': {
        'len_transactions': 5,
        'credentials': {
            'email': 'perfuser16@testbink.com',
            'password': 'Password16',
            'last_name': 'perfuser16',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    '900017': {
        'len_transactions': 6,
        'credentials': {
            'email': 'perfuser17@testbink.com',
            'password': 'Password17',
            'last_name': 'perfuser17',
            'postcode': 'rg1 1aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('123456')
    },
    '900018': {
        'len_transactions': 2,
        'credentials': {
            'email': 'passtest1@testbink.com',
            'password': r'/!£Password1'
        },
        'points': Decimal('123456')
    },
    '900019': {
        'len_transactions': 3,
        'credentials': {
            'email': 'passtest2@testbink.com',
            'password': r'Password1?£$'
        },
        'points': Decimal('123456')
    },
    '900020': {
        'len_transactions': 1,
        'credentials': {
            'email': 'passtest3@testbink.com',
            'password': r'<!-=]{'
        },
        'points': Decimal('123456')
    },
    '900021': {
        'len_transactions': 2,
        'credentials': {
            'email': 'passtest4@testbink.com',
            'password': r'Pass word1'
        },
        'points': Decimal('123456')
    },
    '900022': {
        'len_transactions': 3,
        'credentials': {
            'email': 'passtest5@testbink.com',
            'password': r"Pass'wo'rd1"
        },
        'points': Decimal('123456')
    },
    '900023': {
        'len_transactions': 2,
        'credentials': {
            'email': 'passtest6@testbink.com',
            'password': r'Pa"ssw"ord1'
        },
        'points': Decimal('123456')
    },
    '900024': {
        'len_transactions': 1,
        'credentials': {
            'email': 'passtest7@testbink.com',
            'password': r'Pass@word1'
        },
        'points': Decimal('123456')
    },
    '900025': {
        'len_transactions': 2,
        'credentials': {
            'email': 'passtest8@testbink.com',
            'password': r'Pass_word1'
        },
        'points': Decimal('123456')
    },
    '900026': {
        'len_transactions': 2,
        'credentials': {
            'email': 'passtest9@testbink.com',
            'password': r'Pa*()ss'
        },
        'points': Decimal('123456')
    },
    '900027': {
        'len_transactions': 3,
        'credentials': {
            'email': 'passtest10@testbink.com',
            'password': r'Pas\s\word1'
        },
        'points': Decimal('123456')
    },
    '900028': {
        'len_transactions': 4,
        'credentials': {
            'email': 'passtest11@testbink.com',
            'password': r'Pa$££€ss'
        },
        'points': Decimal('123456')
    },
    '999000': {
        'len_transactions': 2,
        'credentials': {
            'email': 'slow@testbink.com',
            'password': 'Slowpass01',
            'last_name': 'slow',
            'postcode': 'sl1 1ow',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('300')
    },
    '911111': {
        'len_transactions': 5,
        'credentials': {
            'email': "special!#$%&'char1@testbink.com",
            'password': 'Password01',
            'last_name': 'five',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    '922222': {
        'len_transactions': 3,
        'credentials': {
            'email': "special*+-/=?^char2@testbink.com",
            'password': 'Password01',
            'last_name': 'five',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
    '933333': {
        'len_transactions': 4,
        'credentials': {
            'email': 'special_`{|}~char3@testbink.com',
            'password': 'Password01',
            'last_name': 'five',
            'postcode': 'rg5 5aa',
            'date_of_birth': '2000-01-01',
        },
        'points': Decimal('380.01')
    },
}

transactions = [
    {
        "date": arrow.get('01/07/2018 14:24:15', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 1 item',
        "points": Decimal('20.71'),
    },
    {
        "date": arrow.get('02/08/2018 12:11:30', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 3 items',
        "points": Decimal('100.01'),
    },
    {
        "date": arrow.get('03/09/2018 22:05:45', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 5 items',
        "points": Decimal('200'),
    },
    {
        "date": arrow.get('04/09/2018 16:55:00', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 2 items',
        "points": Decimal('50'),
    },
    {
        "date": arrow.get('04/09/2018 07:35:10', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 1 item',
        "points": Decimal('10'),
    },
    {
        "date": arrow.get('05/09/2018 11:30:50', 'DD/MM/YYYY HH:mm:ss'),
        "description": 'Test transaction: 20 items',
        "points": Decimal('1100'),
    },
]

error_credentials = {
    'email': {
        'endsitedown@testbink.com': END_SITE_DOWN,
    },
}


def check_and_raise_error_credentials(credentials):
    for credential_type, credential in credentials.items():
        try:
            error_to_raise = error_credentials[credential_type][credential]
            raise LoginError(error_to_raise)
        except KeyError:
            pass


def get_user(card_number):
    try:
        return users[card_number]
    except (KeyError, TypeError):
        raise LoginError(STATUS_LOGIN_FAILED)


class MockAgentHN(ApiMiner):
    REGISTER_PREFIX = '911'
    retry_limit = None

    def login(self, credentials):
        check_and_raise_error_credentials(credentials)
        if all(cred in credentials for cred in ['email', 'password', 'title', 'first_name', 'last_name']):
            self.user_info = users['000000']
            register_suffix = random.randint(0, 9999999999)
            self.identifier = {
                'card_number': f'{self.REGISTER_PREFIX}{register_suffix:010d}'
            }
            return

        else:
            if credentials.get('card_number')[:3] == self.REGISTER_PREFIX:
                self.user_info = users['000000']
                return

            for user, info in users.items():
                check_email = info['credentials']['email']
                check_password = info['credentials']['password']
                if credentials['email'] == check_email and credentials['password'] == check_password:
                    self.user_info = info
                    self.customer_number = user
                    break

            else:
                raise LoginError(STATUS_LOGIN_FAILED)

        card_number_mapping = {
            '000000': '0000000000000',
            '111111': '1111111111111',
            '555555': '5555555555555',
            '666666': '6666666666666',
            '123456': '1020304056666',
            '234567': '1020304057777',
            # QA Automated Test Fixtures
            '222220': '9123001122330',
            '222225': '9123001122335',
            # New fixtures
            '900001': '9000000000001',
            '900002': '9000000000002',
            '900003': '9000000000003',
            '900004': '9000000000004',
            '900005': '9000000000005',
            '900006': '9000000000006',
            '900007': '9000000000007',
            '900008': '9000000000008',
            '900009': '9000000000009',
            '900010': '9000000000010',
            '900011': '9000000000011',
            '900012': '9000000000012',
            '900013': '9000000000013',
            '900014': '9000000000014',
            '900015': '9000000000015',
            '900016': '9000000000016',
            '900017': '9000000000017',
            '900018': '9000000000018',
            '900019': '9000000000019',
            '900020': '9000000000020',
            '900021': '9000000000021',
            '900022': '9000000000022',
            '900023': '9000000000023',
            '900024': '9000000000024',
            '900025': '9000000000025',
            '900026': '9000000000026',
            '900027': '9000000000027',
            '900028': '9000000000028',
            '911111': '9000000000029',
            '922222': '9000000000030',
            '933333': '9000000000031',

        }
        self.customer_number = card_number_mapping[self.customer_number]

        if credentials.get('card_number') != self.customer_number:
            self.identifier = {'card_number': self.customer_number}

        return

    def balance(self):
        return {
            'points': self.user_info['points'],
            'value': Decimal(0),
            'value_label': '',
            'reward_tier': 1
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]

    def register(self, credentials):
        self.errors = {
            ACCOUNT_ALREADY_EXISTS: 'AlreadyExists',
            STATUS_REGISTRATION_FAILED: 'Invalid',
            UNKNOWN: 'Fail'
        }
        data = {
            'username': credentials['email'],
            'email': credentials['email'],
            'password': credentials['password'],
            'title': credentials['title'],
            'forename': credentials['first_name'],
            'surname': credentials['last_name'],
            'applicationId': 'BINK_APP'
        }
        if credentials.get('phone'):
            data['phone'] = credentials['phone']

        register_response = self._validate_credentials(data)

        if register_response == 'Success':
            return {"message": "success"}

        self.handle_errors(register_response, exception_type=RegistrationError)

    @staticmethod
    def _validate_credentials(data):
        for user, info in users.items():
            check_email = info['credentials']['email']
            check_password = info['credentials']['password']
            if data['email'] == check_email and data['password'] == check_password:
                return 'AlreadyExists'

        titles = ['Mr', 'Mrs', 'Miss', 'Ms', 'Dame', 'Sir', 'Doctor', 'Professor', 'Lord', 'Lady']
        if data['title'].capitalize() not in titles or len(data['password']) < 6:
            return 'Invalid'
        elif data['email'].lower() == 'fail@unknown.com':
            return 'Fail'

        return 'Success'


class MockAgentIce(MerchantApi):
    retry_limit = None
    point_conversion_rate = Decimal('1')
    card_number_mapping = {
        '0000000000000000000': '000000',
        '1111111111111111111': '111111',
        '5555555555555555555': '555555',
        '6666666666666666666': '666666',
        '1020304050607086666': '123456',
        '1020304050607087777': '234567',
        # QA Automated Test Fixtures
        '9123123123001122330': '222220',
        '9123123123001122335': '222225',
        # New fixtures
        '9000000000000000001': '900001',
        '9000000000000000002': '900002',
        '9000000000000000003': '900003',
        '9000000000000000004': '900004',
        '9000000000000000005': '900005',
        '9000000000000000006': '900006',
        '9000000000000000007': '900007',
        '9000000000000000008': '900008',
        '9000000000000000009': '900009',
        '9000000000000000010': '900010',
        '9000000000000000011': '900011',
        '9000000000000000012': '900012',
        '9000000000000000013': '900013',
        '9000000000000000014': '900014',
        '9000000000000000015': '900015',
        '9000000000000000016': '900016',
        '9000000000000000017': '900017',
        '9991112223334445000': '999000',
    }

    def login(self, credentials):
        self.identifier = {}
        if all(cred in credentials for cred in ['title', 'first_name', 'last_name', 'phone', 'email', 'date_of_birth',
                                                'postcode', 'county', 'town_city', 'address_1', 'address_2']):
            self.user_info = users['000000']
            self.customer_number = credentials.get('card_number') or credentials.get('barcode')
            if not self.customer_number:
                card_suffix = random.randint(0, 999999999999999)
                self.customer_number = f'9000{card_suffix:015d}'

            self.identifier['card_number'] = self.customer_number
            self.identifier['barcode'] = self.customer_number
            self.identifier['merchant_identifier'] = 'testregister'
        else:
            if credentials.get('merchant_identifier') == 'testregister':
                self.user_info = users['000000']
                return

            self.customer_number = credentials.get('card_number') or credentials.get('barcode')
            try:
                card_number = self.card_number_mapping[self.customer_number]
            except (KeyError, TypeError):
                raise LoginError(STATUS_LOGIN_FAILED)

            if card_number == '999000':
                sleep(20)

            self.user_info = get_user(card_number)
            login_credentials = (credentials['last_name'].lower(), credentials['postcode'].lower())
            auth_check = (self.user_info['credentials']['last_name'], self.user_info['credentials']['postcode'])

            if login_credentials != auth_check:
                raise LoginError(STATUS_LOGIN_FAILED)

            self.add_missing_credentials(credentials)

        return

    def add_missing_credentials(self, credentials):
        if not credentials.get('merchant_identifier'):
            self.identifier['merchant_identifier'] = '2900001'
        if not credentials.get('card_number'):
            self.identifier['card_number'] = self.customer_number
        if not credentials.get('barcode'):
            self.identifier['barcode'] = self.customer_number

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points)

        return {
            'points': self.user_info['points'],
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]

    def register(self, credentials, inbound=False):
        return self._validate_credentials(credentials)

    def _validate_credentials(self, data):
        ghost_card = data.get('card_number') or data.get('barcode')
        if ghost_card and ghost_card in self.card_number_mapping:
            raise RegistrationError(ACCOUNT_ALREADY_EXISTS)

        for user, info in users.items():
            try:
                check_email = info['credentials']['email']
                if data['email'] == check_email:
                    raise RegistrationError(ACCOUNT_ALREADY_EXISTS)
            except KeyError:
                continue

        if data['postcode'].lower() == 'fail':
            raise RegistrationError(UNKNOWN)

        return {"message": "success"}


class MockAgentCI(ApiMiner):
    retry_limit = None
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        card_number = credentials.get('card_number') or credentials.get('barcode')
        card_number_mapping = {
            '00000000': '000000',
            '11111111': '111111',
            '55555555': '555555',
            '66666666': '666666',
            '1026666': '123456',
            '1027777': '234567',
            # QA Automated Test Fixtures
            '00002220': '222220',
            '00002225': '222225',
            # New fixtures
            '00009001': '900001',
            '00009002': '900002',
            '00009003': '900003',
            '00009004': '900004',
            '00009005': '900005',
            '00009006': '900006',
            '00009007': '900007',
            '00009008': '900008',
            '00009009': '900009',
            '00009010': '900010',
            '00009011': '900011',
            '00009012': '900012',
            '00009013': '900013',
            '00009014': '900014',
            '00009015': '900015',
            '00009016': '900016',
            '00009017': '900017',

        }
        try:
            card_number = card_number_mapping[card_number]
        except (KeyError, TypeError):
            raise LoginError(STATUS_LOGIN_FAILED)

        self.user_info = get_user(card_number)
        if credentials['email'].lower() != self.user_info['credentials']['email']:
            raise LoginError(STATUS_LOGIN_FAILED)

        return

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points)

        return {
            'points': self.user_info['points'],
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]


class MockAgentCoop(MerchantApi):
    retry_limit = None
    point_conversion_rate = Decimal('1')
    card_number_mapping = {
        '633174910000000000': '000000',
        '633174911111111111': '111111',
        '633174915555555555': '555555',
        '633174916666666666': '666666',
        '633174915060706666': '123456',
        '633174915060707777': '234567',
        # QA Automated Test Fixtures
        '633174912301122330': '222220',
        '633174912301122335': '222225',
        # New fixtures
        '633174910000000001': '900001',
        '633174910000000002': '900002',
        '633174910000000003': '900003',
        '633174910000000004': '900004',
        '633174910000000005': '900005',
        '633174910000000006': '900006',
        '633174910000000007': '900007',
        '633174910000000008': '900008',
        '633174910000000009': '900009',
        '633174910000000010': '900010',
        '633174910000000011': '900011',
        '633174910000000012': '900012',
        '633174910000000013': '900013',
        '633174910000000014': '900014',
        '633174910000000015': '900015',
        '633174910000000016': '900016',
        '633174910000000017': '900017',
        '633174919991234500': '999000',
    }

    def login(self, credentials):
        self.identifier = {}
        if all(cred in credentials for cred in ['title', 'first_name', 'last_name', 'email', 'date_of_birth',
                                                'postcode', 'town_city', 'address_1']):
            self.user_info = users['000000']
            try:
                self.customer_number = credentials['card_number']
            except KeyError:
                card_suffix = random.randint(0, 9999999999)
                self.customer_number = f'63317491{card_suffix:010d}'

            self.identifier['card_number'] = self.customer_number
            self.identifier['merchant_identifier'] = 'testregister'

        else:
            if credentials.get('merchant_identifier') == 'testregister':
                self.user_info = users['000000']
                return

            self.customer_number = credentials.get('card_number')
            try:
                user_number = self.card_number_mapping[self.customer_number]
            except (KeyError, TypeError):
                raise LoginError(CARD_NUMBER_ERROR)

            self.user_info = get_user(user_number)
            login_credentials = (credentials['postcode'].lower(), credentials['date_of_birth'])
            auth_check = (self.user_info['credentials']['postcode'], self.user_info['credentials']['date_of_birth'])

            if login_credentials != auth_check:
                raise LoginError(STATUS_LOGIN_FAILED)

            if not credentials.get('merchant_identifier'):
                self.identifier['merchant_identifier'] = '4000000000001'

        return

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points)

        return {
            'points': self.user_info['points'],
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]

    def register(self, credentials, inbound=False):
        return self._validate_credentials(credentials)

    def _validate_credentials(self, data):
        ghost_card = data.get('card_number')
        if ghost_card and ghost_card in self.card_number_mapping:
            raise RegistrationError(ACCOUNT_ALREADY_EXISTS)

        for user, info in users.items():
            try:
                check_email = info['credentials']['email']
                if data['email'] == check_email:
                    raise RegistrationError(ACCOUNT_ALREADY_EXISTS)
            except KeyError:
                continue

        titles = ['Mr', 'Mrs', 'Miss', 'Ms', 'Mx', 'Dr', 'Doctor', 'Prefer not to say']
        if data['title'].capitalize() not in titles:
            raise RegistrationError(STATUS_REGISTRATION_FAILED)
        elif data['postcode'].lower() == 'fail':
            raise RegistrationError(UNKNOWN)

        return {"message": "success"}
