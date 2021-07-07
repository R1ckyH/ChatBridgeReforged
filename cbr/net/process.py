import asyncio
import json
import time

from cbr.lib.logger import CBRLogger
#from cbr.net.tcpserver import CBRTCPServer

help_msg = '''====================CBR====================
help/? for help msg
list for list clients in config.yml
stop/end stop server
stop (client name) stop client connection
ping ping clients
ping (client name) ping client
say msg send msg to clients
'''


class Process:
    def __init__(self, tcp_server, logger : CBRLogger):
        self.server = tcp_server
        self.logger = logger
        self.end = 0

    def message_formater(self, client, player, msg):
        if player != "":
            message = f"[{client}] <{player}> {msg}"  # chat message
        else:
            message = f"[{client}] {msg}"
        return message

    async def close_connection(self, writer : asyncio.StreamWriter, target):
        self.server.clients[target]['online'] = False
        if not writer.is_closing():
            await self.server.send_msg(writer, json.dumps({'action' : 'stop'}), target)
            writer.close()
            await writer.wait_closed()

    async def msg_mc_server(self, msg, client_except = ''):
        for i in self.server.clients.keys():
            if client_except != i and self.server.clients[i]['online'] == True:
                writer = self.server.clients[i]['writer']
                await self.server.send_msg(writer, str(json.dumps(msg)), i)

    async def ping_test(self, target):
        await asyncio.sleep(0.000001)#fuck asyncio again
        client = self.server.clients[target]
        if not client['online']:
            return -2
        self.logger.debug(f'Ping to {target}')
        start_time = time.time()
        await self.server.send_msg(client['writer'], '{"action": "keepAlive", "type": "ping"}', target)
        await self.ping_result(client['process'])
        self.logger.debug(f'get ping result from {target}')
        if self.end == -1:
            self.logger.debug(f'No response from {target}')
            return -1
        return round((self.end - start_time)*1000, 1)

    async def ping_result(self, process):
        process.ping_end = 0
        start = time.time()
        while time.time() - start <= 2:
            await asyncio.sleep(0.000001)#fuck asyncio
            if process.ping_end != 0:
                self.end = process.ping_end
                process.ping_end = 0
                return
        self.end = -1

    def ping_log(self, ping, target):
        if ping == -2:
            self.logger.info(f'- {target}: Offline')
        elif ping == -1:
            self.logger.info(f'- {target}: No response - time = 2000ms')
        else:
            self.logger.info(f'- {target}: Alive - time = {ping}ms')


class ServerProcess(Process):
    def __init__(self, tcp_server, logger : CBRLogger):
        super().__init__(tcp_server, logger)
        self.server = tcp_server
        self.logger = logger

    async def server_msg(self, msg):
        message = {"action": "message",
            "client": "CBR",
            "player": "",
            "message": f"{msg}"
        }
        msg = self.message_formater("CBR", '', msg)
        self.logger.info(msg)
        await self.msg_mc_server(message)

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

    async def msg_process(self, msg : str):
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
                    await self.close_connection(self.server.clients[args[1]]['writer'], args[1])
                else:
                    self.logger.info("Client not found")
        elif msg.startswith('say'):
            msg = msg.replace('say ', '')
            await self.server_msg(msg)
        elif msg.startswith('ping'):
            if msg == 'ping':
                await self.ping_all()
            else:
                if length > 1 and args[1] in self.server.clients.keys():
                    target = args[1]
                    ping = await self.ping_test(target)
                    self.ping_log(ping, target)
                else:
                    self.logger.info("Client not found")
        elif msg == 'forcedebug':
            self.logger.forcedebug()
        else:
            self.logger.info('Unknown command, use help or ? for help message')


class ClientProcess(Process):
    def __init__(self, tcp_server, logger : CBRLogger):
        super().__init__(tcp_server, logger)
        self.server = tcp_server
        self.logger = logger
        self.current_client = ''
        self.ping_end = 0

    async def add_new_client(self, reader, writer, name):
        reconnect = False
        if self.server.clients[name]['online']:
            self.logger.debug(f'{name} already exist, stop old connection now')
            await self.close_connection(self.server.clients[name]['writer'], name)
            reconnect = True
        self.server.clients[name]['reader'] = reader
        self.server.clients[name]['writer'] = writer
        self.server.clients[name]['online'] = True
        if reconnect:
            self.logger.info(f"Reconnect to {name}")
        else:
            self.logger.info(f'{self.current_client} connected to the server')

    def login(self, name, password, clients):
        for i in range(len(clients)):
            if clients[i]['name'] == name:
                if clients[i]['password'] == password:
                    return True
                else:
                    self.logger.error(f"Wrong password from client{name}'s login")
                    self.logger.debug(f"Client password is {password}, not same with {clients[i]['password']} in config.yml")
                    return False
        self.logger.error('Client not found in config.yml')
        return False

    async def process_msg(self, msg, reader : asyncio.StreamReader, writer : asyncio.StreamWriter, addr):
        if 'action' in msg.keys():
            if msg['action'] == 'login':
                if self.login(msg['name'], msg['password'], self.server.config_data['clients']):
                    self.current_client = msg['name']
                    await self.add_new_client(reader, writer, msg['name'])
                    await self.server.send_msg(writer, '{"action": "result","result": "login success"}')
                    self.server.register_process(self, self.current_client)
                else:
                    await self.server.send_msg(writer, '{"action": "result","result": "login fail"}')
                    writer.close()
                    self.logger.debug(f'Asyncio writer from {addr} closed now')
            elif msg['action'] == 'keepAlive':
                if msg['type'] == 'ping':
                    await self.server.send_msg(writer, '{"action": "keepAlive", "type": "pong"}')
                elif msg['type'] == 'pong':
                    self.ping_end = time.time()
            elif msg['action'] == 'message':
                message = self.message_formater(msg['client'], msg['player'], msg['message'])
                self.logger.info(message)
                await self.msg_mc_server(msg, self.current_client)
            elif msg['action'] == 'stop':
                await self.close_connection(writer, self.current_client)
                self.logger.info(f'Connection closed from {self.current_client}')
            elif msg['action'] == 'command':
                sender = msg['sender']
                recevier = msg['receiver']
                command = msg['command']
                if msg['result']['responded']:
                    if(self.server.clients[sender]['online']):
                        await self.server.send_msg(self.server.clients[sender]['writer'], json.dumps(msg), sender)
                        self.logger.info(f'Result of {command} send to {sender}')
                    else:
                        self.logger.error(f'Client {sender} is Closed')
                else:
                    if(self.server.clients[recevier]['online']):
                        await self.server.send_msg(self.server.clients[recevier]['writer'], json.dumps(msg), recevier)
                        self.logger.info(f'Send Command {command} to {recevier}')
                    else:
                        self.logger.debug(f'Client {recevier} not found')
        elif self.current_client == '':
            self.logger.warning(f"Unknown connection from {writer.get_extra_info('peername')}")
            writer.close()


LibVersion = 'v20200116'
'''
plugin:##CBR
数据包格式：
4 byte长的unsigned int代表长度，随后是所指长度的加密字符串，解密后为一个json
json格式：
返回结果： server -> client
{
	"action": "result",
	"result": "RESULT"
}
开始连接： client -> server
{
	"action": "login",
	"name": "ClientName",
	"password": "ClientPassword"
}
返回登录情况：server -> client 返回结果
	"result": login success" // 成功
	"result": login fail" // 失败

传输信息： client <-> server
{
	"action": "message",
	"client": "CLIENT_NAME",
	"player": "PLAYER_NAME",
	"message": "MESSAGE_STRING"
}

结束连接： client <-> server
{
	"action": "stop"
}

调用指令：
clientA -> server -> clientB
{
	"action": "command",
	"sender": "CLIENT_A_NAME",
	"receiver": "CLIENT_B_NAME",
	"command": "COMMAND",
	"result": 
	{
		"responded": false
	}
}
clientA <- server <- clientB
{
	"action": "command",
	"sender": "CLIENT_A_NAME",
	"receiver": "CLIENT_B_NAME",
	"command": "COMMAND",
	"result": 
	{
		"responded": true,
		...
	}
}
	[!!stats]
	"result": 
	{
		"responded": xxx,
		"type": int,  // 0: good, 1: stats not found, 2: stats helper not found
		"stats_name": "aaa.bbb", // if good
		"result": "STRING" // if good
	}
	[!!online]
	"result": 
	{
		"responded": xxx,
		"type": int,  // 0: good, 1: rcon query fail, 2: rcon not found
		"result": "STRING" // if good
	}

保持链接
sender -> receiver
{
	"action": "keepAlive",
	"type": "ping"
}
receiver -> sender
{
	"action": "keepAlive",
	"type": "pong"
}
等待KeepAliveTimeWait秒无响应即可中断连接
'''