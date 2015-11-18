from app.agents.base import Miner


class MyMail(Miner):
    def login(self, credentials):
        self.browser.open('https://www.mymail.co.uk/login', verify=False)

        data = {
            'rememberMe': True,
            'username': credentials['email'],
            'password': credentials['password'],
        }

        # Angular sets this header as cross-site request forgery protection.
        headers = {'X-XSRF-TOKEN': self.browser.session.cookies._cookies['www.mymail.co.uk']['/']['XSRF-TOKEN'].value}
        self.browser.open('https://www.mymail.co.uk/login', method='post', json=data, headers=headers, verify=False)

    def balance(self):
        raise NotImplementedError

    def transactions(self):
        raise NotImplementedError
