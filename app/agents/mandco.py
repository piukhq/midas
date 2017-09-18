from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN
import arrow


class MandCo(RoboBrowserMiner):
    point_conversion_rate = Decimal('0.002')

    def login(self, credentials):
        self.open_url('https://www.mandco.com/on/demandware.store/Sites-mandco-Site/default/LoyaltyCard-Show')
        login_form = self.browser.get_form('dwfrm_login')

        # The email field name is partially scrambled.
        for k, v in login_form.fields.items():
            if v.name.startswith('dwfrm_login_username'):
                login_form[k].value = credentials['username']
                break

        login_form['dwfrm_login_password'].value = credentials['password']

        post_data = {}
        post_data['dwfrm_login_login'] = 'Login'
        for k, v in login_form.fields.items():
            post_data[k] = v.value

        self.open_url(login_form.action, method='post', data=post_data)

        error_box = self.browser.select('#dwfrm_login div.error-form')
        if len(error_box) > 0 and error_box[0].text.startswith('Oops, this email address and password'):
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        points = extract_decimal(self.browser.select('.loyalty-card-content-wraper p strong')[0].text)
        reward_qty = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.format_label(reward_qty, '£5 reward voucher')
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
