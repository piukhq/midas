from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN
import execjs
import json
import re
import os


class Decathlon(Miner):
    json_pattern = re.compile('__gwt_jsonp__\.P\d+\.onSuccess\((.*)\)')
    point_conversion_rate = Decimal('0.004')

    def login(self, credentials):
        script_dir = os.path.dirname(__file__)
        rel_path = 'js/decathlon-decode.js'
        decoder_path = os.path.join(script_dir, rel_path)
        with open(decoder_path) as decode_js:
            js = decode_js.read()
            decoder = execjs.compile(js)

        result = decoder.call('hash_credentials', credentials['email'], credentials['password'])

        mdp = result['mdp']
        email = result['email']
        url = (
            'https://back.mydecathlon.com/mydkt-server-mvc/ajax'
            '/private/authentification/connexionCode'
            '?ppays=GB'
            '&codeAppli=Osmose'
            '&response_type=code'
            '&client_id=osmose_ecuk'
            '&langue=en'
            '&host=www.decathlon.co.uk'
            '&resterConnecter=true'
            '&mdp={}'
            '&email={}'
            '&__preventCache__=1450195310293'
            '&callback='
        ).format(mdp, email)

        self.open_url(url)
        resp = json.loads(self.browser.response.text[1:-1])

    def balance(self):
        self.open_url('https://www.decathlon.co.uk/en/viewprofile')
        points = extract_decimal(self.browser.select
                                 ('#menu-my-account-infos-loyalty-card-point > span.loyalty-content')[0].text.strip())
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.format_label(value, '£5 voucher'),
        }

    def scrape_transactions(self):
        return None
