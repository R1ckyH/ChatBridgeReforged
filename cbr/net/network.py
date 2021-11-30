import json
import struct
import trio

from cbr.lib.logger import CBRLogger
from cbr.net.encrypt import AESCryptor
from cbr.resources import formatter


class NetworkBase(AESCryptor):
    def __init__(self, logger: CBRLogger, key, clients):
        super().__init__(key, logger)
        self.logger = logger
        self.clients = clients

    async def receive_msg(self, stream: trio.SocketStream, address):
        data = await stream.receive_some(4)
        if len(data) < 4:
            self.logger.error(f"Data length error, Data = {data}")
            return '{}'
        length = struct.unpack('I', data)[0]
        msg = await stream.receive_some(length)
        try:
            msg = str(msg, encoding='utf-8')
            msg = self.decrypt(msg)
        except Exception:
            self.logger.bug(error=False)
            return '{}'
        self.logger.debug(f"Received {msg!r} from {address!r}", "CBR")
        return msg

    async def send_msg(self, stream: trio.SocketStream, msg, target=''):
        if target == '':
            lock = trio.Lock()
        else:
            lock = self.clients[target].send_lock
            target = 'to ' + target
        self.logger.debug(f"Send: {msg!r} {target}", "CBR")
        msg = self.encrypt(msg)
        msg = bytes(msg, encoding='utf-8')
        msg = struct.pack('I', len(msg)) + msg
        async with lock:
            await stream.send_all(msg)


class Network(NetworkBase):
    def __init__(self, logger: CBRLogger, key, clients):
        super().__init__(logger, key, clients)
        self.formatter = formatter

    async def send_ping(self, stream: trio.SocketStream, pong=False, target=''):
        msg = self.formatter.ping_formatter(pong)
        await self.send_msg(stream, msg, target)

    async def send_login_result(self, stream: trio.SocketStream, success=True, target=''):
        msg = self.formatter.login_formatter(success)
        await self.send_msg(stream, msg, target)

    async def send_command(self, stream: trio.SocketStream, cmd, target_client):
        msg = self.formatter.command_formatter(cmd, target_client)
        await self.send_msg(stream, msg, target_client)

    async def send_message(self, stream: trio.SocketStream, client, player, message, receiver='', target=''):
        msg = self.formatter.message_formatter(client, player, message, receiver)
        await self.send_msg(stream, msg, target)

    async def send_api(self, stream: trio.SocketStream, receiver, plugin_id, function_name, keys: dict, target=''):
        msg = self.formatter.api_formatter(receiver, plugin_id, function_name, keys)
        await self.send_msg(stream, msg, target)

    async def send_stop(self, stream: trio.SocketStream, target=''):
        message = {
            "action": "stop"
        }
        msg = json.dumps(message)
        await self.send_msg(stream, msg, target)
