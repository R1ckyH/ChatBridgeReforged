import json
import time
import trio

from typing import TYPE_CHECKING

import cbr
from cbr.lib.logger import CBRLogger
from cbr.plugin.info import MessageInfo
from cbr.resources import formatter

if TYPE_CHECKING:
    from cbr.net.tcpserver import CBRTCPServer
    from cbr.plugin.plugin import PluginManager

help_msg = """§r====================CBR====================
##help §r->§a get plugin help msg
##CBR help/? §r->§a get help msg
##CBR status §r->§a Show CBR status
##CBR plugin §r->§a Show plugin command help message
##CBR reload §r->§a Show reload command help message
"""
reload_msg = """§r====================CBR====================
##CBR reload plugin §r->§a modify all changed plugin
##CBR reload all §r->§a Reload all above
"""
"""
##CBR reload config §r->§a reload CBR config
"""  # TODO reload config(next version)?
plugin_msg = """§r====================CBR====================
##CBR plugin list §r->§a show plugin list
##CBR plugin load §b<plugin_file_name> §r->§a load plugin
##CBR plugin unload §b<plugin_file_name> §r->§a unload plugin(Not available without cli)
##CBR plugin reload §b<plugin_id> §r->§a modify all changed plugin
##CBR plugin reloadall §r->§a reload all plugins
##CBR plugin enable §b<plugin_id> §r->§a enable plugin
##CBR plugin disable §b<plugin_id> §r->§a disable plugin(Not available without cli)
"""
status_msg = """§r====================CBR====================
##CBR status CBR §r->§a show CBR status
##CBR status ping §e[client_name] §r->§a show ping of clients
##CBR status online §r->§a show status of clients
##CBR status all §r->§a Reload all above
"""
cli_help_msg = """§r====================CBR====================
##CBR help/? -> get help msg
##CBR status -> Show CBR status
##CBR plugin -> Show plugin command help message
##CBR reload -> Show reload command help message
list -> get clients in config.yml
stop/end -> stop server
stop <client name> -> stop client connection
ping -> ping clients
ping <client name> -> ping client
say <msg> -> send msg to clients
cmd <client name> -> send cmd to client
"""


class Process:
    def __init__(self, tcp_server: "CBRTCPServer", logger: CBRLogger):
        self.server = tcp_server
        self.logger = logger
        self.plugin_manager: "PluginManager" = self.server.plugin_manager
        self.formatter = formatter

    async def close_connection(self, stream: trio.SocketStream, target):
        if target != "" and self.server.clients[target].online:
            self.server.clients[target].online = False
            await self.server.send_stop(stream, target)
            process = self.server.clients[target].process
            process.cancelled = True
            if process.cancel_scope is not None:
                process.cancel_scope.cancel()
        elif target != "":
            self.logger.warning(f"{target} is already close")
        if stream is not None:
            await stream.aclose()

    async def msg_mc_server(self, msg, client_except=""):
        for i in self.server.clients.keys():
            if client_except != i and self.server.clients[i].online and (self.server.clients[i].type == "mc" or client_except == "CBR"):
                stream = self.server.clients[i].stream
                await self.server.send_msg(stream, str(msg), i)

    async def ping_test(self, target):
        client = self.server.clients[target]
        if not client.online:
            return -2
        self.logger.debug(f"Ping to {target}", "CBR")
        client.process.ping_end = -1
        with trio.move_on_after(2) as client.ping_lock:
            start_time = time.time()
            await self.server.send_ping(client.stream, target=target)
            await trio.sleep(2)
        if client.process.ping_end == -1:
            self.logger.debug(f"No response from {target}", "CBR")
            return -1
        ping = (client.process.ping_end - start_time) * 1000
        self.logger.debug(f"get ping result from {target}:{ping}", "CBR")
        return round(ping, 1)

    @staticmethod
    def ping_log(ping, target):
        if ping == -2:
            return f"- {target}: Offline"
        elif ping == -1:
            return f"- {target}: No response - time = 2000ms"
        else:
            return f"- {target}: Alive - time = {ping}ms"

    async def message_process(self, client, player, msg, current_client, event="on_message", raw_msg: dict = None):
        message = self.formatter.info_formatter(client, player, msg)
        if client in self.server.clients.keys():
            client_type = self.server.clients[client].type
        else:
            client_type = ""
        info = MessageInfo(client, msg, player, client_type, self.logger)
        async with trio.open_nursery() as nursery:
            await self.plugin_manager.run_event(event, info, nursery=nursery)
            if event == "on_message":
                if info.is_send_message():
                    await self.msg_mc_server(self.formatter.message_formatter(client, player, msg), current_client)
                    self.logger.chat(message)
                args = msg.split(" ")
                if player == "" and len(args) == 3 and info.client_type == "mc":
                    if args[1] == "joined":
                        await self.plugin_manager.run_event("on_player_joined", args[0], info, nursery=nursery)
                    elif args[1] == "left":
                        await self.plugin_manager.run_event("on_player_left", args[0], info, nursery=nursery)
            else:
                if info.is_send_message():
                    return False
                else:
                    return True


class ServerProcess(Process):
    def __init__(self, tcp_server, logger: CBRLogger):
        super().__init__(tcp_server, logger)
        self.server = tcp_server
        self.logger = logger
        self.cancelled = False

    def online_list(self):
        cnt = len(self.server.clients)
        msg = f"Client count: {cnt}"
        for i in self.server.clients.keys():
            msg += f"\n- {i} : online = {self.server.clients[i].online}"
        return msg

    async def ping_cache(self, target):
        self.server.clients[target].ping = await self.ping_test(target)

    def count_online_client(self):
        count = 0
        for i in self.server.clients.values():
            if i.online:
                count += 1
        return count

    def get_status(self):
        msg = f"ChatBridgeReforged@{cbr.__version__}\n"
        msg += f"Lib version : {cbr.__lib_version__}\n"
        msg += f"Online Client : {self.count_online_client()}"
        return msg

    async def ping_all(self):
        self.logger.debug("Start ping", "CBR")
        async with trio.open_nursery() as nursery:
            for i in self.server.clients.keys():
                nursery.start_soon(self.ping_cache, i)
        msg = ""
        for i in self.server.clients.keys():
            msg += "\n" + self.ping_log(self.server.clients[i].ping, i)
        return msg

    @staticmethod
    def get_help_msg(name=""):
        if name == "":
            return help_msg
        elif name == "reload":
            return reload_msg
        elif name == "plugin":
            return plugin_msg
        elif name == "status":
            return status_msg

    async def msg_process(self, msg: str, nursery: trio.Nursery):
        # args = msg.split(" ")
        # length = len(args)
        cancel = await self.message_process("CBR", "", msg, "CBR", "on_command")
        if cancel:
            return
        self.logger.error("Unknown command, use ##CBR help for help message")


class ClientProcess(Process):
    def __init__(self, tcp_server, logger: CBRLogger):
        super().__init__(tcp_server, logger)
        self.server = tcp_server
        self.logger = logger
        self.current_client = ""
        self.ping_end = 0
        self.cancelled = False

    async def add_new_client(self, stream: trio.SocketStream, name, lib_version, client_type):
        reconnect = False
        if self.server.clients[name].online:
            self.logger.debug(f"{name} already exist, stop old connection now", "CBR")
            await self.close_connection(self.server.clients[name].stream, name)
            reconnect = True
        self.server.clients[name].stream = stream
        self.server.clients[name].online = True
        self.server.clients[name].type = client_type
        if lib_version is not None:
            self.server.clients[name].lib_version = lib_version
            lib_msg = f" with lib version: {lib_version}"
        else:
            lib_msg = ""
        if reconnect:
            self.logger.info(f"Reconnect to {name}: {lib_version}")
        else:
            self.logger.info(f"Client: '{self.current_client}' connected to the server{lib_msg}")

    @staticmethod
    def client_type_check(msg):  # For old ChatBridge
        if "type" not in msg.keys():
            client_type = None
        else:
            client_type = msg["type"]
        return client_type

    def version_check(self, msg):
        if "lib_version" in msg.keys():
            lib_version = msg["lib_version"]
        else:
            lib_version = None
        if lib_version != cbr.__lib_version__:
            self.logger.warning(f"lib version of client {msg['name']}: {str(lib_version)} is not same with server : {cbr.__lib_version__}")
        return lib_version

    def login(self, name, password):
        if name in self.server.clients.keys() and self.server.clients[name].name == name:
            client = self.server.clients[name]
            if client.password == password:
                return True
            else:
                self.logger.error(f"Wrong password from client {name}'s login")
                self.logger.debug(
                    f"Client password is '{password}', not same with '{client.password}' in config.yml", "CBR")
                return False
        self.logger.error(f"Client {name} not found in config.yml")
        return False

    async def process_msg(self, msg, stream: trio.SocketStream, address, nursery: trio.Nursery):
        if "action" in msg.keys():
            if msg["action"] == "login":
                lib_version = self.version_check(msg)
                client_type = self.client_type_check(msg)
                if self.login(msg["name"], msg["password"]):
                    self.current_client = msg["name"]
                    await self.add_new_client(stream, msg["name"], lib_version, client_type)
                    await self.server.send_login_result(stream, target=self.current_client)
                    self.server.register_process(self, self.current_client)
                else:
                    await self.server.send_login_result(stream, False)
                    await stream.aclose()
                    self.logger.debug(f"connection from {address} closed now", "CBR")
            elif msg["action"] == "keepAlive":
                if msg["type"] == "ping":
                    await self.server.send_ping(stream, True, self.current_client)
                elif msg["type"] == "pong":
                    self.ping_end = time.time()
                    self.server.clients[self.current_client].ping_lock.cancel()
            elif msg["action"] == "message":
                nursery.start_soon(self.message_process, msg["client"], msg["player"], msg["message"],
                                   self.current_client, "on_message", msg)
            elif msg["action"] == "stop":
                await self.close_connection(stream, self.current_client)
                self.logger.info(f"Connection closed from {self.current_client}")
            elif msg["action"] == "command":
                sender = msg["sender"]
                receiver = msg["receiver"]
                command = msg["command"]
                if msg["result"]["responded"]:
                    if sender == "CBR":
                        if "type" not in msg["result"].keys():
                            self.logger.warning(
                                f"Unknown result of sending {command} to {receiver} , maybe you should update the version of CBR client")
                            self.server.clients[self.current_client].cmd_result = None
                        elif msg["result"]["type"] == 0:
                            self.server.clients[self.current_client].cmd_result = msg["result"]["result"]
                            self.logger.debug(
                                f"Result of Command to {receiver} finished, result: {msg['result']['result']}", "CBR")
                        elif msg["result"]["type"] == 1:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Command to {receiver} failed")
                        elif msg["result"]["type"] == 2:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Client {receiver} does not connected to rcon")
                        self.server.clients[self.current_client].cmd_lock.cancel()
                    elif self.server.clients[sender].online:
                        await self.server.send_msg(self.server.clients[sender].stream, json.dumps(msg), sender)
                        self.logger.info(f"Result of {command} send to {sender}")
                    else:
                        self.logger.error(f"Client {sender} is Closed")
                else:
                    if self.server.clients[receiver].online:
                        await self.server.send_msg(self.server.clients[receiver].stream, json.dumps(msg), receiver)
                        self.logger.info(f"Send Command {command} to {receiver}")
                    else:
                        self.logger.error(f"Client {receiver} not found")
            elif msg["action"] == "api":
                sender = msg["sender"]
                receiver = msg["receiver"]
                plugin = msg["plugin"]
                function = msg["function"]
                if msg["result"]["responded"]:
                    if sender == "CBR":
                        if "type" not in msg["result"].keys():
                            self.logger.warning(
                                f"Unknown result of using api of {plugin} to {receiver} , you may update the version of CBR client")
                            self.server.clients[self.current_client].cmd_result = None
                        elif msg["result"]["type"] == 0:
                            self.server.clients[self.current_client].cmd_result = msg["result"]["result"]
                            self.logger.debug(
                                f"Result of Command to {receiver} finished, result: {msg['result']['result']}", "CBR")
                        elif msg["result"]["type"] == 1:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Plugin {plugin} not find")
                        elif msg["result"]["type"] == 2:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Function {function} dose not exist in {plugin}")
                        elif msg["result"]["type"] == 3:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Other error exist")
                        self.server.clients[self.current_client].cmd_lock.cancel()
                    elif self.server.clients[sender].online:
                        await self.server.send_msg(self.server.clients[sender].stream, json.dumps(msg), sender)
                        self.logger.info(f"Result of api use of {plugin} send to {sender}")
                    else:
                        self.logger.error(f"Client {sender} is Closed")
                else:
                    if self.server.clients[receiver].online:
                        await self.server.send_msg(self.server.clients[receiver].stream, json.dumps(msg), receiver)
                        self.logger.info(f"Result of api use of {plugin} send to {sender}")
                    else:
                        self.logger.error(f"Client {receiver} not found")
        elif self.current_client == "":
            self.logger.warning(f"Undefined connection from {address}")
            self.cancelled = True
        else:
            self.logger.error(f"Receive Unresolved message, '{msg}' from {address} of client '{self.current_client}'")
            self.logger.info(f"Close Connection to {self.current_client}")
            await self.close_connection(stream, self.current_client)
