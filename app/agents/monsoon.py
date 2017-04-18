from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Monsoon(Miner):
    domain = 'https://uk.monsoon.co.uk'

    login_path = '/view/secured/content/login'

    def is_login_successful(self):
        selector = '#myacc_header [href="/view/secured/myaccount/summary"] span'
        spans = self.browser.select(selector)
        return spans[1].get_text().strip() != 'Sign In or Register'

    def login(self, credentials):
        self.open_url(self.domain + self.login_path, verify=False)

        login_form = self.browser.get_form(action='/j_spring_security_check')
        login_form['j_username'].value = credentials['email']
        login_form['j_password'].value = credentials['password']
        login_form['componentUid'] = 'loginComponent'
        login_form['currentUrl'] = self.login_path

        self.headers['Host'] = 'eu.monsoon.co.uk'
        self.headers['Origin'] = self.domain
        self.headers['Referer'] = self.domain + self.login_path

        self.browser.submit_form(login_form)

        self.check_error(self.login_path,
                         (('div.login_main_error_box.generic_form_error', STATUS_LOGIN_FAILED, 'Sign In Failed'), ))

    def balance(self):
        self.open_url(self.domain + "/view/secured/myaccount/rewardcard")

        value_selector = 'div.myaccount_personaldetails_edit.rewardcard_points > div.section_info_right p'
        points_selector = 'div.myaccount_personaldetails_edit.rewardcard_points > div.section_info_left > p'
        value = extract_decimal(self.browser.select(value_selector)[0].contents[0])
        return {
            'points': extract_decimal(self.browser.select(points_selector)[0].contents[0]),
            'value': value,
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # self.open_url('https://uk.monsoon.co.uk/view/secured/content/myaccount?activeTab=cs_myaccounttab')
        return []
