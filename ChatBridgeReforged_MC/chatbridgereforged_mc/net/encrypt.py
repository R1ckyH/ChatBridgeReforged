import hashlib
import zlib

from binascii import b2a_base64, a2b_base64
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad

from chatbridgereforged_mc.lib.logger import CBRLogger


class AESCryptor:
    """
    By ricky, most of the AESCryptor inspire from ChatBridge, thx Fallen_Breath

    [ChatBridge](https://github.com/TISUnion/ChatBridge) Sorry for late full credit
    """
    def __init__(self, key: str, logger: 'CBRLogger', mode=AES.MODE_CBC):
        self.__no_encrypt = key == ''
        self.key = hashlib.sha256(key.encode("utf-8")).digest()[:16]
        self.logger = logger
        self.mode = mode

    def get_cryptor(self):
        return AES.new(self.key, self.mode, self.key)

    @staticmethod
    def __to16length(text: str):
        text = bytes(text, encoding="utf-8")
        return pad(text, 16)

    def encrypt(self, text):
        if self.__no_encrypt:
            return text.encode("utf-8")
        text = self.__to16length(text)
        result = self.get_cryptor().encrypt(text)
        return b2a_base64(zlib.compress(result, 9))

    def decrypt(self, text):
        if self.__no_encrypt:
            return text
        text = zlib.decompress(a2b_base64(text))
        try:
            result = unpad(self.get_cryptor().decrypt(text), 16)
        except Exception as err:
            self.logger.error('TypeError when decrypting text')
            self.logger.error('Text =' + str(text))
            self.logger.error('Len(text) =' + str(len(text)))
            self.logger.error(str(err.args))
            raise err
        try:
            result = str(result, encoding='utf-8')
        except UnicodeDecodeError:
            self.logger.error('Error at decrypt string conversion')
            self.logger.error('Raw result = ' + str(result))
            result = str(result, encoding='ISO-8859-1')
            self.logger.error('ISO-8859-1 = ' + str(result))
        return result
