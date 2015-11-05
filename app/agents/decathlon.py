from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal
import re


class Decathlon(Miner):
    json_pattern = re.compile('__gwt_jsonp__\.P\d+\.onSuccess\((.*)\)')
    point_conversion_rate = Decimal('0.02')

    def login(self, credentials):
        url = ('https://www.decathlon.co.uk/en/loginAjax'
               '?USERNAME={}&PASSWORD={}').format(credentials['email'], credentials['password'])

        self.open_url(url)

        result = self.browser.select('p')[0].text.strip()
        if result != 'Connected':
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        self.open_url('https://www.decathlon.co.uk/en/mydktAvantages'
                      '?currentMenu=MenuMyAccountWebLinkAvantages#nomPage=defaut')

        points = extract_decimal(
            self.browser.select('#menu-my-account-infos-loyalty-card-point span.loyalty-content')[0].text)

        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    def transactions(self):
        return None
