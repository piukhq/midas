from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal


class Decathlon(Miner):
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

        point_holder = self.browser.select('#menu-my-account-infos-loyalty-card-point span.loyalty-content')[0]
        return {
            'points': extract_decimal(point_holder.text)
        }

    def transactions(self):
        return None
