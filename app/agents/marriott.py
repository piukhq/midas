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
    card_balance = Decimal('0')
    points = Decimal('0')

    def login(self, credentials):
        display = Xvfb()
        display.start()

        firefox_profile = webdriver.FirefoxProfile()
        firefox_profile.set_preference('permissions.default.image', 2)
        firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')

        web_driver = webdriver.Firefox(firefox_profile=firefox_profile)
        web_driver.implicitly_wait(30)

        web_driver.get('https://www.marriott.co.uk/Channels/rewards/signIn-uk.mi')

        web_driver.find_element_by_xpath('//input[@id="field-user-id"]').send_keys(credentials['email'])
        web_driver.find_element_by_xpath('//input[@id="field-password"]').send_keys(credentials['password'])
        web_driver.find_element_by_xpath('//div[@id="layout-body"]/form/div/div/div/button').click()

        try:
            id = 'header-rewards-panel-trigger'
            WebDriverWait(web_driver, 7).until(
                lambda web_driver: web_driver.find_element_by_id(id)
            )

            points_xpath = '//a[@id="header-rewards-panel-trigger"]/span[@class="t-header-subtext"]'
            points_element = web_driver.find_element_by_xpath(points_xpath)
            self.points = extract_decimal(points_element.text)

        except:
            raise LoginError(STATUS_LOGIN_FAILED)

        finally:
            web_driver.quit()
            display.stop()

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
