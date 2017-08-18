from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class HAndM(Miner):
    is_login_successful = False

    def _check_if_logged_in(self):
        error_url = "https://www2.hm.com/en_gb/login?error=true"

        try:
            current_url = self.browser.url
            if current_url != error_url:
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def login(self, credentials):
        self.open_url("https://www2.hm.com/en_gb/index.html")

        form_action = 'https://www2.hm.com/en_gb/j_spring_security_check'

        login_form = self.browser.get_form(action=form_action)
        login_form['j_username'].value = credentials['email']
        login_form['j_password'].value = credentials['password']

        self.browser.submit_form(login_form)

        self._check_if_logged_in()

        self.headers['Host'] = "www2.hm.com"
        self.headers['Origin'] = "http://www2.hm.com"
        self.headers['Referer'] = "http://www2.hm.com/en_gb/hmclub.fullmember.html"

        corporate_brand_id = 0
        country_code = "GB"
        email_address = credentials['email']

        balance_url = "https://www2.hm.com/en_gb/loyalty/getMember?corporate" \
                      "BrandId={}&countryCode={}&emailAddress={}" \
                      .format(corporate_brand_id, country_code, email_address)

        self.open_url(balance_url)

    def balance(self):
        points = self.browser.response.json()['pointsBalance']
        points = Decimal(points)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        date = row.select('.details-list')[0]('span')[3].text.strip()
        description_value = row.select('span.order-id')[0].text.strip()
        description_text = description_value.replace('\xa0', ' ')
        points = row.select('ul.order-table')[0]('span')[1].text

        return {
            'date': arrow.get(date),
            'description': description_text,
            'points': extract_decimal(points)
        }

    def scrape_transactions(self):
        current_url = self.browser.url
        orders_url = "https://www2.hm.com/en_gb/my-account/orders"

        if current_url != orders_url:
            self.browser.open(orders_url)

        orders = self.browser.select('.orders .order-item')[0:]
        return orders
