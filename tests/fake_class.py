from cbr.lib.client import Client
from cbr.lib.typeddicts import TypedServerConfig


class FakeClientConfig:
    def __init__(self, key):
        self.aes_key = key
        self.name = "test"
        self.password = "password"
        self.timeout = 120
        self.auto_restart = False
        self.react_group = "00000000"
        self.host_name = "0.0.0.0"


class FakeStreamSocket:
    def __init__(self, name):
        self.name = name
        self.msg = ""
        self.stop = False

    def __str__(self):
        return self.msg

    def sendall(self, msg):
        self.msg = msg

    async def send_all(self, msg):
        self.sendall(msg)

    def recv(self, length=None):
        msg = self.msg[:length]
        self.msg = self.msg[length:]
        return msg

    async def receive_some(self, length=None):
        return self.recv(length)

    async def aclose(self):
        self.stop = True

    def close(self):
        return
        # self.stop == True


class Fake_guardian:
    def __init__(self):
        self.end = False

    def stop(self):
        self.end = True
