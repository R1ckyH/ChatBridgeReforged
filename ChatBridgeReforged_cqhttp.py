import json
import os
import socket as soc
import struct
import threading
import time
import traceback
import websocket

from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES
from datetime import datetime

from mcdreforged.api.all import *

PREFIX = '!!CBR'
PREFIX2 = '!!cbr'
LIB_VERSION = "v20210820"
CLIENT_TYPE = "cqhttp"
client: 'CBRTCPClient'
CQ_bot: 'CQClient'

debug_mode = False
CONFIG_PATH = 'config/ChatBridgeReforged_cqhttp.json'
LOG_PATH = 'logs/ChatBridgeReforged_cqhttp.log'
ping_time = 60
timeout = 120

PLUGIN_METADATA = {
    'id': 'chatbridgereforged_cqhttp',
    'version': '0.0.1-Beta-014',
    'name': 'ChatBridgeReforged_cqhttp',
    'description': 'Reforged of ChatBridge, Client for cqhttp.',
    'author': 'ricky',
    'link': 'https://github.com/rickyhoho/ChatBridgeReforged'
}

DEFAULT_CONFIG = {
    "name": "cqhttp",
    "password": "cqhttp",
    "host_name": "127.0.0.1",
    "host_port": 30001,
    "aes_key": "ThisIsTheSecret",
    "ws_address": "127.0.0.1",  # not same with host_name
    "ws_port": "6700",
    "ws_access_token": "my_access_token",
    "react_group": "1101314858"
}


def rtext_cmd(txt, msg, cmd):
    return RText(txt).h(msg).c(RAction.run_command, cmd)


def help_formatter(mcdr_prefix, command, first_msg, click_msg, use_command=None):
    if use_command is None:
        use_command = command
    msg = f'{mcdr_prefix} {command} {first_msg}'
    return rtext_cmd(msg, f'Click me to {click_msg}', f'{mcdr_prefix} {use_command}')


def message_formatter(client_name, player, msg):
    if player != "":
        message = f"[{client_name}] <{player}> {msg}"  # chat message
    else:
        message = f"[{client_name}] {msg}"
    return message


def msg_json_formatter(client_name, player, msg):
    message = {
        "action": "message",
        "client": client_name,
        "player": player,
        "message": msg
    }
    return json.dumps(message)


def qq_msg_formatter(text, group_id):
    data = {
        "action": "send_group_msg",
        "params": {
            "group_id": group_id,
            "message": text
        }
    }
    return json.dumps(data)


help_msg = '''§b-----------§fChatBridgeReforged_Client§b-----------§r
''' + help_formatter(PREFIX, 'help', 'show help message§r', 'show help message') + '''
''' + help_formatter(PREFIX, 'start', 'start ChatBridgeReforged client§r', 'start') + '''
''' + help_formatter(PREFIX, 'stop', 'stop ChatBridgeReforged client§r', 'stop') + '''
''' + help_formatter(PREFIX, 'status', 'show status of ChatBridgeReforged client§r', 'show status') + '''
''' + help_formatter(PREFIX, 'reload', 'reload ChatBridgeReforged client§r', 'reload') + '''
''' + help_formatter(PREFIX, 'restart', 'restart ChatBridgeReforged client§r', 'restart') + '''
''' + help_formatter(PREFIX, 'ping', 'ping ChatBridgeReforged server§r', 'ping') + '''
§b-----------------------------------------------§r'''


class CBRLogger:
    def __init__(self):
        self._debug_mode = False
        self.log_path = ''
        self.client = None

    def load(self, client_class=None):
        self.client: CBRTCPClient = client_class
        self._debug_mode = debug_mode
        self.log_path = LOG_PATH

    def info(self, msg):
        self.out_log(msg)

    def error(self, msg):
        self.out_log(msg, error=True)

    def debug(self, msg):
        self.out_log(msg, debug=True)

    def out_log(self, msg: str, error=False, debug=False, not_spam=False):
        for i in range(6):
            msg = msg.replace('§' + str(i), '').replace('§' + chr(97 + i), '')
        msg = msg.replace('§6', '').replace('§7', '').replace('§8', '').replace('§9', '')
        heading = '[CBR] ' + datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        if error:
            msg = heading + '[ERROR]: ' + msg
        elif debug:
            if not self._debug_mode:
                return
            msg = heading + '[DEBUG]: ' + msg
        else:
            msg = heading + '[INFO]: ' + msg
        if not not_spam:
            print(msg + '\n', end='')
            if self.log_path != '':
                with open(LOG_PATH, 'a+', encoding='utf-8') as log:
                    log.write(msg + '\n')

    def bug_log(self, error=False):
        self.error('bug exist')
        for line in traceback.format_exc().splitlines():
            if error is True:
                self.error(line)
            else:
                self.debug(line)

    def print_msg(self, msg, num, error=False, debug=False, not_spam=False):
        if num == 0:
            self.out_log(str(msg), not_spam=not_spam)
        elif num == 1:
            self.info(str(msg))
        elif num == 2:
            self.out_log(msg, error, debug)

    def force_debug(self):
        self._debug_mode = not self._debug_mode
        self.print_msg(f'force debug: {self._debug_mode}', 2)


class Config:
    def __init__(self, logger: CBRLogger):
        self.logger = logger
        self.name = DEFAULT_CONFIG['name']
        self.password = DEFAULT_CONFIG['password']
        self.host_name = DEFAULT_CONFIG['host_name']
        self.host_port = DEFAULT_CONFIG['host_port']
        self.aes_key = DEFAULT_CONFIG['aes_key']
        self.ws_address = "127.0.0.1"  # not same with host_name
        self.ws_port = 6700
        self.ws_access_token = "my_access_token"
        self.ws_url = f"ws://{self.ws_address}:{self.ws_port}/?access_token={self.ws_access_token}"
        self.react_group = ''

    def check_log_file(self):
        if not os.path.exists(LOG_PATH):
            os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
            self.logger.error('Log file not find')
            self.logger.info('Generate new log file')

    def load_config(self):
        sync = False
        self.check_log_file()
        if not os.path.exists(CONFIG_PATH):
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            self.logger.error('Config not find')
            self.logger.info('Generate default config')
            with open(CONFIG_PATH, 'w', encoding='utf-8') as config_file:
                json.dump(DEFAULT_CONFIG, config_file, indent=4)
            return DEFAULT_CONFIG
        with open(CONFIG_PATH, 'r', encoding='utf-8') as config_file:
            data = dict(json.load(config_file))
        for keys in DEFAULT_CONFIG.keys():
            if keys not in data.keys():
                self.logger.error(f"Config {keys} not found, use default value {DEFAULT_CONFIG[keys]}")
                data.update({keys: DEFAULT_CONFIG[keys]})
                sync = True
        if sync:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as config_file:
                json.dump(data, config_file, indent=4)
        return data

    def init_config(self):
        config_dict = self.load_config()
        self.name = config_dict['name']
        self.password = config_dict['password']
        self.host_name = config_dict['host_name']
        self.host_port = config_dict['host_port']
        self.aes_key = config_dict['aes_key']
        self.ws_address = config_dict['ws_address']  # not same with host_name
        self.ws_port = config_dict['ws_port']
        self.ws_access_token = config_dict['ws_access_token']
        self.ws_url = f"ws://{self.ws_address}:{self.ws_port}/?access_token={self.ws_access_token}"
        self.react_group = config_dict['react_group']

    def init_all_config(self):
        self.init_config()


class CQClient(websocket.WebSocketApp):
    def __init__(self, config: Config, logger: CBRLogger, client_class: 'CBRTCPClient'):
        super().__init__(config.ws_url, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.client = client_class
        self.logger = logger
        self.config = config

    def start(self):
        while True:
            self.run_forever()

    def on_message(self, client_class, message):
        if not self.client.connected:
            return
        data = json.loads(message)
        if 'status' in data:
            self.logger.debug('CQBot return status {}'.format(data['status']))
        elif data['post_type'] == 'message' and data['message_type'] == 'group':
            if str(data['group_id']) == self.config.react_group and data['anonymous'] is None:
                msg = msg_json_formatter(self.client.name, data['sender']['nickname'], data['raw_message'])
                message = message_formatter(self.client.name, data['sender']['nickname'], data['raw_message'])
                self.logger.info(message)
                self.client.send_msg(self.client.socket, msg)

    def on_error(self, client_class, error2=None):
        self.logger.error(str(error2))
        self.logger.bug_log()

    def on_close(self, client_class, close_code, close_msg):
        self.logger.info(f"Close connection with code : {close_code}")
        self.logger.info(f"Close message : {close_msg}")

    def send_text(self, text, group_id):  # copy from [ChatBridge](https://github.com/TISUnion/ChatBridge)
        msg = ''
        length = 0
        lines = text.rstrip().splitlines(keepends=True)
        for i in range(len(lines)):
            msg += lines[i]
            length += len(lines[i])
            if i == len(lines) - 1 or length + len(lines[i + 1]) > 500:
                message = qq_msg_formatter(msg, group_id)
                self.logger.debug(f"Send: {message} to cq")
                self.send(message)
                msg = ''
                length = 0


class AESCryptor:
    """
    By ricky, most of the AESCryptor copied from ChatBridge cause I dose not want to change this part

    [ChatBridge](https://github.com/TISUnion/ChatBridge) Sorry for late full credit
    """
    def __init__(self, key, mode=AES.MODE_CBC, logger: CBRLogger = None):
        self.key = self.__to16length(key)
        self.mode = mode
        self.logger = logger

    def __to16length(self, text):
        text = bytes(text, encoding="utf-8")
        return text + (b'\0' * ((16 - (len(text) % 16)) % 16))

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        text = self.__to16length(text)
        result = b2a_hex(cryptor.encrypt(text))
        result = str(result, encoding='utf-8')
        return result

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        text = bytes(text, encoding='utf-8')
        try:
            result = cryptor.decrypt(a2b_hex(text))
        except TypeError as err:
            self.logger.error('TypeError when decrypting text')
            self.logger.error('text =' + str(text))
            raise err
        except ValueError as err:
            self.logger.error(str(err.args))
            self.logger.error('len(text) =' + str(len(text)))
            raise err
        try:
            result = str(result, encoding='utf-8')
        except UnicodeDecodeError:
            self.logger.error('error at decrypt string conversion')
            self.logger.error('raw result = ' + str(result))
            result = str(result, encoding='ISO-8859-1')
            self.logger.error('ISO-8859-1 = ' + str(result))
        return result.rstrip('\0')


class ClientProcess:
    def __init__(self, client_class: 'CBRTCPClient'):
        self.client = client_class
        self.logger = client_class.logger
        self.end = 0

    def ping_test(self):
        if not self.client.connected:
            return -2
        self.logger.debug(f'Ping to server')
        start_time = time.time()
        self.client.send_msg(self.client.socket, '{"action": "keepAlive", "type": "ping"}', 'server')
        self.ping_result()
        self.logger.debug(f'get ping result from server')
        if self.end == -1:
            self.logger.debug(f'No response from server')
            return -1
        return round((self.end - start_time) * 1000, 1)

    def ping_result(self):
        self.end = 0
        start = time.time()
        while time.time() - start <= 2:
            if self.end != 0:
                return
        self.end = -1

    def ping_log(self, ping_ms):
        if ping_ms == -2:
            self.logger.print_msg(f'- Offline', 2)
        elif ping_ms == -1:
            self.logger.print_msg(f'- No response - time = 2000ms', 2)
        else:
            self.logger.print_msg(f'- Alive - time = {ping_ms}ms', 2)

    def input_process(self, message):
        if message == 'help':
            for line in str(help_msg).splitlines():
                self.client.logger.out_log(line)
        elif message == 'stop':
            self.client.try_stop()
        elif message == 'start':
            self.client.try_start()
        elif message == 'status':
            self.client.logger.print_msg(f"CBR status: Online = {self.client.connected}", 2)
        elif message == 'ping':
            ping = self.ping_test()
            self.ping_log(ping)
        elif message == 'reload':
            self.client.reload()
        elif message == 'restart':
            self.client.try_stop()
            time.sleep(0.1)
            self.client.try_start()
            self.client.logger.print_msg(f"CBR status: Online = {self.client.connected}", 2)
        elif message == 'exit':
            exit(0)
        elif message == 'forcedebug':
            self.client.logger.force_debug()
        elif message == 'test':
            for thread in threading.enumerate():
                print(thread.name)
        elif self.client.connected:
            self.client.send_msg(self.client.socket, msg_json_formatter(self.client.name, '', message))
        else:
            self.logger.info("Not Connected")

    def process_msg(self, msg, socket: soc.socket):
        if 'action' in msg.keys():
            if msg['action'] == 'result':
                if msg['result'] == 'login success':
                    self.logger.info("Login Success")
                else:
                    self.logger.error("Login in fail")
            elif msg['action'] == 'keepAlive':
                if msg['type'] == 'ping':
                    self.client.send_msg(socket, '{"action": "keepAlive", "type": "pong"}')
                elif msg['type'] == 'pong':
                    self.end = time.time()
            elif msg['action'] == 'message':
                for i in msg['message'].splitlines():
                    message = message_formatter(msg['client'], msg['player'], i)
                    self.logger.print_msg(message, 0)
                message = message_formatter(msg['client'], msg['player'], msg['message'])
                CQ_bot.send_text(message, group_id=self.client.config.react_group)
            elif msg['action'] == 'stop':
                self.client.close_connection()
                self.logger.info(f'Connection closed from server')


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
    def __init__(self, config: 'Config', logger: CBRLogger):
        self.config = config
        self.logger = logger
        self.socket = None
        self.connected = False
        self.cancelled = False
        self.connecting = False
        self.ip = config.host_name
        self.port = config.host_port
        self.name = config.name
        self.password = config.password
        super().__init__(config.aes_key, self)
        self.process = ClientProcess(self)

    def setup(self, new_config: Config):
        self.config.init_all_config()
        self.logger.load(new_config)
        super().__init__(new_config.aes_key, self)
        self.ip = new_config.host_name
        self.port = new_config.host_port
        self.name = new_config.name
        self.password = new_config.password
        self.connected = False
        self.cancelled = False
        self.connecting = False

    def try_start(self, auto_connect=False):
        if not self.connected and not self.connecting:
            self.connecting = True
            threading.Thread(target=self.start, name='CBR', daemon=True).start()
        elif not auto_connect:
            self.logger.error("Already Connected to server")

    def start(self):
        self.cancelled = False
        self.logger.print_msg(f"Connecting to server with client {self.name}", 2)
        self.logger.info(f'Open connection to {self.ip}:{self.port}')
        self.logger.info(f'version : {PLUGIN_METADATA["version"]}, lib version : {LIB_VERSION}')
        self.socket = soc.socket()
        try:
            self.socket.connect((self.ip, self.port))
        except Exception:
            self.logger.bug_log(error=True)
            self.connected = False
            return
        self.connected = True
        self.socket.settimeout(timeout)
        self.connecting = False
        self.handle_echo()

    def try_stop(self):
        if self.connected:
            self.close_connection()
            self.logger.print_msg("Closed connection", 2)
        else:
            self.logger.print_msg("Connection already closed", 2)

    def close_connection(self, target=''):
        if self.socket is not None and self.connected:
            self.cancelled = True
            self.send_msg(self.socket, json.dumps({'action': 'stop'}), target)
            self.socket.close()
            time.sleep(0.000001)  # for better logging priority
            self.logger.debug("Connection closed to server")
        self.connected = False

    def reload(self):
        self.logger.print_msg("Reload ChatBridgeReforged Client now", 2)
        self.close_connection()
        new_config = Config(self.logger)
        new_config.init_all_config()
        time.sleep(0.1)
        self.setup(new_config)
        self.logger.print_msg("Reload Config", 2)
        self.try_start()
        time.sleep(0.1)
        self.logger.print_msg(f"CBR status: Online = {self.connected}", 2)

    def keep_alive(self):
        while self.socket is not None and self.connected:
            self.logger.debug("keep alive")
            for i in range(ping_time):
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
            msg = self.receive_msg(self.socket, self.ip)
        except OSError as er:
            self.logger.debug("Stop Receive message")
            self.connected = False
            raise er
        msg = json.loads(msg)
        self.process.process_msg(msg, self.socket)

    def handle_echo(self):
        self.login(self.name, self.password)
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


def auto_restart():
    while True:
        time.sleep(5)
        if not client.connected:
            client.try_start(True)


def main():
    global client, CQ_bot
    logger = CBRLogger()
    config = Config(logger)
    config.init_all_config()
    client = CBRTCPClient(config, logger)
    client.try_start()
    logger.info("Starting CQ services")
    CQ_bot = CQClient(config, logger, client)
    threading.Thread(target=auto_restart, name="auto_restart", daemon=True).start()
    threading.Thread(target=CQ_bot.start, name="CQHTTP", daemon=True).start()
    while True:
        input_message = input()
        try:
            client.process.input_process(input_message)
        except Exception:
            client.logger.bug_log()


if __name__ == '__main__':
    main()
