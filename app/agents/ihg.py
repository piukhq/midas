import json
from time import sleep
from decimal import Decimal

import arrow
from selenium.common.exceptions import NoSuchElementException

from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Ihg(SeleniumMiner):
    is_login_successful = None
    is_async = True

    def check_for_popup_window(self):
        self.browser.implicitly_wait(2)
        try:
            popup = self.browser.find_element_by_name("IPEMap")
            if popup.is_displayed():
                raise Exception("There is a popup window that is blocking us.")

        except NoSuchElementException:
            self.browser.implicitly_wait(20)

        except Exception as e:
            raise e

    def check_for_error_msg(self):
        try:
            error_messages = self.browser.find_elements_by_class_name("errorTopMsgText")
            error_messages.extend(self.browser.find_elements_by_class_name("errorMsg"))
            for error_msg in error_messages:
                if error_msg.is_displayed():
                    raise LoginError(STATUS_LOGIN_FAILED)

        except LoginError as exception:
            raise exception

    def check_if_logged_in(self):
        account_url = "https://www.ihg.com/rewardsclub/gb/en/account-mgmt/home"
        self.browser.get(account_url)

        if self.browser.current_url == account_url:
            self.is_login_successful = True
        else:
            self.is_login_successful = False
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        sign_in_url = ("https://www.ihg.com/rewardsclub/gb/en/sign-in/?fwdest="
                       "https://www.ihg.com/rewardsclub/content/gb/en/home&displayCaptcha=true")

        self.browser.get("https://www.ihg.com/rewardsclub/content/gb/en/home")
        self.check_for_popup_window()
        try:
            self.browser.find_element_by_class_name('logIn-link').click()
            self.browser.find_element_by_id('UHF_username').send_keys(credentials['username'])
            self.browser.find_element_by_id('UHF_password').send_keys(credentials['pin'])
            self.browser.find_element_by_class_name('signIn').click()
            sleep(3)
            self.check_for_error_msg()

        except LoginError as exception:
            raise exception

        else:
            if self.browser.current_url == sign_in_url:
                self._login_with_last_name(credentials=credentials)

    def _login_with_last_name(self, credentials):
        self.browser.find_element_by_css_selector(
            "form[name='tpiSignIn'] input[maxlength='75']").send_keys(credentials['username'])
        self.browser.find_element_by_css_selector(
            "form[name='tpiSignIn'] input[maxlength='4']").send_keys(credentials['pin'])
        self.browser.find_element_by_css_selector("input[name='lastName']").send_keys(credentials['last_name'])
        self.browser.find_element_by_class_name("cta-1").click()
        sleep(3)
        self.check_for_error_msg()

    def login(self, credentials):
        self.browser.implicitly_wait(20)
        try:
            self._login(credentials=credentials)
        except Exception:
            self.is_login_successful = False
            raise

        self.check_if_logged_in()
        sleep(2)
        point_text = self.browser.find_element_by_class_name('user-points').text
        self.points = extract_decimal(point_text)

        self.browser.get('https://www.ihg.com/rewardsclub/gb/en/ws/accountActivity/get?activityType=ALL&'
                         'duration=365&rows=10&page=1')

        self.browser.find_element_by_css_selector(".rawdata").click()
        pre = self.browser.find_element_by_tag_name("pre").text
        data = json.loads(pre)
        self.transaction_data = data['accountActivityList']

    def balance(self):
        return {
            'points': self.points,
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['datePostedFormatted'], 'DD-MMM-YYYY'),
            'description': row['description'],
            'points': Decimal(row['totalPointValue']),
        }

    def scrape_transactions(self):
        return self.transaction_data
