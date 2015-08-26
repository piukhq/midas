
class Miner(object):
    def __init__(self):
        self.browser = self.login()

    def login(self):
        raise NotImplementedError()

    def balance(self):
        raise NotImplementedError()

    def transactions(self):
        raise NotImplementedError()
