import base64
import json

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA as CRYPTO_RSA
from Crypto.Signature import pkcs1_15

from app.agents.exceptions import AgentError, VALIDATION, CONFIGURATION_ERROR
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
        json_data_with_timestamp, timestamp = self._add_timestamp(json_data)

        key = CRYPTO_RSA.importKey(self._get_key('bink_private_key'))
        digest = SHA256.new(json_data_with_timestamp.encode('utf8'))
        signer = pkcs1_15.new(key)
        signature = base64.b64encode(signer.sign(digest)).decode('utf8')

        encoded_request = {
            'json': json.loads(json_data),
            'headers': {
                'Authorization': 'Signature {}'.format(signature),
                'X-REQ-TIMESTAMP': timestamp
            }
        }
        return encoded_request

    def decode(self, headers, json_data):
        """
        :param headers: Request headers.

        'Authorization' is required as a base64 encoded signature decoded as a utf8 string prepended with 'Signature'.
        e.g 'Signature fgdkhe3232uiuhijfjkrejwft3iuf3wkherj=='

        Validates with timestamp found in the 'X-REQ-TIMESTAMP' header.

        :param json_data: json string of payload
        :return: json string of payload
        """
        try:
            auth_header = headers['Authorization']
            timestamp = headers['X-REQ-TIMESTAMP']
        except KeyError as e:
            raise AgentError(VALIDATION) from e

        if auth_header[0:9].lower() == 'signature':
            signature = auth_header[10:]
        else:
            raise AgentError(VALIDATION)

        self._validate_timestamp(timestamp)

        json_data_with_timestamp = '{}{}'.format(json_data, timestamp)
        try:
            key = CRYPTO_RSA.importKey(self._get_key('merchant_public_key'))
        except KeyError as e:
            raise AgentError(CONFIGURATION_ERROR) from e

        digest = SHA256.new(json_data_with_timestamp.encode('utf8'))
        signer = pkcs1_15.new(key)
        decoded_sig = base64.b64decode(signature)

        try:
            signer.verify(digest, decoded_sig)
        except ValueError as e:
            raise AgentError(VALIDATION) from e

        return json_data
