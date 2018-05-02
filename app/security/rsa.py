import base64
import json

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
            'json': json.loads(json_data),
            'headers': {
                'Authorization': 'Signature {}'.format(base64.b64encode(signature).decode('utf8'))
            }
        }
        return encoded_request

    def decode(self, auth_header, data):
        """
        :param auth_header: base64 encoded signature decoded as a utf8 string prepended with 'Signature'
        e.g 'Signature fgdkhe3232uiuhijfjkrejwft3iuf3wkherj'
        :param data: dict of payload
        :return: json string of payload
        """
        self._validate_timestamp(data)

        json_data = json.dumps(data)

        key = CRYPTO_RSA.importKey(self._get_key('merchant_public_key'))
        digest = SHA256.new(json_data.encode('utf8'))
        signer = PKCS1_v1_5.new(key)
        encoded_sig = auth_header.replace('Signature ', '')
        signature = base64.b64decode(encoded_sig)

        verified = signer.verify(digest, signature)
        if not verified:
            raise AgentError(VALIDATION)

        return json.dumps(data)
