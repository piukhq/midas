from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal
import base64
import arrow


class TheBodyShop(Miner):
    loyalty_data = []

    def login(self, credentials):
        self.open_url('https://www.thebodyshop.com/en-gb/login')

        login_form = self.browser.get_form('loginForm')
        login_form['j_username'] = credentials['email']
        login_form['j_password'] = credentials['password']
        self.browser.submit_form(login_form)
        self.find_captcha()

        selector = ".message-container.error p"
        self.check_error('/en-gb/login', (
                             (selector, STATUS_LOGIN_FAILED, 'Incorrect username or password.'),
                             (selector, STATUS_LOGIN_FAILED, 'Problem with captcha verification')))

    def balance(self):
        # Get points and transaction data in one call.
        self.open_url('https://www.thebodyshop.com/en-gb/my-account/points')
        points = extract_decimal(self.browser.select('.progress-number')[0].text)
        self.open_url('https://www.thebodyshop.com/en-gb/my-account/vouchers')
        value = extract_decimal(self.browser.select('#formattedTotalVoucherAmount')[0].text)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
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
        return self.loyalty_data
