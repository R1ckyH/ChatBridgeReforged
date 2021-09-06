from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES

from chatbridgereforged_mc.lib.logger import CBRLogger


class AESCryptor:
    """
    By ricky, most of the AESCryptor copied from ChatBridge cause I dose not want to change this part

    [ChatBridge](https://github.com/TISUnion/ChatBridge) Sorry for late full credit
    """
    def __init__(self, key, mode=AES.MODE_CBC, logger: CBRLogger = None):
        self.key = self.__to16length(key)
        self.mode = mode
        self.logger = logger

    def __to16length(self, text):
        text = bytes(text, encoding="utf-8")
        return text + (b'\0' * ((16 - (len(text) % 16)) % 16))

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        text = self.__to16length(text)
        result = b2a_hex(cryptor.encrypt(text))
        result = str(result, encoding='utf-8')
        return result

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        text = bytes(text, encoding='utf-8')
        try:
            result = cryptor.decrypt(a2b_hex(text))
        except TypeError as err:
            self.logger.error('TypeError when decrypting text')
            self.logger.error('text =' + str(text))
            raise err
        except ValueError as err:
            self.logger.error(str(err.args))
            self.logger.error('len(text) =' + str(len(text)))
            raise err
        try:
            result = str(result, encoding='utf-8')
        except UnicodeDecodeError:
            self.logger.error('error at decrypt string conversion')
            self.logger.error('raw result = ' + str(result))
            result = str(result, encoding='ISO-8859-1')
            self.logger.error('ISO-8859-1 = ' + str(result))
        return result.rstrip('\0')
