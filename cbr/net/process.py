import asyncio
import json

from cbr.lib.logger import CBRLogger
#from cbr.cbr_server import CBRServer

class Process:
    def __init__(self, tcp_server, logger : CBRLogger):
        self.server = tcp_server
        self.logger = logger

    def add_new_client(self, reader, writer, name):
        client = {
            name : {
                'reader' : reader,
                'writer' : writer
            }
        }
        self.server.client_list.update(client)
        self.server.client_name.append(name)

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

    async def proceess_msg(self, msg, reader : asyncio.StreamReader, writer : asyncio.StreamWriter, addr):
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
                if msg['player'] != "":
                    message = f"[{msg['client']}] <{msg['player']}> {msg['message']}"  # chat message
                else:
                    message = f"[{msg['client']}] {msg['message']}"
                self.logger.info(message)
                await self.msg_mc_server(msg, self.current_client)
    
    
    async def msg_mc_server(self, msg, client_except = ''):
        for i in range(len(self.server.client_name)):
            if client_except != self.server.client_name[i]:
                writer = self.server.client_list[self.server.client_name[i]]['writer']
                await self.server.send_msg(writer, str(json.dumps(msg)), self.server.client_name[i])
                self.logger.debug(f"Send {msg} to {self.server.client_name[i]}")


LibVersion = 'v20200116'
'''
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