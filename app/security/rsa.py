import base64

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA as CRYPTO_RSA
from Crypto.Signature import PKCS1_v1_5

from app.agents.exceptions import AgentError, VALIDATION


class RSA:
    """
    Generate and verify requests with an RSA signature.
    """

    def __init__(self, credentials):
        """
        :param credentials: list if dicts e.g
        [{'type': 'bink_private_key', 'storage_key': 'vaultkey', 'value': 'keyvalue'}]
        """
        self.credentials = credentials

    def encode(self, json):
        """
        :param json: json string of payload
        :return: dict of parameters to be unpacked for requests.post()
        """
        key = CRYPTO_RSA.importKey(self._get_key('bink_private_key'))
        digest = SHA256.new(json.encode('utf8'))
        signer = PKCS1_v1_5.new(key)
        signature = signer.sign(digest)

        encoded_request = {
            'json': json,
            'headers': {
                'Authorization': base64.b64encode(signature)
            }
        }
        return encoded_request

    def decode(self, request):
        """
        :param request: request object
        :return: json string of payload
        """
        key = CRYPTO_RSA.importKey(self._get_key('merchant_public_key'))
        digest = SHA256.new(request.json.encode('utf8'))
        signer = PKCS1_v1_5.new(key)
        signature = base64.b64decode(request.headers['AUTHORIZATION'])

        verified = signer.verify(digest, signature)
        if not verified:
            raise AgentError(VALIDATION)

        return request.content

    def _get_key(self, key_type):
        for item in self.credentials:
            if item['type'] == key_type:
                return item['value']
        raise KeyError('{} not in credentials')
