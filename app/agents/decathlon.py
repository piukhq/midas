from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN
import re


class Decathlon(Miner):
    json_pattern = re.compile('__gwt_jsonp__\.P\d+\.onSuccess\((.*)\)')
    point_conversion_rate = Decimal('0.004')

    def login(self, credentials):
        self.open_url('https://www.decathlon.co.uk/en/loginAjax'
                      '?USERNAME={}&PASSWORD={}'.format(credentials['email'], credentials['password']))

        result = self.browser.select('p')[0].text.strip()
        if result != 'Connected':
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        self.open_url('https://www.decathlon.co.uk/en/mydktAvantages'
                      '?currentMenu=MenuMyAccountWebLinkAvantages#nomPage=defaut')

        points = extract_decimal(
            self.browser.select('#menu-my-account-infos-loyalty-card-point span.loyalty-content')[0].text)

        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.format_label(value, '£5 voucher'),
        }

    def transactions(self):
        return None
