import json
import unittest

from app.encryption import AESCipher
from app.utils import generate_random_key


class TestEncryption(unittest.TestCase):
    def setUp(self):
        self.key = generate_random_key(32)

    def test_encrypt_decrypt(self):
        message = 'Message To Encrypt'
        aes_cipher = AESCipher(key=self.key)
        cipher_text = aes_cipher.encrypt(message)
        aes_cipher2 = AESCipher(key=self.key)
        decrypted_message = aes_cipher2.decrypt(cipher_text)
        self.assertEqual(message, decrypted_message)

    def test_encrypt_decrypt_dictionary(self):
        login_credentials = {'username': 'test'}
        message = json.dumps(login_credentials)
        aes_cipher = AESCipher(key=self.key)
        cipher_text = aes_cipher.encrypt(message)
        aes_cipher2 = AESCipher(key=self.key)
        decrypted_message = aes_cipher2.decrypt(cipher_text)
        self.assertEqual(message, decrypted_message)
        decrypted_credentials = json.loads(decrypted_message)
        self.assertEqual(login_credentials, decrypted_credentials)

    def test_do_not_allow_encryption_of_none(self):
        aes_cipher = AESCipher(key=self.key)
        self.assertRaises(TypeError, aes_cipher.encrypt, '')

    def test_do_not_allow_decryption_of_none(self):
        aes_cipher = AESCipher(key=self.key)
        cipher_text = aes_cipher.encrypt('blah')
        self.assertRaises(TypeError, aes_cipher.decrypt, '')


if __name__ == '__main__':
    unittest.main()
