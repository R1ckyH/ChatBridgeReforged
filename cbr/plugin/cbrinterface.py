"""
CBR ServerInterface
"""
import trio

from typing import TYPE_CHECKING

from cbr.resources import formatter

if TYPE_CHECKING:
    from cbr.lib.logger import CBRLogger
    from cbr.net.tcpserver import CBRTCPServer


class ServerInterfaceLogger:
    """
        simple logger for server_interface, recommend to use this logger instead of CBRLogger
    """
    def __init__(self, logger: 'CBRLogger', token: trio.lowlevel.TrioToken):
        self.__logger = logger
        self.__token = token

    def info(self, msg):
        trio.from_thread.run_sync(self.__logger.info, msg, trio_token=self.__token)

    def error(self, msg):
        trio.from_thread.run_sync(self.__logger.error, msg, trio_token=self.__token)

    def warning(self, msg):
        trio.from_thread.run_sync(self.__logger.warning, msg, trio_token=self.__token)

    def debug(self, msg):
        trio.from_thread.run_sync(self.__logger.debug, msg, "plugin", trio_token=self.__token)


class CBRInterface:
    def __init__(self, server: 'CBRTCPServer', token: trio.lowlevel.TrioToken):
        self._server = server
        self.__token = token
        self.__formatter = formatter
        self.cbr_logger: 'CBRLogger' = server.logger
        self.logger = ServerInterfaceLogger(self.cbr_logger, token)
        self._server_running = True
        self.__result_cache = None

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

    def tell_message(self, msg, target, receiver=''):
        """
            send message to receiver in target client

            may not useful in some specific client type
        """
        if not self.__running():
            self.logger.error("Server closed, not allow to send anything")
            return
        if target == "CBR":
            for i in msg.splitlines():
                self.logger.info('- ' + i)
            return
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_message, stream, "CBR", "", msg, receiver, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")
            # TODO: raise Error

    def send_message(self, msg, target):
        """
            send message to target client
        """
        if not self.__running():
            self.logger.error("Server closed, not allow to send anything")
            return
        if target == "CBR":
            for i in msg.splitlines():
                self.logger.info('- ' + i)
            return
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_message, stream, "CBR", "", msg, "", target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def send_custom_message(self, target, msg, client, player=''):
        """
            send message to target client with extra custom information
        """
        if not self.__running():
            return
        if target == "CBR":
            for i in msg.splitlines():
                self.logger.info('- ' + i)
            return
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_message, stream, client, player, msg, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def execute_command(self, command, target):
        """
            execute command in a cbr client without return
        """
        if not self.__running():
            return None
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_command, stream, command, target, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def execute_mcdr_command(self, command, target):
        """
            execute mcdr command in a cbr client without return
        """
        if not self.__running():
            return
        if self.__exist(target) and self.is_client_online(target):
            stream = self._server.clients[target].stream
            trio.from_thread.run(self._server.send_command, stream, command, target, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def command_query(self, command, target):
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

    def servers_command_query(self, command, targets):
        """
            query for get the result of multi servers

            use this function instead of command_query to have a better performance if sending same command to multi cbr clients

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
        self._server.add_register_help_msg(prefix, msg)

    def __running(self):
        if self._server_running is False:
            self.logger.error("Server closed, not allow to send anything")
            return False
        return True

    def __exist(self, target):
        if target in self._server.clients:
            return True
        else:
            return False

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
                await self._server.send_command(self._server.clients[target].stream, cmd, target, target)
                await trio.sleep(2)
            return self._server.clients[target].cmd_result
        else:
            self.logger.error(f"client {target} not found or not connected")
            return None
