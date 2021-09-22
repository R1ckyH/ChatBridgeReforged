"""
data pack here
Credit: Fallen-Breath https://github.com/Fallen-Breath https://github.com/TISUnion/ChatBridge
"""
import sys

# Config
# TODO: split mcdr and mc command
# TODO: Rtext
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
    "lib_version" : "Version"
    "type" : "ClientType"
}
返回登录情况：server -> client 返回结果
    "result": login success" // 成功
    "result": login fail" // 失败

传输信息： client <-> server
{
    "action": "message",
    "client": "CLIENT_NAME",
    "player": "PLAYER_NAME",
    "receiver": "PLAYER_NAME",
    "message": "MESSAGE_STRING"
}

结束连接： client <-> server
{
    "action": "stop"
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
    [list] //example
    "command": "list"
    "result":
    {
        "responded": xxx,
        "type": int,  // 0: good, 1: rcon query fail, 2: rcon not found
        "result": "STRING" // if good
    }

API USE
clientA -> server -> clientB
{
    "action": "api",
    "sender": "CLIENT_A_NAME",
    "receiver": "CLIENT_B_NAME",
    "plugin": "PLUGIN_ID",
    "function": "FUNCTION_NAME"
    "keys":
    [
        "KEY1", "KEY2", True // only support string and bool
        // must with order
    ]
    "result":
    {
        "responded": false
    }
}
clientA <- server <- clientB
{
    "action": "api",
    "sender": "CLIENT_A_NAME",
    "receiver": "CLIENT_B_NAME",
    "plugin": "PLUGIN_ID",
    "function": "FUNCTION_NAME"
    "key":
    [
        ...
    ]
    "result": 
    {
        "responded": true,
        "type": int,  // 0: good, 1: plugin not found, 2: api not found 3: other error
        "result": "STRING" // if good
    }
}
'''

if __name__ == '__main__':
    sys.exit()
