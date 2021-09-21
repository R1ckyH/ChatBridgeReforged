import json
import time
import trio
import threading

from typing import TYPE_CHECKING

from cbr.lib.logger import CBRLogger
from cbr.plugin.info import MessageInfo
from cbr.resources import formatter

if TYPE_CHECKING:
    from cbr.net.tcpserver import CBRTCPServer

help_msg = '''====================CBR====================
help/? -> get help msg
list -> get clients in config.yml
stop/end -> stop server
stop <client name> -> stop client connection
ping -> ping clients
ping <client name> -> ping client
say <msg> -> send msg to clients
cmd <client name> -> send cmd to client
'''


class Process:
    def __init__(self, tcp_server: 'CBRTCPServer', logger: CBRLogger):
        self.server = tcp_server
        self.logger = logger
        self.plugin_manager = self.server.plugin_manager
        self.formatter = formatter

    async def close_connection(self, stream: trio.SocketStream, target):
        if target != '':
            self.server.clients[target].online = False
            await self.server.send_stop(stream, target)
            process = self.server.clients[target].process
            process.cancelled = True
            if process.cancel_scope is not None:
                process.cancel_scope.cancel()
        await stream.aclose()

    async def msg_mc_server(self, msg, client_except=''):
        for i in self.server.clients.keys():
            if client_except != i and self.server.clients[i].online and self.server.clients[i].type == 'mc':
                stream = self.server.clients[i].stream
                await self.server.send_msg(stream, str(msg), i)

    async def ping_test(self, target):
        client = self.server.clients[target]
        if not client.online:
            return -2
        self.logger.debug(f'Ping to {target}', "CBR")
        client.process.ping_end = -1
        with trio.move_on_after(2) as client.ping_lock:
            start_time = time.time()
            await self.server.send_ping(client.stream, target=target)
            await trio.sleep(2)
        if client.process.ping_end == -1:
            self.logger.debug(f'No response from {target}', "CBR")
            return -1
        ping = (client.process.ping_end - start_time) * 1000
        self.logger.debug(f'get ping result from {target}:{ping}', "CBR")
        return round(ping, 1)

    def ping_log(self, ping, target):
        if ping == -2:
            self.logger.info(f'- {target}: Offline')
        elif ping == -1:
            self.logger.info(f'- {target}: No response - time = 2000ms')
        else:
            self.logger.info(f'- {target}: Alive - time = {ping}ms')

    async def message_process(self, client, player, msg, current_client, event='on_message', raw_msg: dict = None):
        message = self.formatter.info_formatter(client, player, msg)
        if raw_msg is not None and 'extra' in raw_msg.keys():
            extra = raw_msg['extra']
        else:
            extra = None
        if client in self.server.clients.keys():
            client_type = self.server.clients[client].type
        else:
            client_type = ''
        info = MessageInfo(client, msg, player, client_type, self.logger, extra)
        async with trio.open_nursery() as nursery:
            await self.plugin_manager.run_event(event, info, nursery=nursery)
            if event == 'on_message':
                if info.is_send_message():
                    await self.msg_mc_server(self.formatter.message_formatter(client, player, msg), current_client)
                    self.logger.info(message)
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
        self.logger.info(f'Client count: {cnt}')
        for i in self.server.clients.keys():
            self.logger.info(f"- {i} : online = {self.server.clients[i].online}")

    async def ping_all(self):
        self.logger.debug('Start ping', "CBR")
        for i in self.server.clients.keys():
            self.server.clients[i].ping = await self.ping_test(i)
        self.logger.info('Ping clients:')
        for i in self.server.clients.keys():
            self.ping_log(self.server.clients[i].ping, i)

    def help_msg(self):
        for i in help_msg.splitlines():
            self.logger.info(i)

    async def msg_process(self, msg: str, nursery: trio.Nursery):
        args = msg.split(' ')
        length = len(args)
        cancel = await self.message_process('CBR', '', msg, "CBR", 'on_command')
        if cancel:
            return
        if msg == 'help' or msg == '?':
            self.help_msg()
        elif msg == '##help' or msg == '#?':
            for i in self.server.get_register_help_msg().splitlines():
                self.logger.info(i)
        elif msg == 'list':
            self.online_list()
        elif msg.startswith('stop') or msg == 'end':
            if msg == 'stop' or msg == 'end':
                await self.server.stop()
            else:
                if length > 1 and args[1] in self.server.clients.keys():
                    await self.close_connection(self.server.clients[args[1]].stream, args[1])
                else:
                    self.logger.error("Client not found")
        elif msg.startswith('say'):
            msg = msg.replace('say ', '')
            nursery.start_soon(self.message_process, "CBR", '', msg, "CBR")
        elif msg.startswith('ping'):
            if msg == 'ping':
                await self.ping_all()
            else:
                if length > 1 and args[1] in self.server.clients.keys():
                    target = args[1]
                    ping = await self.ping_test(target)
                    self.ping_log(ping, target)
                else:
                    self.logger.error("Client not found")
        elif msg == 'test':
            for thread in threading.enumerate():
                print(thread.name)
        elif msg == 'reloadall':
            nursery.start_soon(self.server.plugin_manager.reload_all_plugins)
            """
            elif msg.startswith('plg'):
                if length > 1 and args[1] in self.server.clients.keys():
                    target = args[1]
                    if self.server.clients[target].online:
                        cmd = msg.replace('cmd ' + args[1] + ' ', '')
                        await self.send_cmd(cmd, target=args[1])
                    else:
                        self.logger.error("Client not online")
                else:
                    self.logger.error("Client not found")
            """
        elif msg.startswith('cmd'):
            if length > 1 and args[1] in self.server.clients.keys():
                target = args[1]
                if self.server.clients[target].online:
                    cmd = msg.replace('cmd ' + args[1] + ' ', '')
                    await self.server.send_command(self.server.clients[args[1]].stream, cmd, receiver=args[1], target=args[1])
                else:
                    self.logger.error("Client not online")
            else:
                self.logger.error("Client not found")
        elif msg.startswith('forcedebug'):
            if length > 1:
                if args[1] in ["CBR", "plugin"]:
                    module = args[1]
                    self.logger.force_debug(module)
                elif args[1] == 'list':
                    self.logger.info(self.logger.debug_config)
                else:
                    self.logger.force_debug()
            else:
                self.logger.force_debug()
        else:
            self.logger.error('Unknown command, use help or ? for help message')


class ClientProcess(Process):
    def __init__(self, tcp_server, logger: CBRLogger):
        super().__init__(tcp_server, logger)
        self.server = tcp_server
        self.logger = logger
        self.current_client = ''
        self.ping_end = 0
        self.cancelled = False

    async def add_new_client(self, stream: trio.SocketStream, name, lib_version, client_type):
        reconnect = False
        if self.server.clients[name].online:
            self.logger.debug(f'{name} already exist, stop old connection now', "CBR")
            await self.close_connection(self.server.clients[name].stream, name)
            reconnect = True
        self.server.clients[name].stream = stream
        self.server.clients[name].online = True
        self.server.clients[name].type = client_type
        if lib_version is not None:
            self.server.clients[name].lib_version = lib_version
            lib_msg = f' with lib version: {lib_version}'
        else:
            lib_msg = ''
        if reconnect:
            self.logger.info(f"Reconnect to {name}: {lib_version}")
        else:
            self.logger.info(f'{self.current_client} connected to the server{lib_msg}')

    def client_type_check(self, msg):  # For old ChatBridge
        if 'type' not in msg.keys():
            client_type = None
        else:
            client_type = msg['type']
        return client_type

    def version_check(self, msg):
        if 'lib_version' not in msg.keys():
            lib_version = None
            self.logger.warning(f"lib version of client {msg['name']}: {str(lib_version)} is not same with server : {self.server.lib_version}")
        else:
            lib_version = msg['lib_version']
            if lib_version != self.server.lib_version:
                self.logger.warning(f"lib version of client {msg['name']}: {str(lib_version)} is not same with server : {self.server.lib_version}")
        return lib_version

    def login(self, name, password, clients):
        for i in range(len(clients)):
            if clients[i]['name'] == name:
                if clients[i]['password'] == password:
                    return True
                else:
                    self.logger.error(f"Wrong password from client {name}'s login")
                    self.logger.debug(
                        f"Client password is {password}, not same with {clients[i]['password']} in config.yml", "CBR")
        self.logger.error(f'Client {name} not found in config.yml')
        return False

    async def process_msg(self, msg, stream: trio.SocketStream, address, nursery: trio.Nursery):
        if 'action' in msg.keys():
            if msg['action'] == 'login':
                lib_version = self.version_check(msg)
                client_type = self.client_type_check(msg)
                if self.login(msg['name'], msg['password'], self.server.config.clients):
                    self.current_client = msg['name']
                    await self.add_new_client(stream, msg['name'], lib_version, client_type)
                    await self.server.send_login_result(stream, target=self.current_client)
                    self.server.register_process(self, self.current_client)
                else:
                    await self.server.send_login_result(stream, False)
                    await stream.aclose()
                    self.logger.debug(f'connection from {address} closed now', "CBR")
            elif msg['action'] == 'keepAlive':
                if msg['type'] == 'ping':
                    await self.server.send_ping(stream, True, self.current_client)
                elif msg['type'] == 'pong':
                    self.ping_end = time.time()
                    self.server.clients[self.current_client].ping_lock.cancel()
            elif msg['action'] == 'message':
                nursery.start_soon(self.message_process, msg['client'], msg['player'], msg['message'],
                                   self.current_client, 'on_message', msg)
                if msg['message'] == '##help':
                    await self.server.send_message(stream, "CBR", '', self.server.get_register_help_msg(), msg['player'])
            elif msg['action'] == 'stop':
                await self.close_connection(stream, self.current_client)
                self.logger.info(f'Connection closed from {self.current_client}')
            elif msg['action'] == 'command':
                sender = msg['sender']
                receiver = msg['receiver']
                command = msg['command']
                if msg['result']['responded']:
                    if sender == 'CBR':
                        if 'type' not in msg['result'].keys():
                            self.logger.warning(
                                f"Unknown result of sending {command} to {receiver} , maybe you should update the version of CBR client")
                            self.server.clients[self.current_client].cmd_result = None
                        elif msg['result']['type'] == 0:
                            self.server.clients[self.current_client].cmd_result = msg['result']['result']
                            self.logger.debug(
                                f"Result of Command to {receiver} finished, result: {msg['result']['result']}", "CBR")
                        elif msg['result']['type'] == 1:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Command to {receiver} failed")
                        elif msg['result']['type'] == 2:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Client {receiver} does not connected to rcon")
                        self.server.clients[self.current_client].cmd_lock.cancel()
                    elif self.server.clients[sender].online:
                        await self.server.send_msg(self.server.clients[sender].stream, json.dumps(msg), sender)
                        self.logger.info(f'Result of {command} send to {sender}')
                    else:
                        self.logger.error(f'Client {sender} is Closed')
                else:
                    if self.server.clients[receiver].online:
                        await self.server.send_msg(self.server.clients[receiver].stream, json.dumps(msg), receiver)
                        self.logger.info(f'Send Command {command} to {receiver}')
                    else:
                        self.logger.error(f'Client {receiver} not found')
            elif msg['action'] == 'api':
                sender = msg['sender']
                receiver = msg['receiver']
                plugin = msg['plugin']
                function = msg['function']
                if msg['result']['responded']:
                    if sender == 'CBR':
                        if 'type' not in msg['result'].keys():
                            self.logger.warning(
                                f"Unknown result of using api of {plugin} to {receiver} , maybe you should update the version of CBR client")
                            self.server.clients[self.current_client].cmd_result = None
                        elif msg['result']['type'] == 0:
                            self.server.clients[self.current_client].cmd_result = msg['result']['result']
                            self.logger.debug(
                                f"Result of Command to {receiver} finished, result: {msg['result']['result']}", "CBR")
                        elif msg['result']['type'] == 1:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Plugin {plugin} not find")
                        elif msg['result']['type'] == 2:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Function {function} dose not exist in {plugin}")
                        elif msg['result']['type'] == 3:
                            self.server.clients[self.current_client].cmd_result = None
                            self.logger.warning(f"Other error exist")
                        self.server.clients[self.current_client].cmd_lock.cancel()
                    elif self.server.clients[sender].online:
                        await self.server.send_msg(self.server.clients[sender].stream, json.dumps(msg), sender)
                        self.logger.info(f'Result of api use of {plugin} send to {sender}')
                    else:
                        self.logger.error(f'Client {sender} is Closed')
                else:
                    if self.server.clients[receiver].online:
                        await self.server.send_msg(self.server.clients[receiver].stream, json.dumps(msg), receiver)
                        self.logger.info(f'Result of api use of {plugin} send to {sender}')
                    else:
                        self.logger.error(f'Client {receiver} not found')
        elif self.current_client == '':
            self.logger.warning(f"Undefined connection from {stream.socket.getpeername()}")
            self.cancelled = True
