import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES
from hashids import Hashids

ALPHABET = 'abcdefghijklmnopqrstuvwxyz1234567890'
hash_ids = Hashids(min_length=32, salt='GJgCh--VgsonCWacO5-MxAuMS9hcPeGGxj5tGsT40FM', alphabet=ALPHABET)


class AESCipher(object):
    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key).digest()

    def encrypt(self, raw):
        if raw == '':
            raise TypeError('Cannot encrypt nothing')
        raw = self._pad(raw.encrypt('utf-8'))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        if enc == '':
            raise TypeError('Cannot decrypt nothing')
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        length = self.bs - (len(s) % self.bs)
        return s + bytes([length]) * length

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]


class HashSHA1:
    """
    General hashing class e.g encode/decode string with SHA1
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
