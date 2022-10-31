import json
import socket as soc
import threading
import time

from chatbridgereforged_mc.lib.config import Config
from chatbridgereforged_mc.lib.guardian import PingGuardian, RestartGuardian
from chatbridgereforged_mc.lib.logger import CBRLogger
from chatbridgereforged_mc.net.network import Network
from chatbridgereforged_mc.net.process import ClientProcess
from chatbridgereforged_mc.constants import *


class CBRTCPClient(Network):
    def __init__(self, config: "Config", logger: CBRLogger, server=None):
        self.config = config
        self.logger = logger
        self.server: PluginServerInterface = server
        self.socket = None
        self.connected = False
        self.cancelled = False
        self.connecting = False
        self.name = config.name
        self.password = config.password
        self.timeout = config.timeout
        super().__init__(config.aes_key, self)
        self.process = ClientProcess(self)
        if config.auto_restart:
            self.restart_guardian = RestartGuardian(logger, self)
        self.ping_guardian: PingGuardian
        self.ping_guardian = None

    def setup(self, new_config: Config):
        self.config.init_all_config()
        self.logger.load(new_config, self)
        super().__init__(new_config.aes_key, self)
        self.name = new_config.name
        self.password = new_config.password
        self.connected = False
        self.cancelled = False
        self.connecting = False

    def try_start(self, info=None, auto_connect=False):
        if not self.connected and not self.connecting:
            self.connecting = True
            threading.Thread(target=self.start, name="CBR", args=(info,), daemon=True).start()
        elif not auto_connect:
            if info is not None:
                self.logger.print_msg("Already Connected to server", 2, info, server=self.server, error=True)
            else:
                self.logger.print_msg("Already Connected to server", 0, error=True, not_spam=True)

    def start(self, info):
        self.cancelled = False
        self.logger.print_msg(f"Connecting to server '{self.config.host_name}:{self.config.host_port}' with client name {self.name}", 2, info=info, server=self.server)
        self.logger.info(f"version : {VERSION}, lib version : {LIB_VERSION}")
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
        if self.config.auto_restart:
            self.restart_guardian.restart()
        self.socket.settimeout(self.timeout)
        self.handle_echo()

    def try_stop(self, info=None):
        if self.connected:
            self.close_connection()
            self.restart_guardian.stop()
            self.logger.print_msg("Closed connection", 2, info, server=self.server)
        else:
            self.logger.print_msg("Connection already closed", 2, info, server=self.server)
            self.connected = False
            self.connecting = False

    def close_connection(self, target=""):
        self.ping_guardian.stop()
        if self.socket is not None and self.connected:
            self.cancelled = True
            self.send_stop(self.socket, target)
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
        self.ping_guardian = PingGuardian(self, self.logger, self.config)
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
                self.logger.bug_log(False)
                break
            except Exception:
                self.logger.debug("Cancel Process")
                if not self.cancelled:
                    self.logger.bug_log(False)
                break
        self.connected = False
        if self.config.auto_restart:
            self.restart_guardian.reset = False
        self.ping_guardian.stop()
