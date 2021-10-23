import json
import os
import socket as soc
import struct
import threading
import time
import traceback
import zipfile

from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES
from datetime import datetime

from utils.rtext import *

PREFIX = '!!CBR'
PREFIX2 = '!!cbr'
LIB_VERSION = "v20210915"
CLIENT_TYPE = "mc"
client: 'CBRTCPClient'

debug_mode = False
CONFIG_PATH = 'config/ChatBridgeReforged_MC.json'
LOG_PATH = 'logs/ChatBridgeReforged_MC.log'
CHAT_PATH = 'logs/ChatBridgeReforged_MC_chat.log'
SIZE_TO_ZIP = 512  # kb
SIZE_TO_ZIP_CHAT = 512  # kb
DISABLE_CHAT_LOG = False
SPLIT_CHAT_LOG = False
client_color = '6'  # minecraft color code
ping_time = 60
timeout = 120

PLUGIN_METADATA = {
    'id': 'chatbridgereforged_mc',
    'version': '0.0.1-RC-dev017',
    'name': 'ChatBridgeReforged_MC',
    'description': 'Reforged of ChatBridge, Client for normal mc server.',
    'author': 'ricky',
    'link': 'https://github.com/R1ckyH/ChatBridgeReforged',
    'dependencies': {
        'mcdreforged': '>=1.3.0'  # 0.9.x+
    }
}

DEFAULT_CONFIG = {
    "name": "survival",
    "password": "survival",
    "host_name": "127.0.0.1",
    "host_port": 30001,
    "aes_key": "ThisIsTheSecret"
}


def rtext_cmd(txt, msg, cmd):
    return RText(txt).h(msg).c(RAction.run_command, cmd)


def help_formatter(mcdr_prefix, command, first_msg, click_msg, use_command=None):
    if use_command is None:
        use_command = command
    msg = f'{mcdr_prefix} {command} §a{first_msg}'
    return rtext_cmd(msg, f'Click me to {click_msg}', f'{mcdr_prefix} {use_command}')


def message_formatter(client_name, player, msg):
    if player != "":
        message = f"§7[§{client_color}{client_name}§7] <{player}> {msg}"  # chat message
    else:
        message = f"§7[§{client_color}{client_name}§7] {msg}"
    return message


def msg_json_formatter(client_name, player, msg):
    message = {
        "action": "message",
        "client": client_name,
        "player": player,
        "message": msg
    }
    return json.dumps(message)


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

    def print_msg(self, msg, num, info=None, server=None, player='', error=False, debug=False, not_spam=False, chat=False):
        if num == 0:
            if self.client.server is not None:
                if server is not None:
                    if player == '':
                        server.say(msg)
                    else:
                        server.tell(player, msg)
            else:
                not_spam = False
            self.out_log(str(msg), not_spam=not_spam, chat=chat)
        elif num == 1:
            server.reply(info, msg)
            self.info(str(msg))
        elif num == 2:
            if info is None or not info.is_player:
                self.out_log(msg, error, debug)
            else:
                server.reply(info, msg)

    def force_debug(self, info=None, server=None):
        self._debug_mode = not self._debug_mode
        self.print_msg(f'force debug: {self._debug_mode}', 2, info, server=server)


class Config:
    def __init__(self, logger: CBRLogger, server=None):
        self.logger = logger
        self.server = server
        self.name = DEFAULT_CONFIG['name']
        self.password = DEFAULT_CONFIG['password']
        self.host_name = DEFAULT_CONFIG['host_name']
        self.host_port = DEFAULT_CONFIG['host_port']
        self.aes_key = DEFAULT_CONFIG['aes_key']

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

    def init_all_config(self):
        self.init_config()


class Compressor:
    def __init__(self, logger: 'CBRLogger'):
        self.logger = logger

    def zip_log(self, file_path, max_size):
        self.logger.debug(f"Start zip file: '{os.path.basename(file_path)}'")
        if os.path.isfile(file_path):
            file_size = (os.path.getsize(file_path)/1024)
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

    def ping_log(self, ping_ms, info=None, server=None):
        if ping_ms == -2:
            self.logger.print_msg(f'- Offline', 2, info, server=server)
        elif ping_ms == -1:
            self.logger.print_msg(f'- No response - time = 2000ms', 2, info, server=server)
        else:
            self.logger.print_msg(f'- Alive - time = {ping_ms}ms', 2, info, server=server)

    def input_process(self, message, server=None, info=None):
        if message == 'help' or message == '':
            if server is not None and info is not None:
                server.reply(info, help_msg)
            else:
                for line in str(help_msg).splitlines():
                    self.client.logger.out_log(line)
        elif message == 'stop':
            self.client.try_stop(info)
        elif message == 'start':
            self.client.try_start(info)
        elif message == 'status':
            self.client.logger.print_msg(f"CBR status: Online = {self.client.connected}", 2, info, server=server)
        elif message == 'ping':
            ping = self.ping_test()
            self.ping_log(ping, info, server)
        elif message == 'reload':
            self.client.reload(info)
        elif message == 'restart':
            self.client.try_stop(info)
            time.sleep(0.1)
            self.client.try_start(info)
            time.sleep(0.1)
            self.logger.print_msg(f"CBR status: Online = {self.client.connected}", 2, info, server=server)
        elif message == 'exit':
            exit(0)
        elif message == 'forcedebug':
            if info is None or not info.is_player or server.get_permission_level(info.player) > 2:
                self.logger.force_debug(info, server)
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
                    self.logger.print_msg(message, 0, player=msg['receiver'], server=self.client.server, not_spam=True)
            elif msg['action'] == 'stop':
                self.client.close_connection()
                self.logger.info(f'Connection closed from server')
            elif msg['action'] == 'command':
                command = msg['command']
                msg['result']['responded'] = True
                if self.client.server is not None:
                    if self.client.server.is_rcon_running():
                        result = self.client.server.rcon_query(command)
                        if result is not None:
                            msg['result']['type'] = 0
                            msg['result']['result'] = result
                        else:
                            msg['result']['type'] = 1
                    else:
                        msg['result']['type'] = 2
                else:
                    msg['result']['type'] = 2
                self.client.send_msg(socket, json.dumps(msg))
            elif msg['action'] == 'api':
                plugin_id = msg['plugin']
                function = msg['function']
                keys: list = msg['keys']
                msg['result']['responded'] = True
                if self.client.server is not None:
                    plugin = self.client.server.get_plugin_instance(plugin_id)
                    if plugin is None:
                        msg['result']['type'] = 1
                    else:
                        if not hasattr(plugin, function):
                            msg['result']['type'] = 2
                        else:
                            try:
                                func = getattr(plugin, function)
                                result = func(*keys)
                            except Exception:
                                msg['result']['type'] = 3
                                self.logger.bug_log(error=True)
                            else:
                                msg['result']['type'] = 0
                                msg['result']['result'] = result
                else:
                    msg['result']['type'] = 3
                self.client.send_msg(socket, json.dumps(msg))
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
        self.server = server
        self.socket = None
        self.connected = False
        self.cancelled = False
        self.connecting = False
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
        self.socket.settimeout(timeout)
        self.handle_echo()

    def try_stop(self, info=None):
        if self.connected:
            self.close_connection()
            self.logger.print_msg("Closed connection", 2, info, server=self.server)
        else:
            self.logger.print_msg("Connection already closed", 2, info, server=self.server)
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


def on_info(server, info):
    msg = info.content
    if msg.startswith(PREFIX) or msg.startswith(PREFIX2):
        # info.cancel_send_to_server()
        # if msg.endswith('<--[HERE]'):
        #    msg = msg.replace('<--[HERE]', '')
        client.process.input_process(msg.replace(PREFIX + ' ', "").replace(PREFIX2 + ' ', "").replace(PREFIX, "").replace(PREFIX2, ""), server, info)
    else:
        if client is None:
            return
        client.try_start()
        if info.is_player and client.connected:
            client.send_msg(client.socket, msg_json_formatter(client.name, info.player, info.content))


def on_player_joined(server, name, info=None):
    client.try_start()
    client.send_msg(client.socket, msg_json_formatter(client.name, '', name + ' joined ' + client.name))


def on_player_left(server, name, info=None):
    client.try_start()
    client.send_msg(client.socket, msg_json_formatter(client.name, '', name + ' left ' + client.name))


def on_unload(server):
    client.close_connection()


def main(server=None):
    global client
    logger = CBRLogger()
    config = Config(logger, server)
    config.init_all_config()
    client = CBRTCPClient(config, logger, server)
    logger.load(client)
    client.try_start()
    if server is None:
        while True:
            input_message = input()
            try:
                client.process.input_process(input_message)
            except Exception:
                client.logger.bug_log()


def on_load(server, old):
    if old is not None:
        try:
            old.client.try_stop()
        except Exception:
            old.client.logger.bug_log(error=True)
    server.add_help_message(PREFIX, "ChatBridgeReforged")
    time.sleep(0.5)
    main(server)


if __name__ == '__main__':
    main()
