"""
CBR ServerInterface
"""
import json
import trio

from typing import TYPE_CHECKING

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
        self.cbr_logger: 'CBRLogger' = server.logger
        self.logger = ServerInterfaceLogger(self.cbr_logger, token)
        self._server_running = True
        self.__result_cache = None

    def is_client_online(self, client):
        """
            Check clients online or not
        """
        return self._server.clients[client].online

    def is_mc_client(self, client):
        """
            Check clients register for type `mc` or not
        """
        if self._server.clients[client].type == 'mc':
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
            send message to player in target client
        """
        if self._server_running is False:
            self.logger.error("Server closed, not allow to send message")
            return
        if target == "CBR":
            for i in msg.splitlines():
                self.logger.info('- ' + i)
            return
        if target in self._server.clients and self._server.clients[target].online:
            message = json.dumps(self._server.process.msg_formatter("CBR", "", msg, receiver))
            trio.from_thread.run(self._server.send_msg, self._server.clients[target].stream, message, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")
            # TODO: raise Error

    def send_message(self, msg, target):
        """
            send message to target client
        """
        if self._server_running is False:
            self.logger.error("Server closed, not allow to send message")
            return
        if target == "CBR":
            for i in msg.splitlines():
                self.logger.info('- ' + i)
            return
        if target in self._server.clients and self._server.clients[target].online:
            message = json.dumps(self._server.process.msg_formatter("CBR", "", msg))
            trio.from_thread.run(self._server.send_msg, self._server.clients[target].stream, message, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def send_custom_message(self, target, msg, client, player='', extra: dict = None):
        """
            send message to target client with extra custom information
        """
        if self._server_running is False:
            self.logger.error("Server closed, not allow to send message")
            return
        if target == "CBR":
            for i in msg.splitlines():
                self.logger.info('- ' + i)
            return
        if target in self._server.clients and self._server.clients[target].online:
            message = json.dumps(self._server.process.msg_formatter(client, player, msg, extra=extra))
            trio.from_thread.run(self._server.send_msg, self._server.clients[target].stream, message, target, trio_token=self.__token)
        else:
            self.logger.error(f"client {target} not found or not connected")

    def send_command(self, cmd, target) -> str:
        """
            return None if timeout
        """
        if self._server_running is False:
            self.logger.error("Server closed, not allow to send msg")
            return ''
        return trio.from_thread.run(self.__wait_cmd_result, target, cmd, trio_token=self.__token)

    def send_servers_command(self, cmd, targets) -> dict:
        """
            targets is list of server to send

            targets can't be string

            return None in dict if cant get result
        """
        if self._server_running is False:
            self.logger.error("Server closed, not allow to send msg")
            return {}
        return trio.from_thread.run(self.__wait_servers_cmd_result, targets, cmd, trio_token=self.__token)

    def execute_command(self, command, target):
        """
            execute command in a client server without return
        """
        if self._server_running is False:
            self.logger.error("Server closed, not allow to send msg")
            return {}
        return trio.from_thread.run(self._server.process.send_cmd(command, target), trio_token=self.__token)

    def register_help_message(self, prefix, msg):
        """
            register help message for command `##help`
        """
        self._server.add_register_help_msg(prefix, msg)

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
        with trio.move_on_after(2) as self._server.clients[target].cmd_lock:
            self._server.clients[target].cmd_result = None
            await self._server.process.send_cmd(cmd, target)
            await trio.sleep(2)
        return self._server.clients[target].cmd_result
