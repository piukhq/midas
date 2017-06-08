from app.agents.base import Miner
from app.agents.exceptions import LoginError
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from selenium import webdriver
from xvfbwrapper import Xvfb
from decimal import Decimal
from selenium.webdriver.support.ui import WebDriverWait


class Marriott(Miner):

    web_driver = None
    points = None

    def login(self, credentials):
        try:
            self.display = Xvfb()
            self.display.start()

            firefox_profile = webdriver.FirefoxProfile()
            firefox_profile.set_preference('permissions.default.image', 2)

            self.web_driver = webdriver.Firefox(firefox_profile=firefox_profile)
            self.web_driver.implicitly_wait(15)

            self.web_driver.get('https://www.marriott.co.uk/Channels/rewards/signIn-uk.mi')

            self.web_driver.find_element_by_xpath('//input[@id="field-user-id"]').send_keys(credentials['email'])
            self.web_driver.find_element_by_xpath('//input[@id="field-password"]').send_keys(credentials['password'])
            self.web_driver.find_element_by_xpath('//div[@id="layout-body"]/form/div/div/div/button').click()

            id = 'header-rewards-panel-trigger'
            WebDriverWait(self.web_driver, 7).until(
                lambda web_driver: self.web_driver.find_element_by_id(id)
            )

            points_xpath = '//dl[@class="l-password-actions l-margin-bottom-three-quarters"]' \
                           '/dd[@class="t-font-semi-bold t-form-font"]'
            points_element = self.web_driver.find_element_by_xpath(points_xpath)
            self.points = extract_decimal(points_element.text)
            self.quit_selenium()

        except:
            try:
                error_element = '//div[@class="l-message-box t-error-msg l-clear clearfix"]/ul/li'
                error_text = 'Incorrect email address, Rewards number and/or password.'
                self.web_driver.implicitly_wait(0)
                if self.web_driver.find_element_by_xpath(error_element).text == error_text:
                    self.quit_selenium()
                    raise LoginError(STATUS_LOGIN_FAILED)
                    pass
            except Exception as e:
                self.quit_selenium()
                raise e

    def balance(self):
        return {
            'points': self.points,
            'value': Decimal('0'),
            'value_label': ''
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []

    def quit_selenium(self):
        try:
            self.web_driver.quit()
            self.display.stop()

        except Exception as e:
            self.display.stop()
            raise e
