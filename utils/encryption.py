import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES

from cryptography.fernet import Fernet

from django.conf import settings


class AESCipher(object):
    """
    this class is used for encryption and decryption based on AES
    :attr length: length of AES block size
    :attr key: a key for encryption and decryption operations
    """

    def __init__(self, key):
        self.length = 16
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        """
        this method get a raw string and encrypt it with AES CBC mode
        :param raw: a string that we want to encrypt
        :return: a encrypted string
        """
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)  # AES block_size is 16
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        """
        this method get a encoded string and decode it
        :param enc: a string that encoded with AES CBC mode
        :return: a decoded string
        """
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, text):
        """
        add padding to a text
        in this state we add a padding to a incoming text, padding character is a hex character of padding length
        :param text: a string that we want to add padding to end of it
        :return: the incoming string that contains padding
        """
        return text + (self.length - len(text) % self.length) * chr(self.length - len(text) % self.length)

    @staticmethod
    def _unpad(text):
        """
        remove padding for text
        :param text: a string that we want to remove padding from end of it
        :return: the incoming string that removed padding
        """
        return text[:-ord(text[len(text) - 1:])]
