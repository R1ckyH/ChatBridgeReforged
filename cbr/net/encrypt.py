import hashlib
import typing
import zlib

from binascii import a2b_base64, b2a_base64
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from typing import Optional

from cbr.lib.logger import CBRLogger


class FakerCryptor:
    """Pycryptodomex has no type hint, so I have to do this
    """

    def encrypt(self, data: bytes) -> bytes:
        raise NotImplementedError

    def decrypt(self, data: bytes) -> bytes:
        raise NotImplementedError


class AESCryptor:
    """
    By ricky, most of the AESCryptor inspire from ChatBridge, thx Fallen_Breath

    [ChatBridge](https://github.com/TISUnion/ChatBridge)
    Sorry for late full credit

    Formatted codes with type hint by XiaoHuiHui
    """

    def __init__(self, key: str, logger: CBRLogger, mode: int = AES.MODE_CBC) -> None:
        self.__no_encrypt = key == ""
        self.key = hashlib.sha256(key.encode("utf-8")).digest()[:16]
        self.logger = logger
        self.mode = mode

    def get_cryptor(self) -> FakerCryptor:
        return typing.cast(
                FakerCryptor,
                AES.new(self.key, self.mode, self.key)  # type: ignore
            )

    @staticmethod
    def __to16length(text: str) -> bytes:
        b_text = text.encode("utf-8")
        return pad(b_text, 16)
        # return text + (b"\0" * ((16 - (len(text) % 16)) % 16))

    def encrypt(self, text: str) -> bytes:
        if self.__no_encrypt:
            return text.encode("utf-8")
        b_text = self.__to16length(text)
        result = self.get_cryptor().encrypt(b_text)
        return b2a_base64(zlib.compress(result, 9))

    def decrypt(self, b_text: bytes) -> str:
        if self.__no_encrypt:
            return b_text.decode("utf-8")
        b_text = zlib.decompress(a2b_base64(b_text))
        try:
            result = unpad(self.get_cryptor().decrypt(b_text), 16)
        except Exception as err:
            self.logger.error("TypeError when decrypting text")
            self.logger.error(f"Text = {b_text}")
            self.logger.error(f"Len(text) = {len(b_text)}")
            self.logger.error(err.args)
            raise err
        try:
            result = result.decode("utf-8")
        except UnicodeDecodeError:
            self.logger.error("Error at decrypt string conversion")
            self.logger.error(f"Raw result = {result}")
            result = result.decode("ISO-8859-1")
            self.logger.error(f"ISO-8859-1 = {result}")
        return result


if __name__ == "__main__":
    cryptor_test = AESCryptor("testing", CBRLogger("test"))
    print(cryptor_test.encrypt("testing"))
    # print(b2a_hex(bytes("test", "utf8")))
    print(str(cryptor_test.key, "utf8").rstrip("\0"))
    assert cryptor_test.decrypt(cryptor_test.encrypt("testing")) == "testing"
