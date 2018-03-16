

class RSA:
    """
    TODO: Complete functional implementation
    """

    def __init__(self, credentials):
        self.credentials = credentials

    def encode(self, json):
        encoded_request = {'json': json,
                           'headers': 'headers',
                           'other_stuff': 'stuff'}

        return encoded_request
