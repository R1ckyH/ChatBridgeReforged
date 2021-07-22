import json
import os
import struct
import trio
import sys

from cbr.lib.logger import CBRLogger
from cbr.net.encrypt import AESCryptor
from cbr.net.process import ServerProcess, ClientProcess

class network(AESCryptor):
    def __init__(self, logger : CBRLogger, key):
        super().__init__(key, logger)
        self.logger = logger

    async def receive_msg(self, stream : trio.SocketStream, addr):
        data = await stream.receive_some(4)
        if len(data) < 4:
            return '{}'
        length = struct.unpack('I', data)[0]
        msg = await stream.receive_some(length)
        msg = str(msg, encoding='utf-8')
        try:
            msg = self.decrypt(msg)
        except:
            self.logger.bug(exit_now=False)
            return '{}'
        self.logger.debug(f"Received {msg!r} from {addr!r}")
        return msg

    async def send_msg(self, stream : trio.SocketStream, msg ,target = ''):
        if target != '':
            target = 'to ' + target
        self.logger.debug(f"Send: {msg!r} {target}")
        msg = self.encrypt(msg)
        if sys.version_info.major == 3:
            msg = bytes(msg, encoding='utf-8')
        msg = struct.pack('I', len(msg)) + msg
        await stream.send_all(msg)
        await stream.wait_send_all_might_not_block()


class CBRTCPServer(network):
    def __init__(self, logger : CBRLogger, config_data):
        super().__init__(logger, config_data['server_setting']['aes_key'])
        self.logger = logger
        self.config_data = config_data
        self.ip = config_data['server_setting']['ip_address']
        self.port = config_data['server_setting']['port']
        self.clients = self.setup()

    def start(self):
        trio.run(self.run)

    async def run(self):
        await self.main()

    async def start_server(self):
        try:
            await trio.serve_tcp(self.handle_echo, self.port, host= self.ip)
        except OSError:
            self.logger.bug(exit_now = True, error = True)
    
    async def stop(self):
        self.logger.debug('Server closing')
        await self.close_all_connection()
        self.logger.info("Server closed")
        self.nusery.cancel_scope.cancel()
        self.process.cancelled = True

    def setup(self):
        client_config = self.config_data['clients']
        client_dict = {}
        for i in range(len(client_config)):
            client_dict.update({
                client_config[i]['name'] : {
                    'password' : client_config[i]['password'], 
                    'online' : False,
                    'stream' : None,
                    'ping' : None,
                    'pinglock' : None
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
        self.process = ServerProcess(self, self.logger)
        try:
            async with trio.open_nursery() as self.nusery:
                self.nusery.start_soon(self.start_server)
                self.logger.info(f'The Server is now serving on {self.ip}')
                self.nusery.start_soon(trio.to_thread.run_sync, self.input_process)
        except KeyboardInterrupt:
            await self.stop()

    def register_process(self, process : ClientProcess, client_name):
        self.clients[client_name]['process'] = process

    async def handle_echo(self, stream :trio.SocketStream):
        addr = stream.socket.getpeername()
        self.logger.debug(f"new session started from {addr}")
        client_process = ClientProcess(self, self.logger)
        while client_process.cancelled == False:
            try:
                with trio.fail_after(120) as client_process.cancel_scope:
                    await self.server_process(stream, client_process, addr)
            except trio.TooSlowError:
                if not client_process.cancelled:
                    self.logger.error('Connection time out!')
                else:
                    self.logger.debug("Cancel Process")
                break
            except trio.BrokenResourceError and trio.ClosedResourceError:
                print(1)
                self.logger.debug("Process broken")
                break
            except trio.Cancelled:
                self.logger.debug(f"Cancel Process to {client_process.current_client}")
                break
            except:
                print(1)
                self.logger.bug(exit_now = False)
                break
        client_process.cancelled = True
        if client_process.current_client != '':
            self.logger.info(f'Closed Process to {client_process.current_client}')
            self.clients[client_process.current_client]['online'] = False

    async def server_process(self, stream : trio.SocketStream, client_process : ClientProcess, addr ):
        msg = await self.receive_msg(stream, addr)
        msg = json.loads(msg)
        await client_process.process_msg(msg, stream, addr)

    def input_process(self):
        while not self.process.cancelled:
            try:
                msg = input()
            except EOFError:
                return
            try:
                trio.from_thread.run(self.process.msg_process, msg)
            except:
                self.logger.bug(exit_now = False)

if __name__ == '__main__':
    ip = '192.168.1.19'
    port = '7777'
    server = CBRTCPServer({'server_setting':{'ip_address' : ip, 'port': port, 'aes_key': 'asdasd'}})
    server.start()