import base64

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA as CRYPTO_RSA
from Crypto.Signature import PKCS1_v1_5

from app.agents.exceptions import AgentError, VALIDATION
from app.security.base import BaseSecurity


class RSA(BaseSecurity):
    """
    Generate and verify requests with an RSA signature.
    """
    def encode(self, json_data):
        """
        :param json_data: json string of payload
        :return: dict of parameters to be unpacked for requests.post()
        """
        json_data = self._add_timestamp(json_data)

        key = CRYPTO_RSA.importKey(self._get_key('bink_private_key'))
        digest = SHA256.new(json_data.encode('utf8'))
        signer = PKCS1_v1_5.new(key)
        signature = signer.sign(digest)

        encoded_request = {
            'json': json_data,
            'headers': {
                'Authorization': 'Signature {}'.format(base64.b64encode(signature))
            }
        }
        return encoded_request

    def decode(self, request):
        """
        :param request: request object
        :return: json string of payload
        """
        self._validate_timestamp(request.json)

        key = CRYPTO_RSA.importKey(self._get_key('merchant_public_key'))
        digest = SHA256.new(request.content.encode('utf8'))
        signer = PKCS1_v1_5.new(key)
        signature = base64.b64decode(request.headers['AUTHORIZATION'])

        verified = signer.verify(digest, signature)
        if not verified:
            raise AgentError(VALIDATION)

        return request.content
