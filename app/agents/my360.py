from urllib.parse import urlencode
from decimal import Decimal
from app.agents.base import Miner
from app.agents.exceptions import LoginError, UNKNOWN, STATUS_LOGIN_FAILED, END_SITE_DOWN
from app.active import AGENTS
import json


# list_of_active_my360_schemes = [my360_scheme for scheme in AGENTS if AGENTS[scheme] == 'my360.My360']
class My360(Miner):
    points = None
    scheme_dictionary = {
        'stansted-farm': '',
        'the-courtyard': '',
        '19-fourteas-tea-rooms': '',
        'bored-of-southsea': '',
        'game-over-café': '',
        'mad-hatters': '',
        'watkins-and-faux': '',
        'northney-farm-tea-room': '',
        'shakeadelic': '',
        'drift-bar': '',
        'poppins-restaurant': '',
        'polka-dot-piercing': '',
        'nanoo-hair': '',
        'comics-games-and-coffee': '',
        'the-richmond': '',
        'tennessee-chicken': '',
        'cliff-roe-sports': '',
        'michael-chell': '',
        'the-food-cellar': '-fdK4i',
        'hewetts': '',
        'fit-stuff': '',
        'café-copia': '',
        'bear-garden': '',
        'fresco-delikafessen': '',
        'henley-sports': '',
        'the-chocolate-café': '',
        'ted-james-barbershop': '',
        'bubble-city': '',
        'peewees': '',
        'turners-pies': '',
        'the-vestry': '',
        'laurence-menswear': '',
        'gatsby-menswear': '',
        'celo-tan-and-lash': '',
        'linda-h': '',
        'moffats': '',
        'tiffin-tea-rooms': '',
        'strawberry-vibes': '',
        'magoos': '',
        'ians-barbers': '',
        'everybody-pilates': '',
        'nevaeh-hair': '',
        'the-marmion': '',
        'funland': '',
        'the-nags-head': '',
        'beauty-clinic': '',
        'grit-gym-mma-and-fitness': '',
        'hilites-hair-and-beauty': '',
        'the-coffee-co': '',
        'thousand-hills': '',
        'urban-food': '',
        'dhaba-lane': '',
    }

    def is_login_successful(self):
        if self.points:
            return True

        else:
            return False

    def login(self, credentials):
        user_identifier = credentials['barcode']
        scheme_api_identifier = self.scheme_dictionary[self.scheme_slug]

        url = 'https://rewards.api.mygravity.co/v2/reward_scheme/{0}/user/{1}/check_balance'.format(
            scheme_api_identifier,
            user_identifier
        )
        self.browser.open(url)

        try:
            loyalty_data = self.browser.response.json()

        except:
            if self.browser.response.status_code == 404:
                raise ValueError('Status code 404 does not equal 200: Please check user / scheme ID')

            else:
                raise LoginError(END_SITE_DOWN)

        if all(key in ['points', 'valid', 'uid'] for key in loyalty_data.keys()):
            if not loyalty_data['valid']:
                raise LoginError(STATUS_LOGIN_FAILED)

            elif loyalty_data['valid']:
                self.points = loyalty_data['points']

        elif 'error' in loyalty_data:
            if self.browser.response.status_code == 401:
                raise ValueError('Invalid scheme ID used')

            elif loyalty_data['error'].startswith("500"):
                raise LoginError(STATUS_LOGIN_FAILED)

            else:
                raise LoginError(UNKNOWN)

        else:
            raise LoginError(UNKNOWN)

    def balance(self):
        return {
            'points': Decimal(self.points),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
