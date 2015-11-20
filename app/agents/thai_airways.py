from app.agents.base import Miner


class ThaiAirways(Miner):
    def login(self, credentials):
        url = 'http://www.thaiair.com/AIP_ROP/Logon'
        data = {
            'LanguagePreference': 'EN',
            'submit': '',
            'userid': credentials['username'],
            'pin': credentials['pin'],
        }

        self.browser.open(url, method='post', data=data)
