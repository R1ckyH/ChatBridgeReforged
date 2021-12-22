from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES

from cbr.lib.logger import CBRLogger


class AESCryptor:
    """
    By ricky, most of the AESCryptor copied from ChatBridge because I does not want to change this part

    [ChatBridge](https://github.com/TISUnion/ChatBridge) Sorry for late full credit
    """
    def __init__(self, key, logger: CBRLogger, mode=AES.MODE_CBC):  # TODO: EDIT encrypt to fuck more gpl(now)
        self.key = self.__to16length(key)
        self.logger = logger
        self.mode = mode

    def get_cryptor(self):
        return AES.new(self.key, self.mode, self.key)

    def __to16length(self, text):
        text = bytes(text, encoding="utf-8")
        return text + (b'\0' * ((16 - (len(text) % 16)) % 16))

    def encrypt(self, text):
        text = self.__to16length(text)
        result = b2a_hex(self.get_cryptor().encrypt(text))
        result = str(result, encoding='utf-8')
        return result

    def decrypt(self, text):
        text = bytes(text, encoding='utf-8')
        try:
            result = self.get_cryptor().decrypt(a2b_hex(text))
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
        return result.rstrip('\0')


if __name__ == '__main__':
    cryptor_test = AESCryptor("testing", CBRLogger("test"))
    print(cryptor_test.encrypt("testing"))
    print(b2a_hex(bytes("test", 'utf8')))
    print(str(cryptor_test.key, "utf8").rstrip('\0'))
