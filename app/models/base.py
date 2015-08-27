from robobrowser import RoboBrowser


class Miner(object):
    def __init__(self, credentials):
        self.browser = RoboBrowser(parser="lxml")
        self.login(credentials)

    def login(self, credentials):
        raise NotImplementedError()

    def balance(self):
        raise NotImplementedError()

    def transactions(self):
        raise NotImplementedError()
