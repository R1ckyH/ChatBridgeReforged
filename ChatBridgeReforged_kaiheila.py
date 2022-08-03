import asyncio
import khl
import hashlib
import json
import os
import queue
import re
import socket as soc
import struct
import threading
import time
import traceback
import zipfile
import zlib

from binascii import b2a_base64, a2b_base64
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from datetime import datetime
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from cbr.plugin.cbrinterface import CBRInterface
    from cbr.plugin.info import MessageInfo

PREFIX = '!!CBR'
PREFIX2 = '!!cbr'
PREFIX3 = '##KHL'
LIB_VERSION = "v20210915"
CLIENT_TYPE = "kaiheila"
CLIENT_NAME = "Kaiheila"
clients: Dict[str, 'CBRTCPClient']
Kaiheila_bot: 'KaiheilaClient'
restart_guardian: 'RestartGuardian'
local_logger: 'CBRLogger'

debug_mode = False
CONFIG_PATH = f'config/ChatBridgeReforged_{CLIENT_TYPE}.json'
LOG_PATH = f'logs/ChatBridgeReforged_{CLIENT_TYPE}.log'
CHAT_PATH = f'logs/ChatBridgeReforged_{CLIENT_TYPE}_chat.log'
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

METADATA = {
    'id': CLIENT_TYPE,
    'version': '0.2.5-dev030',
    'name': CLIENT_NAME,
    'description': f'Reforged of ChatBridge, Client for {CLIENT_NAME}.',
    'author': 'ricky',
    'link': 'https://github.com/R1ckyH/ChatBridgeReforged'
}

DEFAULT_CONFIG = {
    "host_name": "127.0.0.1",
    "host_port": 30001,
    "aes_key": "ThisIsTheSecret",
    "bot_token": "asdfghjklqwertyuiop.zxcvbn.mQWERTYUIOPSDFG-JKLZXCVBNM",
    "clients": [
        {
            "name": CLIENT_TYPE,
            "password": CLIENT_TYPE,
            "channel_id": "1101314858"
        },
    ]
}

DEFAULT_CLIENT_CONFIG = {
    "name": CLIENT_TYPE,
    "password": CLIENT_TYPE,
    "channel_id": "1101314858"
}


def help_formatter(mcdr_prefix, command, first_msg, click_msg, use_command=None):
    msg = f'{mcdr_prefix} {command} {first_msg}'
    return msg


def message_formatter(client_name, player, msg, keep=False):
    message = ""
    if client_name != "CBR" or keep:
        message += f"[{client_name}] "
    else:
        message += f">>> "
    if player != "":
        message += f"<{player}> {msg}"  # chat message
    else:
        message += f"{msg}"
    return message


def msg_json_formatter(client_name, player, msg):
    message = {
        "action": "message",
        "client": client_name,
        "player": player,
        "message": msg
    }
    return json.dumps(message)


def ping_formatter(pong=False):
    message = {
        "action": "keepAlive",
    }
    if pong:
        message.update({"type": "pong"})
    else:
        message.update({"type": "ping"})
    return json.dumps(message)


def login_formatter(name, password):
    message = {
        "action": "login",
        "name": name,
        "password": password,
        "lib_version": LIB_VERSION,
        "type": CLIENT_TYPE
    }
    return json.dumps(message)


def stop_formatter():
    message = {"action": "stop"}
    return json.dumps(message)


help_msg = '''§b-----------§fChatBridgeReforged_Client§b-----------§r
''' + help_formatter(PREFIX3, 'help', 'show help message§r', 'show help message') + '''
''' + help_formatter(PREFIX3, 'start', 'start ChatBridgeReforged client§r', 'start') + '''
''' + help_formatter(PREFIX3, 'stop', 'stop ChatBridgeReforged client§r', 'stop') + '''
''' + help_formatter(PREFIX3, 'status', 'show status of ChatBridgeReforged client§r', 'show status') + '''
''' + help_formatter(PREFIX3, 'reload', 'reload ChatBridgeReforged client§r', 'reload') + '''
''' + help_formatter(PREFIX3, 'restart', 'restart ChatBridgeReforged client§r', 'restart') + '''
''' + help_formatter(PREFIX3, 'ping', 'ping ChatBridgeReforged server§r', 'ping') + '''
''' + help_formatter(PREFIX3, 'say [client name] <msg>', 'ping ChatBridgeReforged server§r', 'ping') + '''
§b-----------------------------------------------§r'''


class CBRLogger:
    def __init__(self):
        self._debug_mode = debug_mode
        self.log_path = ''
        self.chat_path = ''

    def load(self):
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
        msg = re.sub("§.", "", str(msg))
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


class HeadingLogger:
    def __init__(self, logger: CBRLogger, name='', server=None):
        self.logger = logger
        self.name = name
        if server is None:
            self.__add_msg = ""
        else:
            self.__add_msg = f"[plugin] "
        if name != '':
            self.__add_msg += f"[{self.name}] "

    def info(self, msg):
        self.logger.info(self.__add_msg + str(msg))

    def error(self, msg):
        self.logger.error(self.__add_msg + str(msg))

    def debug(self, msg):
        self.logger.debug(self.__add_msg + str(msg))

    def chat(self, msg):
        self.logger.chat(self.__add_msg + str(msg))

    def bug_log(self, error=False):
        self.error('bug exist')
        for line in traceback.format_exc().splitlines():
            if error is True:
                self.error(line)
            else:
                self.debug(line)

    def force_debug(self):
        self.logger._debug_mode = not self.logger._debug_mode
        self.info(f'force debug: {self.logger._debug_mode}')

    def print_msg(self, msg, num, error=False, debug=False, not_spam=False):
        self.logger.print_msg(msg, num, error, debug, not_spam)


class Config:
    def __init__(self, logger: CBRLogger):
        self.logger = logger
        self.host_name = DEFAULT_CONFIG['host_name']
        self.host_port = DEFAULT_CONFIG['host_port']
        self.aes_key = DEFAULT_CONFIG['aes_key']
        self.clients = DEFAULT_CONFIG['clients']
        self.bot_token = DEFAULT_CONFIG['bot_token']
        self.channel_ids = []

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
        for i in data['clients']:
            for keys in DEFAULT_CLIENT_CONFIG.keys():
                if keys not in i.keys():
                    self.logger.debug(f"Config {keys} not found, use public value {DEFAULT_CLIENT_CONFIG[keys]}")
                    if keys in data.keys():
                        i.update({keys: data[keys]})
                    else:
                        i.update({keys: DEFAULT_CLIENT_CONFIG[keys]})
        for i in range(len(data['clients'])):
            data['clients'][i] = dict(sorted(data['clients'][i].items(), key=lambda kv: kv[0]))
            self.channel_ids.append(data['clients'][i]['channel_id'])
        return data

    def init_config(self):
        config_dict = self.load_config()
        self.host_name = config_dict['host_name']
        self.host_port = config_dict['host_port']
        self.aes_key = config_dict['aes_key']
        self.clients = config_dict['clients']
        self.clients = config_dict['clients']
        self.bot_token = config_dict['bot_token']

    def init_all_config(self):
        self.init_config()


class ClientConfig:
    def __init__(self, config: Config, name, password, channel_id):
        self.name = name
        self.password = password
        self.channel_id = channel_id
        self.logger = config.logger
        self.host_name = config.host_name
        self.host_port = config.host_port
        self.aes_key = config.aes_key
        self.clients = config.clients
        self.bot_token = config.bot_token


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


class KaiheilaClient(khl.Bot):
    def __init__(self, config: Config, logger, clients_dict, server=None):
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        super().__init__(config.bot_token)
        self.message_queue = queue.Queue()
        self.clients: Dict[str, 'CBRTCPClient'] = clients_dict
        self.server = server
        self.logger = HeadingLogger(logger, server=server)
        self.config = config
        self.end = False

    def stop(self):
        self.end = True
        while not self.end:
            time.sleep(0.01)
        self.logger.info(f"Disconnect to {CLIENT_NAME}")

    def start_client(self):
        self.logger.info(f"Starting {CLIENT_NAME} services")
        try:
            self.client.register(khl.MessageTypes.KMD, self.on_message)
            asyncio.ensure_future(self.on_ready(), loop=self.loop)
            self.loop.run_until_complete(self.start())
        except asyncio.exceptions.CancelledError:
            return
        except RuntimeError:
            return

    async def process_loop(self):
        while not end:
            await asyncio.sleep(0.1)
            if not self.message_queue.empty():
                data = self.message_queue.get()
                await self.send(await self.fetch_public_channel(str(data[0])), data[1])
            if self.end:
                self.logger.debug("Stopping all task")
                self.loop.stop()
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()
                self.end = False
                self.loop.run_until_complete(await asyncio.sleep(0.25))
                self.loop.close()
                return

    async def on_ready(self):
        await self.fetch_me()
        self.logger.info(f'Connected to {CLIENT_NAME}, logged on as {self.me.username}!')
        await self.process_loop()

    async def on_message(self, message: khl.Message):
        self.logger.debug('Message from {0.channel}#{0.channel.id} {0.author}: {0.content}'.format(message))
        if message.author == self.me.id:
            return
        if message.ctx.channel.id in self.clients.keys():
            client = self.clients[message.ctx.channel.id]
            msg = msg_json_formatter(client.name, message.author.username, message.content)
            message = message_formatter(client.name, message.author.username, message.content)
            if self.server is None:
                self.logger.info(message)
            client.send_msg(client.socket, msg)

    async def on_error(self, event_method, *args, **kwargs):
        self.logger.error(str(event_method))
        self.logger.bug_log()


class AESCryptor:
    """
    By ricky, most of the AESCryptor inspire from ChatBridge, thx Fallen_Breath

    [ChatBridge](https://github.com/TISUnion/ChatBridge) Sorry for late full credit
    """

    def __init__(self, key: str, logger: 'HeadingLogger', mode=AES.MODE_CBC):
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
            return text.decode("utf-8")
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
    def __init__(self, client_class: 'CBRTCPClient', server=None):
        self.client = client_class
        self.logger = client_class.logger
        self.end = 0
        self.server = server

    def ping_test(self):
        if not self.client.connected:
            return -2
        self.logger.debug(f'Ping to server')
        start_time = time.time()
        self.client.send_ping(self.client.socket, target='server')
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
            time.sleep(0.00001)
        self.end = -1

    def ping_log(self, ping_ms):
        if ping_ms == -2:
            self.logger.print_msg(f'{self.client.name}: Offline', 2)
        elif ping_ms == -1:
            self.logger.print_msg(f'{self.client.name}: No response - time = 2000ms', 2)
        else:
            self.logger.print_msg(f'{self.client.name}: Alive - time = {ping_ms}ms', 2)

    def process_msg(self, msg, socket: soc.socket):
        if "action" in msg.keys():
            if msg["action"] == 'result':
                if msg['result'] == 'login success':
                    if self.server is not None:
                        return
                    self.logger.info("Login Success")
                else:
                    self.logger.error("Login in fail")
            elif msg["action"] == 'keepAlive':
                if msg['type'] == 'ping':
                    self.client.send_ping(socket, True, "server")
                elif msg['type'] == 'pong':
                    self.end = time.time()
            elif msg["action"] == 'message':
                if msg['message'] is None:
                    self.logger.info(str(msg['message']))
                    return
                for i in msg['message'].splitlines():
                    message = message_formatter(msg['client'], msg['player'], i, True)
                    if self.server is None:
                        self.logger.print_msg(message, 0)
                msg['message'] = re.sub("§.", "", msg['message'])
                message = message_formatter(msg['client'], msg['player'], msg['message'])
                Kaiheila_bot.message_queue.put([self.client.channel_id, message])
            elif msg["action"] == 'stop':
                self.client.close_connection()
                self.logger.info(f'Connection closed from server')
        else:
            self.logger.error(f"Receive Unresolved message from server")
            self.logger.info(f"Close Connection to server")
            self.client.close_connection("Server")


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
        except OSError:
            self.logger.info("Connection to server lost")
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


class CBRTCPClient(Network):
    def __init__(self, config: 'Config', logger: CBRLogger, server=None):
        self.config = config
        self.logger = HeadingLogger(logger, config.name, server)
        self.server: 'CBRInterface' = server
        self.socket = None
        self.connected = False
        self.cancelled = False
        self.connecting = False
        self.name = config.name
        self.password = config.password
        self.channel_id = config.channel_id
        super().__init__(config.aes_key, self)
        self.process = ClientProcess(self, server)
        self.ping_guardian: PingGuardian
        self.ping_guardian = None

    def try_start(self, auto_connect=False):
        if not self.connected and not self.connecting:
            self.connecting = True
            threading.Thread(target=self.start, name=f"Client: '{self.name}'", daemon=True).start()
        elif not auto_connect:
            self.logger.error("Already Connected to server")

    def start(self):
        self.cancelled = False
        if self.server is None:
            self.logger.info(f"Connecting to server '{self.config.host_name}:{self.config.host_port}' with client name {self.name}")
            self.logger.info(f'version : {METADATA["version"]}, lib version : {LIB_VERSION}')
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
        if auto_restart:
            restart_guardian.restart()
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
        if self.ping_guardian is not None:
            self.ping_guardian.stop()
        if self.socket is not None and self.connected:
            self.cancelled = True
            self.send_stop(self.socket, target)
            self.socket.close()
            time.sleep(0.000001)  # for better logging priority
            self.logger.debug("Connection closed to server")
        self.connected = False
        self.connecting = False

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
        self.send_login(self.socket, self.name, self.password, "server")
        self.ping_guardian = PingGuardian(self, self.logger)
        self.ping_guardian.start()
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
        if auto_restart:
            restart_guardian.reset = False
        self.ping_guardian.stop()


def input_process(message):
    message = message.replace(PREFIX + ' ', "").replace(PREFIX2 + ' ', "").replace(PREFIX, "").replace(PREFIX2, "")
    if message == 'help' or message == '':
        for line in str(help_msg).splitlines():
            local_logger.out_log(line)
    elif message == 'stop':
        for i in clients.values():
            i.try_stop()
    elif message == 'start':
        for i in clients.values():
            i.try_start()
    elif message == 'status':
        for i in clients.values():
            local_logger.info(f"Status: '{i.name}' Online = {i.connected}")
    elif message == 'ping':
        for i in clients.values():
            ping = i.process.ping_test()
            i.process.ping_log(ping)
    elif message == 'reload':
        reload()
    elif message == 'restart':
        for i in clients.values():
            i.try_stop()
            time.sleep(0.1)
            i.try_start()
            time.sleep(0.1)
            local_logger.info(f"Status: '{i.name}' Online = {i.connected}")
    elif message == 'exit':
        exit(0)
    elif message == 'forcedebug':
        local_logger.force_debug()
    elif message == 'test':
        local_logger.info("Threads:")
        for thread in threading.enumerate():
            local_logger.info(f"- {thread.name}")
        local_logger.info(f"Restart Guardian: {restart_guardian.get_time_left()}s left")
    elif message.startswith('say') and len(args) > 1:
        msg = message.replace('say ' + args[1] + " ", '')
        for i in clients.values():
            if i.name == args[1]:
                if i.connected:
                    i.send_msg(i.client.socket, msg_json_formatter(i.name, '', msg.replace(i.name + ' ', '')))
                    i.logger.info(msg.replace(args[0] + " " + args[1] + " ", ""))
                else:
                    local_logger.info("Not connected")
                return
        local_logger.info("Client not found")
    elif message == "unload":
        on_unload(None)
    # elif self.client.connected:
    #    self.client.send_msg(self.client.socket, msg_json_formatter(self.client.name, '', message))
    else:
        local_logger.info('Unknown command, use help for help message')


class GuardianBase:
    def __init__(self, logger: HeadingLogger, name=''):
        self.logger = logger
        self.reset = False
        self.end = False
        self.name = name
        self.current = 0

    def start(self):
        threading.Thread(target=self.run, name=f"Restart_Guardian_{self.name}", daemon=True).start()
        self.logger.debug(f"Thread Restart_Guardian_{self.name} started")

    def run(self):
        self.end = False
        self.reset = False
        while not self.end:
            self.wait_restart()

    def stop(self):
        self.end = True
        self.reset = True

    def restart(self):
        self.reset = True
        if self.end:
            self.start()

    def wait_restart(self):
        pass

    def stopwatch(self, sec):
        for self.current in range(sec):
            time.sleep(1)
            if self.reset:
                return False
        return True


class PingGuardian(GuardianBase):
    def __init__(self, client, logger):
        super().__init__(logger, "ping: " + client.name)
        self.client = client

    def wait_restart(self):
        self.logger.debug("keep alive")
        for i in range(ping_time):
            time.sleep(1)
            if self.end:
                return
        if self.client.connected:
            self.client.send_ping(self.client.socket, target="server")


class RestartGuardian(GuardianBase):
    def __init__(self, logger, targets):
        super().__init__(logger, "CBR_client")
        self.targets: List['CBRTCPClient'] = targets
        self.wait_time = 0

    def _client_start(self):
        for i in self.targets:
            self.logger.debug(f"Try start")
            i.try_start(auto_connect=True)

    def get_time_left(self):
        return self.wait_time - self.current

    def wait_restart(self):
        for i in wait_time:
            self.wait_time = i
            finish = self.stopwatch(i)
            if finish and not self.reset:
                self._client_start()
            else:
                self.logger.debug(f"Auto_restart reset, restart after 5 sec")
                time.sleep(5)
                return
        while not self.end:
            finish = self.stopwatch(3600)
            if finish and not self.reset:
                self._client_start()
            else:
                self.logger.debug(f"Auto_restart reset, restart after 5 sec")
                time.sleep(5)
                return


def reload():
    global Kaiheila_bot
    local_logger.print_msg("Reload ChatBridgeReforged Client now", 2)
    for i in clients.values():
        i.close_connection()
    config = init_clients(local_logger, Kaiheila_bot.server)
    time.sleep(0.1)
    local_logger.print_msg("Reloaded Config", 2)
    for i in clients.values():
        i.try_start()
    time.sleep(0.1)
    if auto_restart:
        restart_guardian.reset = False
        restart_guardian.targets = list(clients.values())
    Kaiheila_bot.stop()
    time.sleep(0.1)
    Kaiheila_bot = KaiheilaClient(config, local_logger, clients, Kaiheila_bot.server)
    threading.Thread(target=Kaiheila_bot.start_client, name=CLIENT_NAME, daemon=True).start()
    for i in clients.values():
        local_logger.print_msg(f"Status: '{i.name}' Online = {i.connected}", 2)


def init_clients(logger, server: 'CBRInterface' = None):
    global clients
    config = Config(logger)
    config.init_all_config()
    clients = {}
    for i in config.clients:
        check_hack(server, i)
        client_config = ClientConfig(config, i["name"], i["password"], i["channel_id"])
        client = CBRTCPClient(client_config, logger, server)
        clients.update({client.channel_id: client})
    return config


def main(server=None):
    global Kaiheila_bot, restart_guardian, local_logger, clients
    local_logger = CBRLogger()
    config = init_clients(local_logger, server)
    if auto_restart:
        restart_guardian = RestartGuardian(HeadingLogger(local_logger, server=server), list(clients.values()))
    for client in clients.values():
        client.try_start()
    local_logger.load()
    Kaiheila_bot = KaiheilaClient(config, local_logger, clients, server)
    if auto_restart:
        restart_guardian.start()
    threading.Thread(target=Kaiheila_bot.start_client, name=CLIENT_NAME, daemon=True).start()
    if server is None:
        while True:
            input_message = input()
            try:
                input_process(input_message)
            except Exception:
                local_logger.bug_log()


# CBR plugin part

def check_hack(server: 'CBRInterface', config):
    if server is not None:
        hack_server = server._server
        if config['name'] not in hack_server.clients.keys():
            from cbr.lib.client import Client
            hack_server.config.clients.append({"name": config['name'], "password": config['password']})
            hack_server.clients.update({config['name']: Client(config['name'], config['password'])})


DEFAULT_MSG_CONFIG = {
    'full_message_clients': [
        CLIENT_TYPE
    ],
    'less_message_clients': [
        f'{CLIENT_TYPE}1'
    ]
}

full_msg_clients = []
less_msg_clients = []
disable_join_left = True
disable_chat_startswith_to_dc = ["##"]
config_path = f'config/{CLIENT_TYPE}.json'
disable_duplicate_send = True  # Not recommend sending False unless you sure that your kaiheila bot won't be banned
# if enabled, kaiheila will send message to both full message group and less message group at same time
# if not enable, message have prefix like ##khl will not be appeared in full message group


def replace_message(msg):
    msg = msg.replace("##mc ", '').replace('##MC ', '').replace('mc ', '').replace('MC ', '')
    msg = msg.replace('##khl ', '').replace('##KHL ', '').replace('dc ', '').replace('DC ', '')
    return msg


def check_start(msg):
    for i in disable_chat_startswith_to_dc:
        if msg.startswith(i):
            return False
    return True


def custom_check_send(target, msg, client, player, server: 'CBRInterface'):
    cache_disable_duplicate_send = False
    if client == "CBR":
        return False
    if target == 'full' and full_msg_clients != []:
        for i in full_msg_clients:
            if server.is_client_online(i):
                server.send_custom_message(client, i, msg, player)
                cache_disable_duplicate_send = disable_duplicate_send
    elif target == 'less' and less_msg_clients != []:
        for i in less_msg_clients:
            if server.is_client_online(i):
                server.send_custom_message(client, i, msg, player)
                cache_disable_duplicate_send = disable_duplicate_send
    return cache_disable_duplicate_send


def on_message(server: 'CBRInterface', info: 'MessageInfo'):
    if info.client_type == CLIENT_TYPE:
        if info.source_client in less_msg_clients and less_msg_clients != []:
            info.cancel_send_message()
            msg = info.content
            if msg.lower().startswith('##mc') or msg.lower().startswith('mc '):
                msg = replace_message(msg)
                servers = server.get_online_mc_clients()
                server.logger.info(f"[{info.source_client}] <{info.sender}> {msg}")
                for i in servers:
                    server.send_custom_message(info.source_client, i, msg, info.sender)
        elif info.source_client not in full_msg_clients:
            info.cancel_send_message()
    else:
        args = info.content.split(' ')
        msg = info.content
        if disable_join_left and len(args) == 3 and (args[1] == 'joined' or args[1] == 'left'):
            return
        if msg.lower().startswith('##khl') or msg.lower().startswith('dc '):
            msg = replace_message(msg)
            if not custom_check_send('less', msg, info.source_client, info.sender, server):
                custom_check_send('full', msg, info.source_client, info.sender, server)
        else:
            if check_start(info.content):
                custom_check_send('full', info.content, info.source_client, info.sender, server)


def on_command(server: 'CBRInterface', info: 'MessageInfo'):
    if info.content.startswith("##KHL"):
        info.cancel_send_message()
        input_process(info.content.replace("##KHL ", "").replace("##KHL", ""))
    elif info.content.lower().startswith('##khl') or info.content.lower().startswith('dc '):
        info.cancel_send_message()
        msg = replace_message(info.content)
        if not custom_check_send('less', msg, info.source_client, info.sender, server):
            custom_check_send('full', msg, info.source_client, info.sender, server)


def on_load(server: 'CBRInterface'):
    global full_msg_clients, less_msg_clients
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as config:
            data = json.load(config)
        change = False
        if isinstance(data['full_message_clients'], str):
            change = True
            data['full_message_clients'] = [data['full_message_clients']]
        if isinstance(data['less_message_clients'], str):
            change = True
            data['less_message_clients'] = [data['less_message_clients']]
        if change:
            with open(config_path, 'w', encoding='utf-8') as config:
                json.dump(data, config, indent=4)
    else:
        with open(config_path, 'w', encoding='utf-8') as config:
            json.dump(DEFAULT_MSG_CONFIG, config, indent=4)
        data = DEFAULT_MSG_CONFIG
    full_msg_clients = data['full_message_clients']
    less_msg_clients = data['less_message_clients']
    threading.Thread(target=main, args=(server,), name="CBR_MAIN", daemon=True).start()


def on_unload(server):
    input_process("stop")
    Kaiheila_bot.stop()
    if auto_restart:
        restart_guardian.stop()


if __name__ == '__main__':
    main()
