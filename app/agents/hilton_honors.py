import arrow
import random
import time

from app.agents.base import Miner
from app.agents.exceptions import LoginError, AgentError, TRIPPED_CAPTCHA
from app.agents.exceptions import STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from xvfbwrapper import Xvfb
from selenium.webdriver.common.keys import Keys


class Hilton(Miner):

    MAX_WAITING_TIME_SELENIUM = 5
    LOGIN_URL = 'https://secure3.hilton.com/en/hh/customer/login/index.htm'
    ALL_TRANSACTION_URL = 'https://secure3.hilton.com/en/hh/customer/account/allPointActivity.htm'
    POINTS_PATH = '//div[@id="my_account_grid_top_middle"]/h2/strong[@class="points"]'
    TRANSACTION_TABLE_PATH = '//html/body/div[@id="body_wrapper"]/div/div[@id="main_content"]/div/div/div/' \
        'table[@class="hhonors_table accordion "]/tbody'

    def __init__(self, retry_count, scheme_id):
        self.display = Xvfb()
        self.display.start()

        firefox_profile = webdriver.FirefoxProfile()
        firefox_profile.set_preference('permissions.default.image', 2)
        firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
        self.browser = webdriver.Firefox(firefox_profile=firefox_profile)

        self.browser.implicitly_wait(self.MAX_WAITING_TIME_SELENIUM)

        self.scheme_id = scheme_id
        self.retry_count = retry_count
        self.points = None

    def login(self, credentials):
        try:
            self.browser.get(self.LOGIN_URL)

            # set username
            self.browser.find_element_by_xpath('//input[@id="username"]').send_keys(credentials['username'])
            time.sleep(random.randint(10, 20) * 0.1)  # we have less chances to get captcha

            # set password
            self.browser.find_element_by_xpath('//input[@id="password"]').send_keys(credentials['password'])
            time.sleep(random.randint(10, 20) * 0.1)  # we have less chances to get captcha

            # submit the form and login!
            self.browser.find_element_by_xpath('//input[@id="password"]').send_keys(Keys.RETURN)
            time.sleep(random.randint(10, 20) * 0.1)  # we have less chances to get captcha

        except:
            self.quit_selenium()
            raise AgentError(UNKNOWN)

        self._find_captcha()

        # get the points to be sure we are logged in
        try:
            points_elem = self.browser.find_element_by_xpath(self.POINTS_PATH)
            time.sleep(random.randint(5, 10) * 0.1)

            self.points = extract_decimal(points_elem.text)

        except:
            self.browser.implicitly_wait(0)
            error_message = self.browser.find_elements_by_id('invalidCredentials')
            self.quit_selenium()
            if len(error_message) == 0:
                raise AgentError(UNKNOWN)

            else:
                raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        return {
            'points': self.points,
            'value': Decimal('0'), '\n'
            'value_label': ''
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['date'], 'D MMM YYYY'),
            'description': row['description'],
            'points': Decimal(row['points_earned'])
        }

    def scrape_transactions(self):
        try:
            self.browser.get(self.ALL_TRANSACTION_URL)

            transactions = []
            table = self.browser.find_element_by_xpath(self.TRANSACTION_TABLE_PATH)
            rows = table.find_elements_by_tag_name('tr')

            for row in rows:
                columns = row.find_elements_by_tag_name('td')

                if len(columns) > 1:
                    # Filter row with 1 column as they are just empty
                    # Expected structure: [0]Date| [1]''| [2]Description| [3]''|
                    #                     [4]Points Earned| [5] Miles earned| [6]Action
                    transactions.append({
                        'date': columns[0].text,
                        'description': columns[2].text,
                        'points_earned': columns[4].text,
                        'miles_earned': columns[5].text,
                        'action': columns[6].text
                    })
            return transactions

        except:
            raise AgentError(UNKNOWN)

        finally:
            self.quit_selenium()

    def _find_captcha(self):
        try:
            self.browser.find_element_by_id('divcaptcha')
            # if does not raise NoSuchElementException we have a captcha
            self.quit_selenium()
            raise AgentError(TRIPPED_CAPTCHA)

        except NoSuchElementException:
            pass  # all good captcha not present

    def quit_selenium(self):
        self.browser.quit()
        self.display.stop()
