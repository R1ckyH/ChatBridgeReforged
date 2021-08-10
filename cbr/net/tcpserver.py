import json
import os
import struct
import trio

from cbr.lib.logger import CBRLogger
from cbr.net.encrypt import AESCryptor
from cbr.net.process import ServerProcess, ClientProcess
from cbr.plugin.plugin import PluginManager
from cbr.plugin.serverinterface import ServerInterface


class Network(AESCryptor):
    def __init__(self, logger: CBRLogger, key, clients):
        super().__init__(key, logger)
        self.logger = logger
        self.clients = clients

    async def receive_msg(self, stream: trio.SocketStream, address):
        data = await stream.receive_some(4)
        if len(data) < 4:
            return None
        length = struct.unpack('I', data)[0]
        msg = await stream.receive_some(length)
        msg = str(msg, encoding='utf-8')
        try:
            msg = self.decrypt(msg)
        except Exception:
            self.logger.bug(exit_now=False)
            return '{}'
        self.logger.debug(f"Received {msg!r} from {address!r}")
        return msg

    async def send_msg(self, stream: trio.SocketStream, msg, target=''):
        if target == '':
            lock = trio.Lock()
        else:
            lock = self.clients[target]['sendlock']
            target = 'to ' + target
        self.logger.debug(f"Send: {msg!r} {target}")
        msg = self.encrypt(msg)
        msg = bytes(msg, encoding='utf-8')
        msg = struct.pack('I', len(msg)) + msg
        async with lock:
            await stream.send_all(msg)


class CBRTCPServer(Network):
    def __init__(self, logger: CBRLogger, config_data):
        self.logger = logger
        self.config_data = config_data
        self.libversion = config_data['libversion']
        self.ip = config_data['server_setting']['ip_address']
        self.port = config_data['server_setting']['port']
        self.nursery = None
        self.clients = self.setup_client()
        super().__init__(logger, config_data['server_setting']['aes_key'], self.clients)
        self.server_interface = ServerInterface(self)
        self.plugin_manager = PluginManager(self.server_interface, self.logger)
        self.process = ServerProcess(self, self.logger)

    def start(self):
        trio.run(self.run)

    async def run(self):
        await self.main()

    async def start_server(self):
        try:
            await trio.serve_tcp(self.handle_echo, self.port, host=self.ip)
        except OSError:
            self.logger.bug(exit_now=True, error=True)

    async def stop(self):
        self.logger.debug('Server closing')
        await self.close_all_connection()
        self.logger.info("Server closed")
        self.nursery.cancel_scope.cancel()
        self.process.cancelled = True

    def setup_client(self):
        client_config = self.config_data['clients']
        client_dict = {}
        for i in range(len(client_config)):
            client_dict.update({
                client_config[i]['name']: {
                    'password': client_config[i]['password'],
                    'online': False,
                    'type': False,
                    'stream': None,
                    'sendlock': trio.Lock(),
                    'ping': None,
                    'pinglock': None,
                    'cmdlock': trio.CancelScope(),
                    'cmdresult': None
                }
            })
        return client_dict

    async def close_all_connection(self):
        for i in self.clients.keys():
            if self.clients[i]['online']:
                stream = self.clients[i]['stream']
                await self.process.close_connection(stream, i)
                self.logger.info(f"Closed connection to {i}")

    async def main(self):
        self.logger.info(f'Server starting at pid {os.getpid()}')
        try:
            async with trio.open_nursery() as self.nursery:
                self.nursery.start_soon(self.start_server)
                self.logger.info(f'The Server is now serving on {self.ip}:{self.port}')
                self.nursery.start_soon(trio.to_thread.run_sync, self.input_process)
                self.nursery.start_soon(self.plugin_manager.reload_all_plugins)
        except KeyboardInterrupt:
            await self.stop()

    def register_process(self, process: ClientProcess, client_name):
        self.clients[client_name]['process'] = process

    async def handle_echo(self, stream: trio.SocketStream):
        address = stream.socket.getpeername()
        self.logger.debug(f"new session started from {address}")
        client_process = ClientProcess(self, self.logger)
        async with trio.open_nursery() as nursery:
            while not client_process.cancelled:
                try:
                    with trio.fail_after(120) as client_process.cancel_scope:
                        await self.server_process(stream, client_process, address, nursery)
                except trio.TooSlowError:
                    if not client_process.cancelled:
                        self.logger.error('Connection time out!')
                    else:
                        self.logger.debug("Cancel Process")
                    break
                except trio.BrokenResourceError:
                    self.logger.debug("Process broken")
                    break
                except trio.ClosedResourceError:
                    self.logger.debug("Process Closed")
                except trio.Cancelled:
                    self.logger.debug(f"Cancel Process to {client_process.current_client}")
                    break
                except Exception:
                    self.logger.bug(exit_now=False, error=True)
                    break
            client_process.cancelled = True
            if client_process.current_client != '':
                self.logger.info(f'Closed Process to {client_process.current_client}')
                self.clients[client_process.current_client]['online'] = False

    async def server_process(self, stream: trio.SocketStream, client_process: ClientProcess, address, nursery):
        msg = await self.receive_msg(stream, address)
        msg = json.loads(msg)
        await client_process.process_msg(msg, stream, address, nursery)

    def input_process(self):
        while not self.process.cancelled:
            try:
                msg = input()
            except EOFError:
                return
            try:
                trio.from_thread.run(self.process.msg_process, msg, self.nursery)
            except Exception:
                self.logger.bug(exit_now=False, error=True)
