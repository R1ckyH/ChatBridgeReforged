import json
import socket as soc
import struct
import threading
import time

from chatbridgereforged_mc.lib.config import Config
from chatbridgereforged_mc.lib.logger import CBRLogger
from chatbridgereforged_mc.net.encrypt import AESCryptor
from chatbridgereforged_mc.net.process import ClientProcess
from chatbridgereforged_mc.resources import *


class Network(AESCryptor):
    def __init__(self, key, new_client: 'CBRTCPClient'):
        super().__init__(key, logger=new_client.logger)
        self.client = new_client

    def receive_msg(self, socket: soc.socket, address):
        data = socket.recv(4)
        if len(data) < 4:
            return '{}'
        length = struct.unpack('I', data)[0]
        msg = socket.recv(length)
        msg = str(msg, encoding='utf-8')
        try:
            msg = self.decrypt(msg)
        except Exception:
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
        msg = bytes(msg, encoding='utf-8')
        msg = struct.pack('I', len(msg)) + msg
        try:
            socket.sendall(msg)
        except BrokenPipeError:
            self.logger.info("Connection closed from server")
            self.client.connected = False
            self.client.close_connection()


class CBRTCPClient(Network):
    def __init__(self, config: 'Config', logger: CBRLogger, server=None):
        self.config = config
        self.logger = logger
        self.server: PluginServerInterface = server
        self.socket = None
        self.connected = False
        self.cancelled = False
        self.connecting = False
        self.name = config.name
        super().__init__(config.aes_key, self)
        self.process = ClientProcess(self)

    def setup(self, new_config: Config):
        self.config.init_all_config()
        self.logger.load(new_config)
        super().__init__(new_config.aes_key, self)
        self.name = new_config.name
        self.connected = False
        self.cancelled = False
        self.connecting = False

    def try_start(self, info=None):
        if not self.connected and not self.connecting:
            self.connecting = True
            threading.Thread(target=self.start, name='CBR', args=(info,), daemon=True).start()
        else:
            if info is not None:
                self.logger.print_msg("Already Connected to server", 2, info, server=self.server, error=True)
            else:
                self.logger.print_msg("Already Connected to server", 0, error=True, not_spam=True)

    def start(self, info):
        self.cancelled = False
        self.logger.print_msg(f"Connecting to server with client {self.name}", 2, info, server=self.server)
        self.logger.info(f'Open connection to {self.config.host_name}:{self.config.host_port}')
        self.logger.info(f'version : {VERSION}, lib version : {LIB_VERSION}')
        self.socket = soc.socket()
        try:
            self.socket.connect((self.config.host_name, self.config.host_port))
        except Exception:
            self.logger.bug_log(error=True)
            self.connected = False
            return
        self.connected = True
        self.socket.settimeout(self.config.timeout)
        self.connecting = False
        self.handle_echo()

    def try_stop(self, info=None):
        if self.connected:
            self.close_connection()
            self.logger.print_msg("Closed connection", 2, info, server=self.server)
        else:
            self.logger.print_msg("Connection already closed", 2, info, server=self.server)

    def close_connection(self, target=''):
        if self.socket is not None and self.connected:
            self.cancelled = True
            self.send_msg(self.socket, json.dumps({'action': 'stop'}), target)
            self.socket.close()
            time.sleep(0.000001)  # for better logging priority
            self.logger.debug("Connection closed to server")
        self.connected = False

    def reload(self, info=None):
        self.logger.print_msg("Reload ChatBridgeReforged Client now", 2, info, server=self.server)
        self.close_connection()
        new_config = Config(self.logger, self.server)
        new_config.init_all_config()
        time.sleep(0.1)
        self.setup(new_config)
        self.logger.print_msg("Reload Config", 2, info, server=self.server)
        self.try_start(info)
        time.sleep(0.1)
        self.logger.print_msg(f"CBR status: Online = {self.connected}", 2, info, server=self.server)

    def keep_alive(self):
        while self.socket is not None and self.connected:
            self.logger.debug("keep alive")
            for i in range(self.config.ping_time):
                time.sleep(1)
                if not self.connected:
                    return
            ping_msg = json.dumps({"action": "keepAlive", "type": "ping"})
            if self.connected:
                self.send_msg(self.socket, ping_msg)

    def login(self, name, password):
        msg = {"action": "login", "name": name, "password": password, "lib_version": LIB_VERSION, "type": CLIENT_TYPE}
        self.send_msg(self.socket, json.dumps(msg))

    def client_process(self):
        try:
            msg = self.receive_msg(self.socket, self.config.host_name)
        except OSError as er:
            self.logger.debug("Stop Receive message")
            self.connected = False
            raise er
        msg = json.loads(msg)
        self.process.process_msg(msg, self.socket)

    def handle_echo(self):
        self.login(self.name, self.config.password)
        threading.Thread(target=self.keep_alive, name='CBRPing', daemon=True).start()
        while self.socket is not None and self.connected:
            try:
                self.client_process()
            except soc.timeout:
                self.logger.error('Connection time out!')
                self.logger.debug('Closed connection to server')
                break
            except ConnectionAbortedError:
                self.logger.info('Connection closed')
                self.logger.bug_log()
                break
            except Exception:
                self.logger.debug("Cancel Process")
                if not self.cancelled:
                    self.logger.bug_log()
                break
        self.connected = False
