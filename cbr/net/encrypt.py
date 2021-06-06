import logging
import sys

from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES
from cbr.lib.logger import CBRLogger

class AESCryptor():
	# key and text needs to be utf-8 str in python2 or str in python3
    # by ricky, most of the code keep cause me dose not want to change this part
    def __init__(self, key, logger : CBRLogger, mode=AES.MODE_CBC):
        self.key = self.__to16Length(key)
        self.logger = logger
        self.mode = mode

    def __to16Length(self, text):
        if sys.version_info.major == 3:
            text = bytes(text, encoding="utf-8")
        return text + (b'\0' * ((16 - (len(text) % 16)) % 16))

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        text = self.__to16Length(text)
        result = b2a_hex(cryptor.encrypt(text))
        if sys.version_info.major == 3:
            result = str(result, encoding='utf-8')
        return result

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        if sys.version_info.major == 3:
            text = bytes(text, encoding='utf-8')
        try:
            result = cryptor.decrypt(a2b_hex(text))
        except TypeError as err:
            self.logger.error('TypeError when decrypting text')
            self.logger.error('text =', text)
            raise err
        except ValueError as err:
            self.logger.error(err.args)
            self.logger.error('len(text) =' + str(len(text)))
            raise err
        if sys.version_info.major == 3:
            try:
                result = str(result, encoding='utf-8')
            except UnicodeDecodeError:
                self.logger.error('error at decrypt string conversion')
                self.logger.error('raw result = ' + str(result))
                result = str(result, encoding='ISO-8859-1')
                self.logger.error('ISO-8859-1 = ' + str(result))
        return result.rstrip('\0')
