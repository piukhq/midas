from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from selenium import webdriver
from xvfbwrapper import Xvfb
from decimal import Decimal, ROUND_DOWN


class Starbucks(RoboBrowserMiner):
    web_driver = None
    card_balance = Decimal('0')
    points = Decimal('0')

    def login(self, credentials):
        display = Xvfb()
        display.start()

        chrome_options = webdriver.ChromeOptions()
        prefs = {
            "profile.managed_default_content_settings.images": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)

        web_driver = webdriver.Chrome(chrome_options=chrome_options)
        web_driver.implicitly_wait(30)

        web_driver.get('https://www.starbucks.co.uk/account/signin')

        web_driver.find_element_by_xpath('//input[@placeholder="Username or email"]').send_keys(credentials['username'])
        web_driver.find_element_by_xpath('//input[@placeholder="Password"]').send_keys(credentials['password'])
        web_driver.find_element_by_xpath('//*[@id="AT_SignIn_Button"]').click()

        # Try to get the account details.
        try:
            # Get pre-paid card balance.
            self.card_balance = extract_decimal(web_driver.find_element_by_xpath(
                '//*[@id="selected_card"]/div/span[1]/span[2]/span/span[3]').text)

            # Get points details.
            self.points = extract_decimal(web_driver.find_element_by_xpath(
                '//*[@id="stars_and_rewards_section"]/div[3]/figure/figcaption/span[1]').text)
        except:
            # If getting the account status failed, then it likely means we failed to log in.
            raise LoginError(STATUS_LOGIN_FAILED)
        finally:
            # Make sure we clean up after ourselves, or Chrome will crash when the virtual display closes.
            web_driver.quit()
            display.stop()

    def balance(self):
        return {
            'points': self.points,
            'value': Decimal('0'),
            'balance': self.card_balance,
            'value_label': '{}/15 coffees'.format(self.points.quantize(0, ROUND_DOWN)),
        }
