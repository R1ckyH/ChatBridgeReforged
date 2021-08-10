import json
import time
import trio
import threading

from typing import TYPE_CHECKING

from cbr.lib.logger import CBRLogger
from cbr.plugin.info import MessageInfo

if TYPE_CHECKING:
    from cbr.net.tcpserver import CBRTCPServer

help_msg = '''====================CBR====================
help/? for help msg
list for list clients in config.yml
stop/end stop server
stop (client name) stop client connection
ping ping clients
ping (client name) ping client
say msg send msg to clients
cmd (client name) send cmd to client
'''


class Process:
    def __init__(self, tcp_server: 'CBRTCPServer', logger: CBRLogger):
        self.server = tcp_server
        self.logger = logger
        self.plugin_manager = self.server.plugin_manager

    def message_formatter(self, client, player, msg):
        if player != "":
            message = f"[{client}] <{player}> {msg}"  # chat message
        else:
            message = f"[{client}] {msg}"
        return message

    async def close_connection(self, stream: trio.SocketStream, target):
        if target != '':
            self.server.clients[target]['online'] = False
            await self.server.send_msg(stream, json.dumps({'action': 'stop'}), target)
            process = self.server.clients[target]['process']
            process.cancelled = True
            if process.cancel_scope is not None:
                process.cancel_scope.cancel()
        await stream.aclose()

    async def msg_mc_server(self, msg, client_except=''):
        for i in self.server.clients.keys():
            if client_except != i and self.server.clients[i]['online']:
                stream = self.server.clients[i]['stream']
                await self.server.send_msg(stream, str(json.dumps(msg)), i)

    async def ping_test(self, target):
        client = self.server.clients[target]
        if not client['online']:
            return -2
        self.logger.debug(f'Ping to {target}')
        client['process'].ping_end = -1
        with trio.move_on_after(2) as client['pinglock']:
            start_time = time.time()
            await self.server.send_msg(client['stream'], '{"action": "keepAlive", "type": "ping"}', target)
            await trio.sleep(2)
        if client['process'].ping_end == -1:
            self.logger.debug(f'No response from {target}')
            return -1
        ping = (client['process'].ping_end - start_time) * 1000
        self.logger.debug(f'get ping result from {target}:{ping}')
        return round(ping, 1)

    def ping_log(self, ping, target):
        if ping == -2:
            self.logger.info(f'- {target}: Offline')
        elif ping == -1:
            self.logger.info(f'- {target}: No response - time = 2000ms')
        else:
            self.logger.info(f'- {target}: Alive - time = {ping}ms')

    async def message_process(self, client, player, msg, current_client):
        message = self.message_formatter(client, player, msg)
        info = MessageInfo(client, msg, player, self.logger)
        try:
            await self.plugin_manager.run_event('on_message', info)
        except Exception:
            self.logger.bug(exit_now=False, error=True)
        self.logger.info(message)
        if info._send_to_servers:
            await self.msg_mc_server(self.msg_formatter(client, player, msg), current_client)

    def msg_formatter(self, client, player, msg):
        message = {"action": "message",
                   "client": client,
                   "player": player,
                   "message": msg
                   }
        return message


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
            self.logger.info(f"- {i} : online = {self.server.clients[i]['online']}")

    async def ping_all(self):
        self.logger.debug('Start ping')
        for i in self.server.clients.keys():
            self.server.clients[i]['ping'] = await self.ping_test(i)
        self.logger.info('Ping clients:')
        for i in self.server.clients.keys():
            self.ping_log(self.server.clients[i]['ping'], i)

    def help_msg(self):
        for i in help_msg.splitlines():
            self.logger.info(i)

    async def send_cmd(self, cmd, target):
        msg = {
            "action": "command",
            "sender": "CBR",
            "receiver": target,
            "command": cmd,
            "result":
                {
                    "responded": False
                }
        }
        await self.server.send_msg(self.server.clients[target]['stream'], json.dumps(msg), target)

    async def msg_process(self, msg: str, nursery: trio.Nursery):
        args = msg.split(' ')
        length = len(args)
        if msg == 'help' or msg == '?':
            self.help_msg()
        elif msg == 'list':
            self.online_list()
        elif msg.startswith('stop') or msg == 'end':
            if msg == 'stop' or msg == 'end':
                await self.server.stop()
            else:
                if length > 1 and args[1] in self.server.clients.keys():
                    await self.close_connection(self.server.clients[args[1]]['stream'], args[1])
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
            await self.plugin_manager.reload_all_plugins()
        elif msg.startswith('cmd'):
            if length > 1 and args[1] in self.server.clients.keys():
                target = args[1]
                if self.server.clients[target]['online']:
                    cmd = msg.replace('cmd ' + args[1] + ' ', '')
                    await self.send_cmd(cmd, target=args[1])
                else:
                    self.logger.error("Client not online")
            else:
                self.logger.error("Client not found")
        elif msg == 'forcedebug':
            self.logger.forcedebug()
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

    async def add_new_client(self, stream: trio.SocketStream, name, libversion, client_type):
        reconnect = False
        if self.server.clients[name]['online']:
            self.logger.debug(f'{name} already exist, stop old connection now')
            await self.close_connection(self.server.clients[name]['stream'], name)
            reconnect = True
        self.server.clients[name]['stream'] = stream
        self.server.clients[name]['online'] = True
        self.server.clients[name]['type'] = client_type
        if libversion is not None:
            libversion = f' with lib version: {libversion}'
        else:
            libversion = ''
        if reconnect:
            self.logger.info(f"Reconnect to {name}{libversion}")
        else:
            self.logger.info(f'{self.current_client} connected to the server{libversion}')

    def client_type_check(self, msg):
        if 'type' not in msg.keys():
            client_type = "None"
        else:
            client_type = msg['type']
        return client_type

    def version_check(self, msg):
        if 'libversion' not in msg.keys():
            libversion = None
            self.logger.warning(f"lib version of client {msg['name']}: {str(libversion)} is not same with server : {self.server.libversion}")
        else:
            libversion = msg['libversion']
            if libversion != self.server.libversion:
                self.logger.warning(f"lib version of client {msg['name']}: {str(libversion)} is not same with server : {self.server.libversion}")
        return libversion

    def login(self, name, password, clients):
        for i in range(len(clients)):
            if clients[i]['name'] == name:
                if clients[i]['password'] == password:
                    return True
                else:
                    self.logger.error(f"Wrong password from client {name}'s login")
                    self.logger.debug(
                        f"Client password is {password}, not same with {clients[i]['password']} in config.yml")
                    return False
        self.logger.error(f'Client {name} not found in config.yml')
        return False

    async def process_msg(self, msg, stream: trio.SocketStream, address, nursery: trio.Nursery):
        if 'action' in msg.keys():
            if msg['action'] == 'login':
                libversion = self.version_check(msg)
                client_type = self.client_type_check(msg)
                if self.login(msg['name'], msg['password'], self.server.config_data['clients']):
                    self.current_client = msg['name']
                    await self.add_new_client(stream, msg['name'], libversion, client_type)
                    await self.server.send_msg(stream, '{"action": "result","result": "login success"}',
                                               self.current_client)
                    self.server.register_process(self, self.current_client)
                else:
                    await self.server.send_msg(stream, '{"action": "result","result": "login fail"}')
                    await stream.aclose()
                    self.logger.debug(f'connection from {address} closed now')
            elif msg['action'] == 'keepAlive':
                if msg['type'] == 'ping':
                    await self.server.send_msg(stream, '{"action": "keepAlive", "type": "pong"}', self.current_client)
                elif msg['type'] == 'pong':
                    self.ping_end = time.time()
                    self.server.clients[self.current_client]['pinglock'].cancel()
            elif msg['action'] == 'message':
                nursery.start_soon(self.message_process, msg['client'], msg['player'], msg['message'],
                                   self.current_client)
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
                            self.server.clients[self.current_client]['cmdresult'] = None
                        elif msg['result']['type'] == 0:
                            self.server.clients[self.current_client]['cmdresult'] = msg['result']['result']
                            self.logger.debug(
                                f"Result of Command to {receiver} finished, result: {msg['result']['result']}")
                        elif msg['result']['type'] == 1:
                            self.server.clients[self.current_client]['cmdresult'] = None
                            self.logger.warning(f"Command to {receiver} failed")
                        elif msg['result']['type'] == 2:
                            self.server.clients[self.current_client]['cmdresult'] = None
                            self.logger.warning(f"Client {receiver} does not connected to rcon")
                        self.server.clients[self.current_client]['cmdlock'].cancel()
                    elif self.server.clients[sender]['online']:
                        await self.server.send_msg(self.server.clients[sender]['stream'], json.dumps(msg), sender)
                        self.logger.info(f'Result of {command} send to {sender}')
                    else:
                        self.logger.error(f'Client {sender} is Closed')
                else:
                    if self.server.clients[receiver]['online']:
                        await self.server.send_msg(self.server.clients[receiver]['stream'], json.dumps(msg), receiver)
                        self.logger.info(f'Send Command {command} to {receiver}')
                    else:
                        self.logger.error(f'Client {receiver} not found')
        elif self.current_client == '':
            self.logger.warning(f"Unknown connection from {stream.socket.getpeername()}")
            self.cancelled = True
