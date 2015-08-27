import hashlib
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

    @staticmethod
    def parse_transaction(row):
        raise NotImplementedError()

    def hashed_transaction(self, transaction):
        transaction = self.parse_transaction(transaction)
        s = "{0}{1}{2}".format(transaction['date'], transaction['title'], transaction['points'])
        transaction["hash"] = hashlib.md5(s.encode("utf-8")).hexdigest()
        return transaction
