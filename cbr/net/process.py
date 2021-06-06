import asyncio
import json

from cbr.lib.logger import CBRLogger
#from cbr.cbr_server import CBRServer

help_msg = '''====================CBR====================
help/? for help msg
list for list clients in config.yml
stop/end stop server
stop (client name) stop client connection
say msg send msg to clients
'''


class Process:
    def __init__(self, tcp_server, logger : CBRLogger):
        self.server = tcp_server
        self.logger = logger
        self.current_client = ''

    def add_new_client(self, reader, writer, name):
        self.server.clients[name].update({'reader' : reader, 'writer' : writer})
        self.server.clients[name]['online'] = True

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

    def message_formater(self, client, player, msg):
        if player != "":
            message = f"[{client}] <{player}> {msg}"  # chat message
        else:
            message = f"[{client}] {msg}"
        return message

    async def process_msg(self, msg, reader : asyncio.StreamReader, writer : asyncio.StreamWriter, addr):
        if 'action' in msg.keys():
            if msg['action'] == 'login':
                if self.login(msg['name'], msg['password'], self.server.config_data['clients']):
                    self.add_new_client(reader, writer, msg['name'])
                    self.current_client = msg['name']
                    await self.server.send_msg(writer, '{"action": "result","result": "login success"}')
                    self.logger.info(f'{self.current_client} connected to the server')
                else:
                    await self.server.send_msg(writer, '{"action": "result","result": "fail"}')
                    writer.close()
                    self.logger.debug(f'Asyncio writer from {addr} closed now')
            elif msg['action'] == 'keepAlive':
                await self.server.send_msg(writer,'{"action": "keepAlive", "type": "pong"}')
            elif msg['action'] == 'message':
                message = self.message_formater(msg['client'], msg['player'], msg['message'])
                if msg['player'] != "":
                    message = f"[{msg['client']}] <{msg['player']}> {msg['message']}"  # chat message
                else:
                    message = f"[{msg['client']}] {msg['message']}"
                self.logger.info(message)
                await self.msg_mc_server(msg, self.current_client)
            elif msg['action'] == 'stop':
                await self.close_connection(writer, self.current_client)
            elif msg['action'] == 'command':
                sender = msg['sender']
                recevier = msg['receiver']
                command = msg['command']
                if msg['result']['responded']:
                    if(self.server.clients[sender]['online']):
                        await self.server.send_msg(self.server.clients[sender]['writer'], json.dumps(msg), sender)
                        self.logger.info(f'{command} result send to {sender}')
                    else:
                        self.logger.error(f'Client {sender} is Closed')
                else:
                    if(self.server.clients[recevier]['online']):
                        await self.server.send_msg(self.server.clients[recevier]['writer'], json.dumps(msg), recevier)
                        self.logger.info(f'Send Command {command} to {recevier}')
                    else:
                        self.logger.debug(f'Client {recevier} not found')

    async def close_connection(self, writer, client):
        self.server.clients[client]['online'] = False
        if not writer.is_closing():
            await self.server.send_msg(writer, json.dumps({'action' : 'stop'}), client)
            writer.close()

    async def msg_mc_server(self, msg, client_except = ''):
        for i in self.server.clients.keys():
            if client_except != i and self.server.clients[i]['online'] == True:
                writer = self.server.clients[i]['writer']
                await self.server.send_msg(writer, str(json.dumps(msg)), i)

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

    async def msg_process(self, msg):
        if msg == 'help' or msg == '?':
            for i in help_msg.splitlines():
                self.logger.info(i)
        elif msg == 'list':
            self.online_list()
        elif msg.startswith('stop') or msg == 'end':
            if msg == 'stop' or msg == 'end':
                await self.server.stop()
            else:
                args = msg.split(' ')
                if args[1] in self.server.clients.keys():
                    await self.close_connection(self.server.clients[args[1]]['writer'], args[1])
                else:
                    self.logger.info("Client not found")
        elif msg.startswith('say'):
            msg = msg.replace('say ', '')
            await self.server_msg(msg)
        else:
            self.logger.info('Unknown command, use help or ? for help message')


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