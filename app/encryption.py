import base64
import hashlib
import json
from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from Crypto import Random
from Crypto.Cipher import AES
from hashids import Hashids
from tenacity import retry, stop_after_attempt, wait_exponential

import settings

ALPHABET = "abcdefghijklmnopqrstuvwxyz1234567890"
hash_ids = Hashids(min_length=32, salt="GJgCh--VgsonCWacO5-MxAuMS9hcPeGGxj5tGsT40FM", alphabet=ALPHABET)


class AESCipher(object):
    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key).digest()

    def encrypt(self, raw):
        if raw == "":
            raise TypeError("Cannot encrypt nothing")
        raw = self._pad(raw.encode("utf-8"))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        if enc == "":
            raise TypeError("Cannot decrypt nothing")
        enc = base64.b64decode(enc)
        iv = enc[: AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size :])).decode("utf-8")

    def _pad(self, s):
        length = self.bs - (len(s) % self.bs)
        return s + bytes([length]) * length

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1 :])]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=3, max=12),
    reraise=True,
)
@lru_cache(128)
def get_aes_key(secret_name):
    client = connect_to_vault()
    vault_aes_keys = client.get_secret(secret_name).value
    aes_key = json.loads(vault_aes_keys)["AES_KEY"]
    return aes_key.encode()


def connect_to_vault():
    return SecretClient(vault_url=settings.VAULT_URL, credential=DefaultAzureCredential())


class HashSHA1:
    """
    SHA1 hashing class e.g encode/decode string
    """

    @staticmethod
    def encrypt(input: str) -> str:
        """
        :param input: string to be encoded as SHA1
        :return: encoded string
        """
        h = hashlib.sha1()
        h.update(input.encode("utf-8"))
        encoded_str = h.hexdigest()

        return encoded_str
