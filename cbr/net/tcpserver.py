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
        self.logger.debug(f"Send: {msg + target!r}")
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
        self.client_name = []
        self.client_list = {}
        self.input_msg = None

    def start(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.stop()
        exit(0)

    def stop(self):
        self.loop_input = False
        self.logger.debug('Server closing')
        #self.close_all_connection()
        #self.shutdown()
        self.server.close()
        self.logger.info("Server closed")
    
    def shutdown(self):
        for task in asyncio.Task.all_tasks():
            task.cancel()

    def close_all_connection(self):
        print(self.client_name)
        for i in range(len(self.client_name)):
            writer = self.client_list[self.client_name[i]]['writer']
            print(writer.is_closing())
            if not writer.is_closing():
                writer.close()
            self.logger.debug(f"{self.client_name[i]} is closed")

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
            await self.msg_to_all()
            await self.server.serve_forever()

    async def handle_echo(self, reader, writer : asyncio.StreamWriter):
        process = Process(self, self.logger)
        addr = writer.get_extra_info('peername')
        self.logger.debug(f"new session started from {addr}")
        while not writer.is_closing():
            try:
                await asyncio.wait_for(self.server_process(reader, writer, process), timeout=120)
            except asyncio.TimeoutError as te:
                self.logger.error(f'Connection time out!{te}')
                self.logger.bug(exit_now = False)
                writer.close()
                self.logger.debug(f'Asyncio writer from {self.addr} closed now')
            except:
                self.logger.info(f'Connection closed from {process.current_client}')
        # writer.close()

    async def server_process(self, reader, writer, process : Process):
            addr = writer.get_extra_info('peername')
            msg = await self.receive_msg(reader, addr)
            msg = json.loads(msg)
            await process.proceess_msg(msg, reader, writer, addr)
    
    async def server_msg(self, msg):
        message = {"action": "message",
            "client": "CBR",
            "player": "",
            "message": f"{msg}"
        }
        for i in range(len(self.client_name)):
            self.logger.debug(self.client_name[i])
            writer = self.client_list[self.client_name[i]]['writer']
            await self.send_msg(writer, str(json.dumps(message)))

    async def msg_to_all(self):
        while True:
            await asyncio.sleep(0.05)#tick
            if self.loop_input == False:
                break
            if self.input_msg != None:
                await self.server_msg(self.input_msg)
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