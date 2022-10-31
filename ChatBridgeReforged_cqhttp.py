import hashlib
import json
import os
import re
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
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from cbr.plugin.cbrinterface import CBRInterface
    from cbr.plugin.info import MessageInfo

PREFIX = "!!CBR"
PREFIX2 = "!!cbr"
PREFIX3 = "##CQ"
LIB_VERSION = "v20210915"
CLIENT_TYPE = "cqhttp"
clients: Dict[str, "CBRTCPClient"]
CQ_bot: "CQClient"
restart_guardian: "RestartGuardian"
local_logger: "CBRLogger"

debug_mode = False
CONFIG_PATH = "config/ChatBridgeReforged_cqhttp.json"
LOG_PATH = "logs/ChatBridgeReforged_cqhttp.log"
CHAT_PATH = "logs/ChatBridgeReforged_cqhttp_chat.log"
SIZE_TO_ZIP = 512  # kb
SIZE_TO_ZIP_CHAT = 512  # kb
DISABLE_CHAT_LOG = True
SPLIT_CHAT_LOG = False
auto_restart = True  # not recommend to change
client_color = "6"  # minecraft color code
ping_time = 60
timeout = 120
wait_time = [5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]
end = False

METADATA = {
    "id": "cqhttp",
    "version": "0.2.5-dev030",
    "name": "cqhttp",
    "description": "Reforged of ChatBridge, Client for cqhttp.",
    "author": "ricky",
    "link": "https://github.com/R1ckyH/ChatBridgeReforged"
}

DEFAULT_CONFIG = {
    "host_name": "127.0.0.1",
    "host_port": 30001,
    "aes_key": "ThisIsTheSecret",
    "ws_address": "127.0.0.1",  # not same with host_name
    "ws_port": "6700",
    "ws_access_token": "my_access_token",
    "clients": [
        {
            "name": "cqhttp",
            "password": "cqhttp",
            "react_group": "1101314858"
        },
    ]
}

DEFAULT_CLIENT_CONFIG = {
    "name": "cqhttp",
    "password": "cqhttp",
    "react_group": "1101314858"
}


def help_formatter(mcdr_prefix, command, first_msg, click_msg, use_command=None):
    msg = f"{mcdr_prefix} {command} {first_msg}"
    return msg


def message_formatter(client_name, player, msg):
    message = ""
    if client_name != "CBR":
        message += f"[{client_name}] "
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


def qq_msg_formatter(text, group_id):
    data = {
        "action": "send_group_msg",
        "params": {
            "group_id": group_id,
            "message": text
        }
    }
    return json.dumps(data)


help_msg = """§b-----------§fChatBridgeReforged_Client§b-----------§r
""" + help_formatter(PREFIX3, "help", "show help message§r", "show help message") + """
""" + help_formatter(PREFIX3, "start", "start ChatBridgeReforged client§r", "start") + """
""" + help_formatter(PREFIX3, "stop", "stop ChatBridgeReforged client§r", "stop") + """
""" + help_formatter(PREFIX3, "status", "show status of ChatBridgeReforged client§r", "show status") + """
""" + help_formatter(PREFIX3, "reload", "reload ChatBridgeReforged client§r", "reload") + """
""" + help_formatter(PREFIX3, "restart", "restart ChatBridgeReforged client§r", "restart") + """
""" + help_formatter(PREFIX3, "ping", "ping ChatBridgeReforged server§r", "ping") + """
""" + help_formatter(PREFIX3, "say [client name] <msg>", "ping ChatBridgeReforged server§r", "ping") + """
§b-----------------------------------------------§r"""


class CBRLogger:
    def __init__(self):
        self._debug_mode = debug_mode
        self.log_path = ""
        self.chat_path = ""

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
        heading = "[CBR] " + datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        if chat:
            msg = heading + "[CHAT]: " + msg
            if SPLIT_CHAT_LOG:
                if self.chat_path != "":
                    print(msg + "\n", end="")
                    with open(self.chat_path, "a+", encoding="utf-8") as log:
                        log.write(msg + "\n")
                return
        elif error:
            msg = heading + "[ERROR]: " + msg
        elif debug:
            if not self._debug_mode:
                return
            msg = heading + "[DEBUG]: " + msg
        else:
            msg = heading + "[INFO]: " + msg
        if not not_spam:
            print(msg + "\n", end="")
            if self.log_path != "":
                with open(self.log_path, "a+", encoding="utf-8") as log:
                    log.write(msg + "\n")

    def bug_log(self, error=True):
        self.error("bug exist")
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
        self.print_msg(f"force debug: {self._debug_mode}", 2)


class HeadingLogger:
    def __init__(self, logger: CBRLogger, name="", server=None):
        self.logger = logger
        self.name = name
        if server is None:
            self.__add_msg = ""
        else:
            self.__add_msg = f"[plugin] "
        if name != "":
            self.__add_msg += f"[{self.name}] "

    def info(self, msg):
        self.logger.info(self.__add_msg + str(msg))

    def error(self, msg):
        self.logger.error(self.__add_msg + str(msg))

    def debug(self, msg):
        self.logger.debug(self.__add_msg + str(msg))

    def chat(self, msg):
        self.logger.chat(self.__add_msg + str(msg))

    def bug_log(self, error=True):
        self.error("bug exist")
        for line in traceback.format_exc().splitlines():
            if error is True:
                self.error(line)
            else:
                self.debug(line)

    def force_debug(self):
        self.logger._debug_mode = not self.logger._debug_mode
        self.info(f"force debug: {self.logger._debug_mode}")

    def print_msg(self, msg, num, error=False, debug=False, not_spam=False):
        self.logger.print_msg(msg, num, error, debug, not_spam)


class Config:
    def __init__(self, logger: CBRLogger):
        self.logger = logger
        self.host_name = DEFAULT_CONFIG["host_name"]
        self.host_port = DEFAULT_CONFIG["host_port"]
        self.aes_key = DEFAULT_CONFIG["aes_key"]
        self.clients = DEFAULT_CONFIG["clients"]
        self.ws_address = DEFAULT_CONFIG["ws_address"]  # not same with host_name
        self.ws_port = DEFAULT_CONFIG["ws_port"]
        self.ws_access_token = DEFAULT_CONFIG["ws_access_token"]
        self.ws_url = f"ws://{self.ws_address}:{self.ws_port}/?access_token={self.ws_access_token}"
        self.react_groups = []

    def check_log_file(self):
        if not os.path.exists(LOG_PATH):
            os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
            self.logger.error("Log file not find")
            self.logger.info("Generate new log file")

    def load_config(self):
        sync = False
        self.check_log_file()
        if not os.path.exists(CONFIG_PATH):
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            self.logger.error("Config not find")
            self.logger.info("Generate default config")
            with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
                json.dump(DEFAULT_CONFIG, config_file, indent=4)
            return DEFAULT_CONFIG
        with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
            data = dict(json.load(config_file))
        for keys in DEFAULT_CONFIG.keys():
            if keys not in data.keys():
                self.logger.error(f"Config {keys} not found, use default value {DEFAULT_CONFIG[keys]}")
                data.update({keys: DEFAULT_CONFIG[keys]})
                sync = True
        if sync:
            with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
                json.dump(data, config_file, indent=4)
        for i in data["clients"]:
            for keys in DEFAULT_CLIENT_CONFIG.keys():
                if keys not in i.keys():
                    self.logger.debug(f"Config {keys} not found, use public value {DEFAULT_CLIENT_CONFIG[keys]}")
                    if keys in data.keys():
                        i.update({keys: data[keys]})
                    else:
                        i.update({keys: DEFAULT_CLIENT_CONFIG[keys]})
        for i in range(len(data["clients"])):
            data["clients"][i] = dict(sorted(data["clients"][i].items(), key=lambda kv: kv[0]))
            self.react_groups.append(data["clients"][i]["react_group"])
        return data

    def init_config(self):
        config_dict = self.load_config()
        self.host_name = config_dict["host_name"]
        self.host_port = config_dict["host_port"]
        self.aes_key = config_dict["aes_key"]
        self.clients = config_dict["clients"]
        self.ws_address = config_dict["ws_address"]  # not same with host_name
        self.ws_port = config_dict["ws_port"]
        self.ws_access_token = config_dict["ws_access_token"]
        self.ws_url = f"ws://{self.ws_address}:{self.ws_port}/?access_token={self.ws_access_token}"

    def init_all_config(self):
        self.init_config()


class ClientConfig:
    def __init__(self, config: Config, name, password, react_group):
        self.name = name
        self.password = password
        self.react_group = react_group
        self.logger = config.logger
        self.host_name = config.host_name
        self.host_port = config.host_port
        self.aes_key = config.aes_key
        self.clients = config.clients
        self.ws_address = config.ws_address  # not same with host_name
        self.ws_port = config.ws_port
        self.ws_access_token = config.ws_access_token
        self.ws_url = config.ws_url
        self.react_groups = config.react_groups


class Compressor:
    def __init__(self, logger: "CBRLogger"):
        self.logger = logger

    def zip_log(self, file_path, max_size):
        self.logger.debug(f"Start zip file: '{os.path.basename(file_path)}'")
        if os.path.isfile(file_path):
            file_size = (os.path.getsize(file_path) / 1024)
            if file_size > max_size:
                if file_path == CHAT_PATH:
                    zip_name = "logs/CBR_chat"
                else:
                    zip_name = "logs/CBR_"
                zip_name += time.strftime("%Y-%m-%d_%H%M%S", time.localtime(os.path.getmtime(file_path))) + ".zip"
                with zipfile.ZipFile(zip_name, "w") as zipper:
                    zipper.write(file_path, arcname=os.path.basename(file_path), compress_type=zipfile.ZIP_DEFLATED)
                    os.remove(file_path)
                self.logger.debug("zipped old file")
            else:
                self.logger.debug("Not enough size to zip")
        else:
            self.logger.debug("Nothing to zip")


class CQClient(websocket.WebSocketApp):
    def __init__(self, config: Config, logger: CBRLogger, clients_dict, server=None):
        super().__init__(config.ws_url, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close,
                         on_open=self.on_open)
        self.ws_url = config.ws_url
        self.clients: Dict[str, "CBRTCPClient"] = clients_dict
        self.server = server
        self.logger = HeadingLogger(logger, server=server)
        self.config = config
        self.connected = False
        self.thread_event = threading.Event()
        self.restart_guardian = None
        self.restart_guardian: CQGuardian

    def run(self):
        self.logger.info(f"Starting CQ services to {self.ws_url}")
        self.run_forever()

    def start(self):
        if auto_restart:
            self.restart_guardian = CQGuardian(self, self.logger)
            self.restart_guardian.start()
            while not self.restart_guardian.end:
                self.thread_event.clear()
                self.run()
                self.thread_event.wait()
        else:
            self.run()

    def stop(self):
        if self.restart_guardian is not None:
            self.restart_guardian.stop()
        self.keep_running = False
        time.sleep(0.1)
        self.thread_event.set()

    @staticmethod
    def on_message(self, message):
        data = json.loads(message)
        if "status" in data:
            if "msg" in data and data["msg"] == "SEND_MSG_API_ERROR":
                self.logger.error("CQBot error on sending message")
                self.logger.debug(data)
            else:
                self.logger.debug("CQBot return status {}".format(data["status"]))
        elif data["post_type"] == "message" and data["message_type"] == "group":
            if str(data["group_id"]) in self.config.react_groups and data["anonymous"] is None:
                client = self.clients[str(data["group_id"])]
                msg = msg_json_formatter(client.name, data["sender"]["nickname"], data["raw_message"])
                message = message_formatter(client.name, data["sender"]["nickname"], data["raw_message"])
                if self.server is None:
                    self.logger.info(message)
                client.send_msg(client.socket, msg)

    @staticmethod
    def on_error(self, error2=None):
        self.logger.error(str(error2))
        self.logger.bug_log()

    @staticmethod
    def on_open(self):
        self.connected = True
        if auto_restart:
            self.restart_guardian.restart()
        self.logger.info(f"Connected to qq")

    @staticmethod
    def on_close(self, close_code, close_msg):
        self.connected = False
        self.logger.info(f"Close connection with code : {close_code}")
        self.logger.debug(f"Close message : {close_msg}")
        if auto_restart:
            self.restart_guardian.reset = False

    def send_msg(self, msg, group_id):
        message = qq_msg_formatter(msg, group_id)
        self.logger.debug(f"Send: {message} to cq")
        try:
            self.send(message)
        except Exception:
            self.logger.error("Fail to send message to qq, try connect now")
            self.thread_event.set()
            try:
                if self.connected:
                    self.send(message)
            except Exception:
                self.logger.bug_log(error=False)

    def send_text(self, text, group_id):
        msg = ""
        length = 0
        lines = text.rstrip().splitlines(keepends=True)
        for i in lines:
            if length > 500:
                self.send_msg(msg, group_id)
                msg = ""
                length = 0
            msg += i
            length += len(i)
        try:
            self.send_msg(msg, group_id)
        except websocket.WebSocketConnectionClosedException:
            self.logger.error("Connection to qq closed")


class AESCryptor:
    """
    By ricky, most of the AESCryptor inspire from ChatBridge, thx Fallen_Breath

    [ChatBridge](https://github.com/TISUnion/ChatBridge) Sorry for late full credit
    """

    def __init__(self, key: str, logger: "HeadingLogger", mode=AES.MODE_CBC):
        self.__no_encrypt = key == ""
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
            self.logger.error("TypeError when decrypting text")
            self.logger.error("Text =" + str(text))
            self.logger.error("Len(text) =" + str(len(text)))
            self.logger.error(str(err.args))
            raise err
        try:
            result = str(result, encoding="utf-8")
        except UnicodeDecodeError:
            self.logger.error("Error at decrypt string conversion")
            self.logger.error("Raw result = " + str(result))
            result = str(result, encoding="ISO-8859-1")
            self.logger.error("ISO-8859-1 = " + str(result))
        return result


class ClientProcess:
    def __init__(self, client_class: "CBRTCPClient", server=None):
        self.client = client_class
        self.logger = client_class.logger
        self.end = 0
        self.server = server

    def ping_test(self):
        if not self.client.connected:
            return -2
        self.logger.debug(f"Ping to server")
        start_time = time.time()
        self.client.send_ping(self.client.socket, target="server")
        self.ping_result()
        self.logger.debug(f"get ping result from server")
        if self.end == -1:
            self.logger.debug(f"No response from server")
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
            self.logger.print_msg(f"{self.client.name}: Offline", 2)
        elif ping_ms == -1:
            self.logger.print_msg(f"{self.client.name}: No response - time = 2000ms", 2)
        else:
            self.logger.print_msg(f"{self.client.name}: Alive - time = {ping_ms}ms", 2)

    def process_msg(self, msg, socket: soc.socket):
        if "action" in msg.keys():
            if msg["action"] == "result":
                if msg["result"] == "login success":
                    if self.server is not None:
                        return
                    self.logger.info("Login Success")
                else:
                    self.logger.error("Login in fail")
            elif msg["action"] == "keepAlive":
                if msg["type"] == "ping":
                    self.client.send_ping(socket, True, "server")
                elif msg["type"] == "pong":
                    self.end = time.time()
            elif msg["action"] == "message":
                if msg["message"] is None:
                    self.logger.info(str(msg["message"]))
                    return
                for i in msg["message"].splitlines():
                    message = message_formatter(msg["client"], msg["player"], i)
                    if self.server is None:
                        self.logger.print_msg(message, 0)
                msg["message"] = re.sub("§.", "", msg["message"])
                message = message_formatter(msg["client"], msg["player"], msg["message"])
                CQ_bot.send_text(message, group_id=self.client.react_group)
            elif msg["action"] == "stop":
                self.client.close_connection()
                self.logger.info(f"Connection closed from server")
        else:
            self.logger.error(f"Receive Unresolved message from server")
            self.logger.info(f"Close Connection to server")
            self.client.close_connection("Server")


class NetworkBase(AESCryptor):
    def __init__(self, key, new_client: "CBRTCPClient"):
        super().__init__(key, logger=new_client.logger)
        self.client = new_client

    def receive_msg(self, socket: soc.socket, address):
        data = socket.recv(4)
        if len(data) < 4:
            self.logger.error("Data length error")
            return "{}"
        length = struct.unpack("I", data)[0]
        msg = socket.recv(length)
        try:
            msg = self.decrypt(msg)
        except Exception:
            self.logger.bug_log()
            return "{}"
        self.logger.debug(f"Received {msg!r} from {address!r}")
        return msg

    def send_msg(self, socket: soc.socket, msg, target=""):
        if not self.client.connected:
            self.logger.debug("Not connected to the server")
            return
        if target != "":
            target = "to " + target
        self.logger.debug(f"Send: {msg!r} {target}")
        msg = self.encrypt(msg)
        msg = struct.pack("I", len(msg)) + msg
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
    def __init__(self, config: "Config", logger: CBRLogger, server=None):
        self.config = config
        self.logger = HeadingLogger(logger, config.name, server)
        self.server: "CBRInterface" = server
        self.socket = None
        self.connected = False
        self.cancelled = False
        self.connecting = False
        self.name = config.name
        self.password = config.password
        self.react_group = config.react_group
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
            self.logger.info(f"version : {METADATA['version']}, lib version : {LIB_VERSION}")
        self.socket = soc.socket()
        try:
            self.socket.connect((self.config.host_name, self.config.host_port))
        except Exception:
            self.logger.bug_log()
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

    def close_connection(self, target=""):
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
                self.logger.error("Connection time out!")
                self.logger.debug("Closed connection to server")
                break
            except ConnectionAbortedError:
                self.logger.info("Connection closed")
                self.logger.bug_log(error=False)
                break
            except Exception:
                self.logger.debug("Cancel Process")
                if not self.cancelled:
                    self.logger.bug_log(error=False)
                break
        self.connected = False
        if auto_restart:
            restart_guardian.reset = False
        self.ping_guardian.stop()


def input_process(message):
    message = message.replace(PREFIX + " ", "").replace(PREFIX2 + " ", "").replace(PREFIX, "").replace(PREFIX2, "")
    if message == "help" or message == "":
        for line in str(help_msg).splitlines():
            local_logger.out_log(line)
    elif message == "stop":
        for i in clients.values():
            i.try_stop()
    elif message == "start":
        for i in clients.values():
            i.try_start()
    elif message == "status":
        for i in clients.values():
            local_logger.info(f"Status: '{i.name}' Online = {i.connected}")
    elif message == "ping":
        for i in clients.values():
            ping = i.process.ping_test()
            i.process.ping_log(ping)
    elif message == "reload":
        reload()
    elif message == "restart":
        for i in clients.values():
            i.try_stop()
            time.sleep(0.1)
            i.try_start()
            time.sleep(0.1)
            local_logger.info(f"Status: '{i.name}' Online = {i.connected}")
    elif message == "exit":
        exit(0)
    elif message == "forcedebug":
        local_logger.force_debug()
    elif message == "test":
        local_logger.info("Threads:")
        for thread in threading.enumerate():
            local_logger.info(f"- {thread.name}")
        local_logger.info(f"Restart Guardian: {restart_guardian.get_time_left()}s left")
    elif message.startswith("say") and len(args) > 1:
        msg = message.replace("say " + args[1] + " ", "")
        for i in clients.values():
            if i.name == args[1]:
                if i.connected:
                    i.send_msg(i.client.socket, msg_json_formatter(i.name, "", msg.replace(i.name + " ", "")))
                    i.logger.info(msg.replace(args[0] + " " + args[1] + " ", ""))
                else:
                    local_logger.info("Not connected")
                return
    elif message == "unload":
        on_unload(None)
    # elif self.client.connected:
    #    self.client.send_msg(self.client.socket, msg_json_formatter(self.client.name, "", message))
    else:
        local_logger.info("Unknown command, use help for help message")


class GuardianBase:
    def __init__(self, logger: "CBRLogger", name=""):
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


class CQGuardian(GuardianBase):
    def __init__(self, client: CQClient, logger):
        super().__init__(logger, "cqhttp")
        self.client = client

    def stopwatch(self, sec):
        result = super().stopwatch(sec)
        if result:
            self.logger.error(f"Connection error to qq, reconnect after {sec} second")
            self.client.thread_event.set()

    def wait_restart(self):
        for i in wait_time:
            self.logger.debug(f"Check trigger")
            if self.reset:
                self.logger.debug(f"Check reset, start after 5 sec")
                time.sleep(5)
                return
            self.stopwatch(i)
        while not self.end:
            self.logger.debug(f"Check trigger")
            if self.reset:
                self.logger.debug(f"Check reset")
                time.sleep(5)
                return
            self.stopwatch(3600)

    def run(self):
        super().run()


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
        self.targets: List["CBRTCPClient"] = targets
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
    global CQ_bot
    local_logger.print_msg("Reload ChatBridgeReforged Client now", 2)
    for i in clients.values():
        i.close_connection()
    config = init_clients(local_logger, CQ_bot.server)
    local_logger.print_msg("Reloaded Config", 2)
    CQ_bot.stop()
    for i in clients.values():
        i.try_start()
    if auto_restart:
        restart_guardian.reset = False
        restart_guardian.targets = list(clients.values())
    CQ_bot = CQClient(config, local_logger, clients, CQ_bot.server)
    threading.Thread(target=CQ_bot.start, name="CQHTTP", daemon=True).start()
    for i in clients.values():
        local_logger.print_msg(f"Status: '{i.name}' Online = {i.connected}", 2)


def init_clients(logger, server: "CBRInterface" = None):
    global clients
    config = Config(logger)
    config.init_all_config()
    clients = {}
    for i in config.clients:
        check_hack(server, i)
        client_config = ClientConfig(config, i["name"], i["password"], i["react_group"])
        client = CBRTCPClient(client_config, logger, server)
        clients.update({client.react_group: client})
    return config


def main(server=None):
    global CQ_bot, restart_guardian, local_logger, clients
    local_logger = CBRLogger()
    config = init_clients(local_logger, server)
    if auto_restart:
        restart_guardian = RestartGuardian(HeadingLogger(local_logger, server=server), list(clients.values()))
    for client in clients.values():
        client.try_start()
    local_logger.load()
    CQ_bot = CQClient(config, local_logger, clients, server)
    if auto_restart:
        restart_guardian.start()
    threading.Thread(target=CQ_bot.start, name="CQHTTP", daemon=True).start()
    if server is None:
        while True:
            input_message = input()
            try:
                input_process(input_message)
            except Exception:
                local_logger.bug_log(error=False)


# CBR plugin part

def check_hack(server: "CBRInterface", config):
    if server is not None:
        hack_server = server._server
        if config["name"] not in hack_server.clients.keys():
            from cbr.lib.client import Client
            hack_server.config.clients.append({"name": config["name"], "password": config["password"]})
            hack_server.clients.update({config["name"]: Client(config["name"], config["password"])})


DEFAULT_MSG_CONFIG = {
    "full_message_group_client": [
        "cqhttp1"
    ],
    "less_message_group_client": [
        "cqhttp"
    ]
}

full_msg_group_client = []
less_msg_group_client = []
disable_join_left = True
disable_chat_startswith_to_qq = ["##"]
config_path = "config/cqhttp.json"
disable_duplicate_send = True  # Not recommend sending False unless you sure that your qq bot won"t be banned
# if enabled, cq will send message to both full message group and less message group at same time
# if not enable, message have prefix like ##qq will not be appeared in full message group


def replace_message(msg):
    msg = msg.replace("##mc ", "").replace("##MC ", "").replace("mc ", "").replace("MC ", "")
    msg = msg.replace("##qq ", "").replace("##QQ ", "").replace("qq ", "").replace("QQ ", "")
    return msg


def check_start(msg):
    for i in disable_chat_startswith_to_qq:
        if msg.startswith(i):
            return False
    return True


def custom_check_send(target, msg, client, player, server: "CBRInterface"):
    cache_disable_duplicate_send = False
    if client == "CBR":
        return False
    if target == "full" and full_msg_group_client != []:
        for i in full_msg_group_client:
            if server.is_client_online(i):
                server.send_custom_message(client, i, msg, player)
                cache_disable_duplicate_send = disable_duplicate_send
    elif target == "less" and less_msg_group_client != []:
        for i in less_msg_group_client:
            if server.is_client_online(i):
                server.send_custom_message(client, i, msg, player)
                cache_disable_duplicate_send = disable_duplicate_send
    return cache_disable_duplicate_send


def on_message(server: "CBRInterface", info: "MessageInfo"):
    if info.client_type == "cqhttp":
        if info.source_client in less_msg_group_client and less_msg_group_client != []:
            info.cancel_send_message()
            msg = info.content
            if msg.lower().startswith("##mc") or msg.lower().startswith("mc "):
                msg = replace_message(msg)
                servers = server.get_online_mc_clients()
                server.logger.info(f"[{info.source_client}] <{info.sender}> {msg}")
                for i in servers:
                    server.send_custom_message(info.source_client, i, msg, info.sender)
        elif info.source_client not in full_msg_group_client:
            info.cancel_send_message()
    else:
        args = info.content.split(" ")
        msg = info.content
        if disable_join_left and len(args) == 3 and (args[1] == "joined" or args[1] == "left"):
            return
        if msg.lower().startswith("##qq") or msg.lower().startswith("qq "):
            msg = replace_message(msg)
            if not custom_check_send("less", msg, info.source_client, info.sender, server):
                custom_check_send("full", msg, info.source_client, info.sender, server)
        elif info.sender == "mc":
            if check_start(info.content):
                custom_check_send("full", info.content, info.source_client, info.sender, server)


def on_command(server: "CBRInterface", info: "MessageInfo"):
    if info.content.startswith("##CQ"):
        info.cancel_send_message()
        input_process(info.content.replace("##CQ ", "").replace("##CQ", ""))
    elif info.content.lower().startswith("##qq") or info.content.lower().startswith("qq "):
        info.cancel_send_message()
        msg = replace_message(info.content)
        if not custom_check_send("less", msg, info.source_client, info.sender, server):
            custom_check_send("full", msg, info.source_client, info.sender, server)


def on_load(server: "CBRInterface"):
    global full_msg_group_client, less_msg_group_client
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as config:
            data = json.load(config)
        change = False
        if isinstance(data["full_message_group_client"], str):
            change = True
            data["full_message_group_client"] = [data["full_message_group_client"]]
        if isinstance(data["less_message_group_client"], str):
            change = True
            data["less_message_group_client"] = [data["less_message_group_client"]]
        if change:
            with open(config_path, "w", encoding="utf-8") as config:
                json.dump(data, config, indent=4)
    else:
        with open(config_path, "w", encoding="utf-8") as config:
            json.dump(DEFAULT_MSG_CONFIG, config, indent=4)
        data = DEFAULT_MSG_CONFIG
    full_msg_group_client = data["full_message_group_client"]
    less_msg_group_client = data["less_message_group_client"]
    threading.Thread(target=main, args=(server,), name="CBR_MAIN", daemon=True).start()


def on_unload(server):
    input_process("stop")
    CQ_bot.stop()
    if auto_restart:
        restart_guardian.stop()
        CQ_bot.restart_guardian.stop()
        CQ_bot.thread_event.set()


if __name__ == "__main__":
    main()
