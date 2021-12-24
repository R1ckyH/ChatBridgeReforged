import hashlib
import json
import os
import socket as soc
import struct
import threading
import time
import traceback
import websocket
import zipfile
import zlib

from binascii import b2a_base64, a2b_base64
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from datetime import datetime

PREFIX = '!!CBR'
PREFIX2 = '!!cbr'
LIB_VERSION = "v20210915"
CLIENT_TYPE = "cqhttp"
client: 'CBRTCPClient'
CQ_bot: 'CQClient'

debug_mode = False
CONFIG_PATH = 'config/ChatBridgeReforged_cqhttp.json'
LOG_PATH = 'logs/ChatBridgeReforged_cqhttp.log'
CHAT_PATH = 'logs/ChatBridgeReforged_cqhttp_chat.log'
SIZE_TO_ZIP = 512  # kb
SIZE_TO_ZIP_CHAT = 512  # kb
DISABLE_CHAT_LOG = True
SPLIT_CHAT_LOG = False
auto_restart = True  # not recommend to change
client_color = '6'  # minecraft color code
ping_time = 60
timeout = 120
wait_time = [5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]
end = False

PLUGIN_METADATA = {
    'id': 'chatbridgereforged_cqhttp',
    'version': '0.0.1-dev021',
    'name': 'ChatBridgeReforged_cqhttp',
    'description': 'Reforged of ChatBridge, Client for cqhttp.',
    'author': 'ricky',
    'link': 'https://github.com/R1ckyH/ChatBridgeReforged'
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


def help_formatter(mcdr_prefix, command, first_msg, click_msg, use_command=None):
    msg = f'{mcdr_prefix} {command} {first_msg}'
    return msg


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
        self.chat_path = ''
        self.client = None

    def load(self, client_class=None):
        self.client: CBRTCPClient = client_class
        self._debug_mode = debug_mode
        self.log_path = LOG_PATH
        self.chat_path = CHAT_PATH
        compressor = Compressor(self)
        compressor.zip_log(self.log_path, SIZE_TO_ZIP)
        compressor.zip_log(self.chat_path, SIZE_TO_ZIP_CHAT)

    def info(self, msg):
        self.out_log(msg)

    def error(self, msg):
        self.out_log(msg, error=True)

    def chat(self, msg):
        if not DISABLE_CHAT_LOG:
            self.out_log(msg, error=True, chat=True)

    def debug(self, msg):
        self.out_log(msg, debug=True)

    def out_log(self, msg: str, error=False, debug=False, not_spam=False, chat=False):
        for i in range(6):
            msg = msg.replace('§' + str(i), '').replace('§' + chr(97 + i), '')
        msg = msg.replace('§6', '').replace('§7', '').replace('§8', '').replace('§9', '').replace('§r', '')
        heading = '[CBR] ' + datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        if chat:
            msg = heading + '[CHAT]: ' + msg
            if SPLIT_CHAT_LOG:
                if self.chat_path != '':
                    print(msg + '\n', end='')
                    with open(self.chat_path, 'a+', encoding='utf-8') as log:
                        log.write(msg + '\n')
                return
        elif error:
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
                with open(self.log_path, 'a+', encoding='utf-8') as log:
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


class Compressor:
    def __init__(self, logger: 'CBRLogger'):
        self.logger = logger

    def zip_log(self, file_path, max_size):
        self.logger.debug(f"Start zip file: '{os.path.basename(file_path)}'")
        if os.path.isfile(file_path):
            file_size = (os.path.getsize(file_path) / 1024)
            if file_size > max_size:
                if file_path == CHAT_PATH:
                    zip_name = 'logs/CBR_chat'
                else:
                    zip_name = 'logs/CBR_'
                zip_name += time.strftime('%Y-%m-%d_%H%M%S', time.localtime(os.path.getmtime(file_path))) + '.zip'
                with zipfile.ZipFile(zip_name, 'w') as zipper:
                    zipper.write(file_path, arcname=os.path.basename(file_path), compress_type=zipfile.ZIP_DEFLATED)
                    os.remove(file_path)
                self.logger.debug("zipped old file")
            else:
                self.logger.debug("Not enough size to zip")
        else:
            self.logger.debug("Nothing to zip")


class CQClient(websocket.WebSocketApp):
    def __init__(self, config: Config, logger: CBRLogger, client_class: 'CBRTCPClient'):
        super().__init__(config.ws_url, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close,
                         on_open=self.on_open)
        self.ws_url = config.ws_url
        self.client = client_class
        self.logger = logger
        self.config = config
        self.connected = False
        self.success_connect = False
        self.thread_event = threading.Event()

    def run(self):
        self.logger.info(f"Starting CQ services to {self.ws_url}")
        self.run_forever()

    def auto_connect(self):
        def trigger(waiting_time):
            # if not self.connected:
            self.logger.error(f"Connection error to qq, reconnect after {waiting_time} second")
            time.sleep(waiting_time)
            self.thread_event.set()

        self.success_connect = False
        for i in wait_time:
            self.logger.debug(f"Check trigger")
            if self.success_connect or self.connected:
                self.logger.debug(f"Check reset, start after 5 sec")
                time.sleep(5)
                return
            trigger(i)
        while True:
            self.logger.debug(f"Check trigger")
            if self.success_connect or self.connected:
                self.logger.debug(f"Check reset")
                time.sleep(5)
                return
            trigger(3600)

    def auto_connector(self):
        time.sleep(10)
        while True:
            self.auto_connect()

    def start(self):
        if auto_restart:
            threading.Thread(name="cq_auto_restart", target=self.auto_connector, daemon=True).start()
            while True:
                self.run()
                self.thread_event.clear()
                self.thread_event.wait()
        else:
            self.run()

    def on_message(self, client_class, message):
        if not self.client.connected:
            return
        data = json.loads(message)
        if 'status' in data:
            if 'msg' in data and data['msg'] == 'SEND_MSG_API_ERROR':
                self.logger.error('CQBot error on sending message')
                self.logger.debug(data)
            else:
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

    def on_open(self, client_class):
        self.success_connect = True
        self.connected = True
        self.logger.info(f"Connected to qq")

    def on_close(self, client_class, close_code, close_msg):
        self.connected = False
        self.logger.info(f"Close connection with code : {close_code}")
        self.logger.debug(f"Close message : {close_msg}")

    def send_msg(self, msg, group_id):
        message = qq_msg_formatter(msg, group_id)
        self.logger.debug(f"Send: {message} to cq")
        try:
            self.send(message)
        except Exception:
            self.logger.error("Fail to send message to qq, try connect now")
            self.thread_event.set()
            try:
                self.send(message)
            except Exception:
                self.logger.bug_log(error=True)

    def send_text(self, text, group_id):
        msg = ''
        length = 0
        lines = text.rstrip().splitlines(keepends=True)
        for i in lines:
            if length > 500:
                self.send_msg(msg, group_id)
                msg = ''
                length = 0
            msg += i
            length += len(i)
        try:
            self.send_msg(msg, group_id)
        except websocket.WebSocketConnectionClosedException:
            self.logger.error("Connection to qq closed")


class AESCryptor:
    """
    By ricky, most of the AESCryptor respire from ChatBridge, thx Fallen_Breath

    [ChatBridge](https://github.com/TISUnion/ChatBridge) Sorry for late full credit
    """

    def __init__(self, key: str, logger: 'CBRLogger', mode=AES.MODE_CBC):
        self.__no_encrypt = key == ''
        self.key = hashlib.sha256(key.encode("utf-8")).digest()[:16]
        self.logger = logger
        self.mode = mode

    def get_cryptor(self):
        return AES.new(self.key, self.mode, self.key)

    @staticmethod
    def __to16length(text: str):
        text = bytes(text, encoding="utf-8")
        return pad(text, 16)

    def encrypt(self, text):
        if self.__no_encrypt:
            return text.encode("utf-8")
        text = self.__to16length(text)
        result = self.get_cryptor().encrypt(text)
        return b2a_base64(zlib.compress(result, 9))

    def decrypt(self, text):
        if self.__no_encrypt:
            return text
        text = zlib.decompress(a2b_base64(text))
        try:
            result = unpad(self.get_cryptor().decrypt(text), 16)
        except Exception as err:
            self.logger.error('TypeError when decrypting text')
            self.logger.error('Text =' + str(text))
            self.logger.error('Len(text) =' + str(len(text)))
            self.logger.error(str(err.args))
            raise err
        try:
            result = str(result, encoding='utf-8')
        except UnicodeDecodeError:
            self.logger.error('Error at decrypt string conversion')
            self.logger.error('Raw result = ' + str(result))
            result = str(result, encoding='ISO-8859-1')
            self.logger.error('ISO-8859-1 = ' + str(result))
        return result


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
        message = message.replace(PREFIX + ' ', "").replace(PREFIX2 + ' ', "").replace(PREFIX, "").replace(PREFIX2, "")
        if message == 'help' or message == '':
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
            time.sleep(0.1)
            self.logger.print_msg(f"CBR status: Online = {self.client.connected}", 2)
        elif message == 'exit':
            exit(0)
        elif message == 'forcedebug':
            self.logger.force_debug()
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
                if msg['message'] is None:
                    self.logger.info(str(msg['message']))
                    return
                for i in msg['message'].splitlines():
                    message = message_formatter(msg['client'], msg['player'], i)
                    self.logger.print_msg(message, 0)
                for i in range(6):
                    msg['message'] = msg['message'].replace('§' + str(i), '').replace('§' + chr(97 + i), '')
                msg['message'] = msg['message'].replace('§6', '').replace('§7', '').replace('§8', '').replace('§9', '')
                message = message_formatter(msg['client'], msg['player'], msg['message'])
                CQ_bot.send_text(message, group_id=self.client.config.react_group)
            elif msg['action'] == 'stop':
                self.client.close_connection()
                self.logger.info(f'Connection closed from server')
        else:
            self.logger.error(f"Receive Unresolved message from server")
            self.logger.info(f"Close Connection to server")
            self.client.close_connection("Server")


class Network(AESCryptor):
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
            msg = str(msg, encoding='utf-8')
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


class CBRTCPClient(Network):
    def __init__(self, config: 'Config', logger: CBRLogger):
        self.config = config
        self.logger = logger
        self.socket = None
        self.connected = False
        self.cancelled = False
        self.connecting = False
        self.success_connect = False
        self.name = config.name
        self.password = config.password
        super().__init__(config.aes_key, self)
        self.process = ClientProcess(self)

    def setup(self, new_config: Config):
        self.config.init_all_config()
        self.logger.load(self)
        super().__init__(new_config.aes_key, self)
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
        self.logger.info(f'Open connection to {self.config.host_name}:{self.config.host_port}')
        self.logger.info(f'version : {PLUGIN_METADATA["version"]}, lib version : {LIB_VERSION}')
        self.socket = soc.socket()
        try:
            self.socket.connect((self.config.host_name, self.config.host_port))
        except Exception:
            self.logger.bug_log(error=True)
            self.connected = False
            self.connecting = False
            return
        self.connected = True
        self.connecting = False
        self.success_connect = True
        self.socket.settimeout(timeout)
        self.handle_echo()

    def try_stop(self):
        if self.connected:
            self.close_connection()
            self.logger.print_msg("Closed connection", 2)
        else:
            self.logger.print_msg("Connection already closed", 2)
            self.connected = False
            self.connecting = False

    def close_connection(self, target=''):
        if self.socket is not None and self.connected:
            self.cancelled = True
            self.send_msg(self.socket, json.dumps({'action': 'stop'}), target)
            self.socket.close()
            time.sleep(0.000001)  # for better logging priority
            self.logger.debug("Connection closed to server")
        self.connected = False
        self.connecting = False

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
        while self.socket is not None and self.connected and not end:
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
            msg = self.receive_msg(self.socket, self.config.host_name)
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


def wait_restart():
    client.success_connect = False
    for i in wait_time:
        time.sleep(i)
        if not client.success_connect and not client.connected:
            # self.logger.error(f"Connection failed, reconnect after {waiting_time} second")
            client.logger.debug(f"Try start")
            client.try_start(auto_connect=True)
        else:
            client.logger.debug(f"Auto_restart reset after 5 sec")
            time.sleep(5)
            return
    while True:
        if not client.success_connect and not client.connected:
            time.sleep(3600)
            client.logger.debug(f"Try start")
            client.try_start(auto_connect=True)
        else:
            client.logger.debug(f"Auto_restart reset after 5 sec")
            time.sleep(5)
            return


def restart_loop():
    while not end:
        wait_restart()


def main():
    global client, CQ_bot
    logger = CBRLogger()
    config = Config(logger)
    config.init_all_config()
    client = CBRTCPClient(config, logger)
    logger.load(client)
    client.try_start()
    CQ_bot = CQClient(config, logger, client)
    if auto_restart:
        threading.Thread(target=restart_loop, name="auto_restart", daemon=True).start()
    threading.Thread(target=CQ_bot.start, name="CQHTTP", daemon=True).start()
    while True:
        input_message = input()
        try:
            client.process.input_process(input_message)
        except Exception:
            client.logger.bug_log()


if __name__ == '__main__':
    main()
