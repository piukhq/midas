from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Maximiles(Miner):
    point_conversion_rate = Decimal('0.0009')

    def login(self, credentials):
        self.open_url('http://www.maximiles.co.uk/my-account/login')

        self.headers = {
            'Host': 'www.maximiles.co.uk',
            'Connection': 'keep-alive',
            'Content-Length': '140',
            'Cache-Control': 'max-age=0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Origin': 'http://www.maximiles.co.uk',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.75 '
                          'Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'http://www.maximiles.co.uk/my-account/login',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-GB,en-US;q=0.8,en;q=0.6',
        }

        login_form = self.browser.get_form('infos')
        login_form['maximiles_id'].value = credentials['email']
        login_form['passe'].value = credentials['password']

        self.browser.submit_form(login_form, headers=self.headers)

        selector = 'div.error > ul > li'
        self.check_error('/my-account/login', ((selector, STATUS_LOGIN_FAILED, 'Invalid Username/password'),))

    def balance(self):
        points = extract_decimal(self.browser.select('#global #main #colLeft h1 strong')[0].text)
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
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
