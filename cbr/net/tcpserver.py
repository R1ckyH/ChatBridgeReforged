import asyncio
import json
import struct
import threading
import time
import sys

from cbr.lib.logger import CBRLogger
from cbr.net.encrypt import AESCryptor
from cbr.net.process import Process

class network(AESCryptor):
    def __init__(self, logger : CBRLogger, key):
        super().__init__(key, logger)
        self.logger = logger

    async def receive_msg(self, reader : asyncio.StreamReader, addr):
        data = await reader.read(4)
        if len(data) < 4:
            return ''
        length = struct.unpack('I', data)[0]
        msg = await reader.read(length)
        msg = str(msg, encoding='utf-8')
        msg = self.decrypt(msg)
        self.logger.debug(f"Received {msg!r} from {addr!r}")
        return msg

    async def send_msg(self, writer : asyncio.StreamWriter, msg ,target = ''):
        if target != '':
            target = 'to ' + target
        self.logger.debug(f"Send: {msg!r} {target}")
        msg = self.encrypt(msg)
        if sys.version_info.major == 3:
            msg = bytes(msg, encoding='utf-8')
        msg = struct.pack('I', len(msg)) + msg
        writer.write(msg)
        await writer.drain()


class CBRTCPServer(network):
    def __init__(self, logger : CBRLogger, config_data):
        super().__init__(logger, config_data['server_setting']['aes_key'])
        self.logger = logger
        self.config_data = config_data
        self.ip = config_data['server_setting']['ip_address']
        self.port = config_data['server_setting']['port']
        self.clients = self.setup()
        self.input_msg = None

    def start(self):
        asyncio.run(self.run())

    async def run(self):
        try:
            await self.main()
        except KeyboardInterrupt:
            await self.stop()
        exit(0)

    async def stop(self):
        self.loop_input = False
        self.logger.debug('Server closing')
        await self.close_all_connection()
        self.server.close()
        self.logger.info("Server closed")
    
    def setup(self):
        client_config = self.config_data['clients']
        client_dict = {}
        for i in range(len(client_config)):
            client_dict.update({client_config[i]['name'] : {
                'password' : client_config[i]['password'], 
                'online' : False
            }})
        return client_dict

    async def close_all_connection(self):
        for i in self.clients.keys():
            if self.clients[i]['online']:
                writer = self.clients[i]['writer']
                await self.process.close_connection(writer, i)
                self.logger.debug(f"Connection of {i} is closed")

    async def main(self):
        self.logger.info('Server starting')
        try:
            self.server = await asyncio.start_server(self.handle_echo, self.ip, self.port)
        except OSError:
            self.logger.bug(exit_now = True, error = True)
        self.addr = self.server.sockets[0].getsockname()
        self.logger.info(f'The Server is now serving on {self.addr}')
        readthread = threading.Thread(target = self.wait_for_msg, name = 'INPUT')#fuck asyncio in windows (welcome pull request to give a better solution)
        async with self.server:
            readthread.start()
            self.process = Process(self, self.logger)
            await self.input_process()
            try:
                await self.server.serve_forever()
            except RuntimeError:#fuck asyncio raise error
                return

    async def handle_echo(self, reader, writer : asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        self.logger.debug(f"new session started from {addr}")
        while not writer.is_closing():
            try:
                await asyncio.wait_for(self.server_process(reader, writer), timeout=120)
            except asyncio.TimeoutError as te:
                self.logger.error(f'Connection time out!{te}')
                self.logger.bug(exit_now = False)
                writer.close()
                self.logger.debug(f'Asyncio writer from {self.addr} closed now')
            except:
                self.logger.info(f'Connection closed from {self.process.current_client}')
                self.clients[self.process.current_client]['online'] = False
        # writer.close()

    async def server_process(self, reader, writer):
            addr = writer.get_extra_info('peername')
            msg = await self.receive_msg(reader, addr)
            msg = json.loads(msg)
            await self.process.proceess_msg(msg, reader, writer, addr)

    async def input_process(self):
        while self.server.is_serving():
            await asyncio.sleep(0.05)#tick
            if self.input_msg != None:
                try:
                    await self.process.msg_process(self.input_msg)
                except:
                    self.logger.bug(exit_now = False)
                self.input_msg = None

    def wait_for_msg(self):
        self.loop_input = True
        while True:
            if self.input_msg == None:
                try:
                    self.input_msg = input()
                except EOFError:
                    time.sleep(0.1)
                    self.logger.bug()
                    break
            if self.loop_input == False:
                break

if __name__ == '__main__':
    ip = '192.168.1.19'
    port = '7777'
    server = CBRTCPServer({'server_setting':{'ip_address' : ip, 'port': port, 'aes_key': 'asdasd'}})
    server.start()