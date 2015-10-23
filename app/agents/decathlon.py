from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal, ROUND_FLOOR
from math import floor
import json
import re
import arrow


class Decathlon(Miner):
    json_pattern = re.compile('__gwt_jsonp__\.P\d+\.onSuccess\((.*)\)')

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

    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        # Obtain the account token.
        self.open_url('https://back.mydecathlon.com/mydkt-server-mvc/ajax/private/authentification/connexionCode'
                      '?ppays=GB&codeAppli=Osmose&response_type=code&client_id=osmose_ecuk&langue=en'
                      '&host=www.decathlon.co.uk&resterConnecter=true'
                      '&mdp=tBlZFD4vFf9iF1x4&email=O1bwQNsqP19wRMvfUJtYRMKqO19p'
                      '&__preventCache__=1445596341121&callback=__gwt_jsonp__.P1.onSuccess')

        token_response = json.loads(self.json_pattern.findall(self.browser.response.text)[0])
        token = token_response['data']['token']

        self.open_url('http://back.mydecathlon.com/mydkt-server-mvc/ajax/private/tickets/liste'
                      '?ppays=GB&isStoreReceipt=t&isTransfert=false&esdljkdl={}'
                      '&__preventCache__=1445600047005&callback=__gwt_jsonp__.P9.onSuccess'.format(token))
        first_response = json.loads(self.json_pattern.findall(self.browser.response.text)[0])

        self.open_url('http://back.mydecathlon.com/mydkt-server-mvc/ajax/private/tickets/listeDetail'
                      '?ppays=GB&isStoreReceipt=t&isTransfert=false'
                      '&entetes=%5B%7B%22typeTiers%22%3A7%2C+%22numTiers%22%3A718%2C+%22sousNumTiers'
                      '%22%3A718%2C+%22tetId%22%3A404543%7D%5D&esdljkdl={}&__preventCache__=1445600047072'
                      '&callback=__gwt_jsonp__.P10.onSuccess'.format(token))
        second_response = json.loads(self.json_pattern.findall(self.browser.response.text)[0])

        rows = [{
            'date': arrow.get(first_response['data'][x]['dateTicket'].strip(), 'YYYY-MM-DD'),
            'description': 'Purchase at a {} store.'.format(first_response['data'][x]['nomTiers'].title()),
            'points': Decimal(floor(second_response['data'][x]['montantTicket'])),
            'location': first_response['data'][x]['nomTiers'].title(),
        } for x in range(len(first_response['data']))]

        return [self.hashed_transaction(row) for row in rows]
