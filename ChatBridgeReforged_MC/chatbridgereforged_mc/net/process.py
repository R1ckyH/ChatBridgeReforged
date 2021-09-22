import socket as soc
import threading
import time

from typing import TYPE_CHECKING

from chatbridgereforged_mc.resources import *

if TYPE_CHECKING:
    from chatbridgereforged_mc.net.tcpclient import CBRTCPClient


class ClientProcess:
    def __init__(self, client_class: 'CBRTCPClient'):
        self.client = client_class
        self.logger = client_class.logger
        self.end = 0

    def message_formatter(self, client_name, player, msg):
        if player != "":
            message = f"§7[§{self.client.config.client_color}{client_name}§7] <{player}> {msg}"  # chat message
        else:
            message = f"§7[§{self.client.config.client_color}{client_name}§7] {msg}"
        return message

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
        if message == 'help' or (message == '' and server is not None and info is not None):
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
                    message = self.message_formatter(msg['client'], msg['player'], i)
                    self.logger.print_msg(message, 0, player=msg['receiver'], server=self.client.server, not_spam=True)
            elif msg['action'] == 'stop':
                self.client.close_connection()
                self.logger.info(f'Connection closed from server')
            elif msg['action'] == 'command':
                command = msg['command']
                msg['result']['responded'] = True
                if self.client.server is not None:
                    if command.startswith("!!"):
                        self.client.server.execute_command(command)
                        return
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
                                return
                            msg['result']['type'] = 0
                            msg['result']['result'] = result
                else:
                    msg['result']['type'] = 3
                self.client.send_msg(socket, json.dumps(msg))
