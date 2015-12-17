from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN
import execjs
import arrow
import json
import os


class Decathlon(Miner):
    point_conversion_rate = Decimal('0.004')

    def login(self, credentials):
        script_dir = os.path.dirname(__file__)
        rel_path = 'js/decathlon-decode.js'
        decoder_path = os.path.join(script_dir, rel_path)
        with open(decoder_path) as decode_js:
            js = decode_js.read()
            decoder = execjs.compile(js)

        result = decoder.call('hash_credentials', credentials['email'], credentials['password'])

        mdp = result['mdp']
        email = result['email']
        url = ('http://back.mydecathlon.com/mydkt-server-mvc/ajax'
               '/private/authentification/connexion'
               '?ppays=GB'
               '&codeAppli=NetCardV2'
               '&langue=EN'
               '&resterConnecter=true'
               '&mdp={}'
               '&email={}'
               '&callback='
               ).format(mdp, email)

        self.open_url(url)
        resp = json.loads(self.browser.response.text[1:-1])

        if resp['data']['codeRetour'] == '404':
            raise LoginError(STATUS_LOGIN_FAILED)

        self.token = resp['data']['token']

    def balance(self):
        self.open_url('http://back.mydecathlon.com/mydkt-server-mvc/ajax'
                      '/private/synthesePersonne/getInfoPersonne'
                      '?ppays=GB'
                      '&personneId=0'
                      '&esdljkdl={}'
                      '&callback='.format(self.token))

        resp = json.loads(self.browser.response.text[1:-1])
        points = Decimal(resp['data']['soldePoint']['solde'])

        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.format_label(value, '£5 voucher'),
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['date']),
            'description': row['description'],
            'points': extract_decimal(row['points']),
            'value': extract_decimal(row['value']),
            'location': row['location'],
        }

    def scrape_transactions(self):
        self.open_url('http://back.mydecathlon.com/mydkt-server-mvc/ajax/private'
                      '/tickets/liste'
                      '?ppays=GB'
                      '&idPersonne=0'
                      '&isStoreReceipt=t'
                      '&isTransfert=false'
                      '&esdljkdl={}'
                      '&callback='.format(self.token))

        list = json.loads(self.browser.response.text[1:-1])

        self.open_url('http://back.mydecathlon.com/mydkt-server-mvc/ajax/private'
                      '/tickets/listeDetail'
                      '?ppays=GB'
                      '&idPersonne=0'
                      '&isStoreReceipt=t'
                      '&isTransfert=false'
                      '&entetes=%5B%7B%22typeTiers%22%3A7%2C+%22sousNumTiers%22%3A718%2C'
                      '+%22numTiers%22%3A718%2C+%22tetId%22%3A404543%7D%5D'
                      '&esdljkdl={}'
                      '&callback='.format(self.token))

        detail = json.loads(self.browser.response.text[1:-1])

        transactions = []
        for i, t in enumerate(list['data']):
            d = detail['data'][i]
            transactions.append({
                'date': t['dateTicket'],
                'description': 'Transaction #{}'.format(t['tetId']),
                'points': str(d['credits'][0]['nombreDePoints']),
                'value': str(d['montantTicket']),
                'location': t['nomTiers'],
            })

        return transactions
