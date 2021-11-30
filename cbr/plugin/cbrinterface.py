"""
CBR ServerInterface
"""
import trio

from typing import TYPE_CHECKING

from cbr.resources import formatter

if TYPE_CHECKING:
    from cbr.lib.logger import CBRLogger
    from cbr.net.tcpserver import CBRTCPServer
    from cbr.plugin.info import MessageInfo


class CBRInterfaceLogger:
    """
        simple logger for server_interface, recommend to use this logger instead of CBRLogger
    """
    def __init__(self, logger: 'CBRLogger', token: trio.lowlevel.TrioToken):
        self.__logger = logger
        self.__token = token
        self.__formatter = formatter

    def chat(self, msg):
        msg = self.__formatter.no_color_formatter(msg)
        trio.from_thread.run_sync(self.__logger.chat, msg, trio_token=self.__token)

    def info(self, msg):
        msg = self.__formatter.no_color_formatter(msg)
        trio.from_thread.run_sync(self.__logger.info, msg, trio_token=self.__token)

    def error(self, msg):
        msg = self.__formatter.no_color_formatter(msg)
        trio.from_thread.run_sync(self.__logger.error, msg, trio_token=self.__token)

    def warning(self, msg):
        msg = self.__formatter.no_color_formatter(msg)
        trio.from_thread.run_sync(self.__logger.warning, msg, trio_token=self.__token)

    def debug(self, msg):
        msg = self.__formatter.no_color_formatter(msg)
        trio.from_thread.run_sync(self.__logger.debug, msg, "plugin", trio_token=self.__token)


class CBRInterface:
    def __init__(self, server: 'CBRTCPServer', token: trio.lowlevel.TrioToken, plugin_id):
        self._server = server
        self.__token = token
        self.cbr_logger: 'CBRLogger' = server.logger
        self.logger = CBRInterfaceLogger(self.cbr_logger, token)
        self.__result_cache = None
        self.__current_plugin_id = plugin_id

    def is_client_online(self, client):
        """
            Check clients online or not
        """
        if self.__exist(client):
            return self._server.clients[client].online
        else:
            return False

    def is_mc_client(self, client):
        """
            Check clients register for type `mc` or not
        """
        if self.__exist(client) and self._server.clients[client].type == 'mc':
            return True
        else:
            return False

    def get_online_clients(self):
        """
            get list of online clients
        """
        clients = []
        for i in self._server.clients.keys():
            if self.is_client_online(i):
                clients.append(i)
        return clients

    def get_mc_clients(self):
        """
            get list of minecraft clients
        """
        clients = []
        for i in self._server.clients.keys():
            if self.is_mc_client(i):
                clients.append(i)
        return clients

    def get_online_mc_clients(self):
        """
            get list of online minecraft clients
        """
        clients = []
        for i in self._server.clients.keys():
            if self.is_client_online(i) and self.is_mc_client(i):
                clients.append(i)
        return clients

    def get_client_type(self, client):
        """
            get type of clients register, if not register return ''
        """
        if client in self._server.clients.keys():
            return self._server.clients[client].type

    def send_message(self, target, msg):
        """
            send message to target client
        """
        if not self.__running():
            self.logger.error("Server closed, not allow to send anything")
            return
        if target == "CBR":
            self.__split_msg(msg)
            return
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_message, stream, "CBR", "", msg, "", target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def tell_message(self, target, receiver, msg):
        """
            send message to receiver in target client

            may not useful in some specific client type
        """
        if not self.__running():
            self.logger.error("Server closed, not allow to send anything")
            return
        if target == "CBR":
            self.__split_msg(msg)
            return
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_message, stream, "CBR", "", msg, receiver, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")
            # TODO: raise Error(to be confirm)

    def reply(self, info: 'MessageInfo', msg):
        """
            reply to client or player(if exist)
        """
        if not self.__running():
            self.logger.error("Server closed, not allow to send anything")
            return
        if info.source_client == "CBR":
            self.__split_msg(msg)
            return
        target = info.source_client
        receiver = info.sender
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_message, stream, "CBR", "", msg, receiver, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def send_custom_message(self, self_client, target, msg, source_player='', receiver=''):
        """
            send message to target client with custom information
        """
        if not self.__running():
            return
        if target == "CBR":
            self.__split_msg(msg)
            return
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_message, stream, self_client, source_player, msg, receiver, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def execute_command(self, target, command):
        """
            execute command in a cbr client without return
        """
        if not self.__running():
            return None
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_command, stream, command, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def execute_mcdr_command(self, target, command):
        """
            execute mcdr command in a cbr client without return
        """
        if not self.__running():
            return
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_command, stream, command, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def command_query(self, target, command):
        """
            execute command in a cbr client with return

            return None if timeout or Error
        """
        if not self.__running():
            return None
        if self.__exist(target) and self.is_client_online(target):
            return trio.from_thread.run(self.__wait_cmd_result, target, command, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")
            return None

    def servers_command_query(self, targets: list, command):
        """
            query for get the result of multi servers

            use this function instead of command_query to have a better performance
            if sending same command to multi cbr clients

            targets is list of server to send

            targets can't be string

            return None in dict if cant get result
        """
        if not self.__running():
            return None
        return trio.from_thread.run(self.__wait_servers_cmd_result, targets, command, trio_token=self.__token)

    def api_query(self, target, plugin_id, function_name, keys: list):
        """
            query for get the result of api in mcdr plugin

            is is ok to have function name with plugin package in mcdr 2.0 which like `abc.xyz`

            key is a list that store string, dict or bool
        """
        pass
        if not self.__running():
            return None
        if self.__exist(target) and self.is_client_online(target):
            return trio.from_thread.run(self.__wait_api_result, target, plugin_id, function_name, keys, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")
            return None

    def register_help_message(self, prefix, msg):
        """
            register help message for command `##help`
        """
        self._server.add_register_help_msg(self.__current_plugin_id, prefix, msg)

    def __running(self):
        if self._server.server_running is False:
            self.logger.error("Server closed, not allow to send anything")
            return False
        return True

    def __exist(self, target):
        if target in self._server.clients:
            return True
        else:
            return False

    def __split_msg(self, msg):
        for i in msg.splitlines():
            if self.__current_plugin_id == "ChatBridgeReforged":
                self.logger.chat(i)
            else:
                self.logger.chat('- ' + i)

    async def __wait_api_result(self, target, plugin_id, function_name, keys):
        with trio.move_on_after(2) as self._server.clients[target].cmd_lock:
            self._server.clients[target].cmd_result = None
            stream = self._server.clients[target].stream
            await self._server.send_api(stream, target, plugin_id, function_name, keys, target)
            await trio.sleep(2)
        return self._server.clients[target].cmd_result

    async def __wait_servers_cmd_result(self, targets, cmd):
        self.__result_cache = {}
        async with trio.open_nursery() as nursery:
            for i in targets:
                nursery.start_soon(self.__cache_commands_result, i, cmd)
        results = self.__result_cache
        self.__result_cache = None
        return results

    async def __cache_commands_result(self, target, cmd):
        self.__result_cache.update({target: await self.__wait_cmd_result(target, cmd)})

    async def __wait_cmd_result(self, target, cmd):
        if self.__exist(target):
            with trio.move_on_after(2) as self._server.clients[target].cmd_lock:
                self._server.clients[target].cmd_result = None
                await self._server.send_command(self._server.clients[target].stream, cmd, target)
                await trio.sleep(2)
            return self._server.clients[target].cmd_result
        else:
            self.logger.error(f"client {target} not found or not connected")
            return None
