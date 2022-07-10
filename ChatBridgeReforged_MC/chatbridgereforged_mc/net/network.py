import socket as soc
import struct

from typing import TYPE_CHECKING

from chatbridgereforged_mc.net.encrypt import AESCryptor
from chatbridgereforged_mc.utils import login_formatter, msg_json_formatter, ping_formatter, stop_formatter

if TYPE_CHECKING:
    from chatbridgereforged_mc.net.tcpclient import CBRTCPClient


class NetworkBase(AESCryptor):
    def __init__(self, key, new_client: 'CBRTCPClient'):
        super().__init__(key, logger=new_client.logger)
        self.client = new_client

    def receive_msg(self, socket: soc.socket, address):
        data = socket.recv(4)
        if len(data) < 4:
            self.logger.error("Data length error")
            return '{}'
        length = struct.unpack('I', data)[0]
        msg = socket.recv(length)
        try:
            msg = self.decrypt(msg)
        except Exception:
            self.logger.bug_log(error=True)
            return '{}'
        self.logger.debug(f"Received {msg!r} from {address!r}")
        return msg

    def send_msg(self, socket: soc.socket, msg, target=''):
        if not self.client.connected:
            self.logger.debug("Not connected to the server")
            return
        if target != '':
            target = 'to ' + target
        self.logger.debug(f"Send: {msg!r} {target}")
        msg = self.encrypt(msg)
        msg = struct.pack('I', len(msg)) + msg
        try:
            socket.sendall(msg)
        except BrokenPipeError:
            self.logger.info("Connection closed from server")
            self.client.connected = False
            self.client.close_connection()


class Network(NetworkBase):
    def __init__(self, key, new_client):
        super().__init__(key, new_client)

    def send_ping(self, socket, pong=False, target=""):
        msg = ping_formatter(pong)
        self.send_msg(socket, msg, target)

    def send_login(self, socket, name, password, target=""):
        msg = login_formatter(name, password)
        self.send_msg(socket, msg, target)

    def send_stop(self, socket, target=""):
        msg = stop_formatter()
        self.send_msg(socket, msg, target)
