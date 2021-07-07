import re
import os
import sys
import time
import json
import trio
import struct
import logging
import threading

from ruamel import yaml
from typing import Optional
from Crypto.Cipher import AES
from mcdreforged.api.all import *
from binascii import b2a_hex, a2b_hex
from mcdreforged.utils.logger import MCDReforgedLogger

config_file = 'config/ChatBridgeReforged_client.yml'
log_file = 'logs/ChatBridgeReforged_Client_mc.log'

debug_mode = False
ping_time = 60
client = None
prefix = '!!CBR'

default_config = {
	"name": "testClient",
	"password": "testPassword",
	"server_hostname": "localhost",
	"server_port": 30001,
	"aes_key": "ThisIstheSecret"
}


def rtext_cmd(txt, msg, cmd, color = None, styles = None) -> RTextBase:
    return RText(txt, color, styles).h(msg).c(RAction.run_command, cmd)


PLUGIN_METADATA = {
    'id': 'chatbridgereforged_client_mc',
    'version': '0.0.1-Alpha-006-pre3', # 版本号屁股后面加了1
    'name': 'ChatBridgeReforged Client', # 改了名称, 让它更像一个名称, id没改
    'description': 'Reforged of ChatBridge, Client for normal mc server.',
    'author': 'ricky',
    'link': 'https://github.com/rickyhoho/ChatBridgeReforged',
    'dependencies': {
        'mcdreforged': '>=1.3.0'
    }
}

# 重写的Logger, 里面所有用到logger的地方都改了
class CBRLogger(MCDReforgedLogger):
    DEFAULT_NAME = 'CBR'
    
    def debug(self, *args):
        if debug_mode:
            super(MCDReforgedLogger, self).debug(*args)

    def set_file(self, file_name):
        if not os.path.isdir(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))
        if not os.path.isfile(file_name):
            with open(file_name, 'w', encoding='UTF-8') as f:
                f.write('')
        if self.file_handler is not None:
            self.removeHandler(self.file_handler)
        self.file_handler = logging.FileHandler(file_name, encoding='UTF-8')
        self.file_handler.setFormatter(self.FILE_FMT)
        self.addHandler(self.file_handler)

# 重写的插件帮助
def show_help(info: Optional[Info] = None):
    help_msg = '''------ MCDR {1} v{2} -------
§7{0} help §r显示帮助信息
§7{0} start §r启动ChatBridge Reforged客户端
§7{0} stop §r关闭ChatBridge Reforged客户端
§7{0} reload §r重载ChatBridge Reforged客户端配置
§7{0} restart §r重启ChatBridge Reforged客户端
§7{0} ping §r检测至ChatBridge Reforged服务端的延迟
'''.strip().format(prefix, PLUGIN_METADATA['name'], PLUGIN_METADATA['version'])
    help_msg_rtext = RTextList()
    for line in help_msg.splitlines():
        result = re.search(r'(?<=§7)!!loc[\w ]*(?=§)', line)
        if result is not None:
            help_msg_rtext.append(RText(line).c(RAction.suggest_command, result.group()).h('点击以填入 §7{}§r'.format(result.group())))
        else:
            help_msg_rtext.append(line)
    if isinstance(info, Info):
        info.get_server().reply(info, help_msg_rtext)
    else:
        logger.info(str(help_msg_rtext))


def print_msg(msg, num, info: Info = None, src : CommandSource = None, server : ServerInterface = None):
    if src != None:
        server = src.get_server()
        info = src.get_info()
    if num == 0:
        server.say(msg)
        logger.info(str(msg))
    elif num == 1:
        server.tell(info.player, msg)
        logger.info(str(msg))

# 重写了config加载, yaml带注释
def load_config():
    config = None
    need_save = False
    if not os.path.isdir(os.path.dirname(config_file)):
        os.makedirs(os.path.dirname(config_file))
        logger.info(f'Created {os.path.dirname(config_file)}')

    if not os.path.isfile(config_file):
        if config is None:
            config = default_config.copy()
        need_save = True
        logger.info('Config file not found, generated')
    
    if config is None:
        with open(config_file, 'r', encoding='UTF-8') as f:
            config = yaml.round_trip_load(f)
        if config == None:
            try:
                os.remove(config_file)
            except:
                pass
            config = default_config
            need_save = True
            logger.info('Invalid config file, regenerated')
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
                logger.info(f'Invalid config key {key}, using default value {value}')
                need_save = True
  
    if need_save:
        with open(config_file, 'w', encoding='UTF-8') as f:
            yaml.round_trip_dump(config, f, allow_unicode = True)

    logger.info('Loaded config file')
    return config


class AESCryptor():
	# key and text needs to be utf-8 str in python2 or str in python3
    # by ricky, most of the code keep cause me dose not want to change this part
    def __init__(self, key, mode=AES.MODE_CBC):
        self.key = self.__to16Length(key)
        self.mode = mode

    def __to16Length(self, text):
        if sys.version_info.major == 3:
            text = bytes(text, encoding="utf-8")
        return text + (b'\0' * ((16 - (len(text) % 16)) % 16))

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        text = self.__to16Length(text)
        result = b2a_hex(cryptor.encrypt(text))
        if sys.version_info.major == 3:
            result = str(result, encoding='utf-8')
        return result

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        if sys.version_info.major == 3:
            text = bytes(text, encoding='utf-8')
        try:
            result = cryptor.decrypt(a2b_hex(text))
        except TypeError as err:
            logger.info('TypeError when decrypting text', True)
            logger.info('text =', text, True)
            raise err
        except ValueError as err:
            logger.info(err.args, True)
            logger.info('len(text) =' + str(len(text)), True)
            raise err
        if sys.version_info.major == 3:
            try:
                result = str(result, encoding='utf-8')
            except UnicodeDecodeError:
                logger.info('error at decrypt string conversion', True)
                logger.info('raw result = ' + str(result), True)
                result = str(result, encoding='ISO-8859-1')
                logger.info('ISO-8859-1 = ' + str(result), True)
        return result.rstrip('\0')


class network(AESCryptor):
    def __init__(self, key):
        super().__init__(key)
        self.connected = False

    async def receive_msg(self, client_stream : trio.SocketStream, addr):
        data = await client_stream.receive_some(4)
        if len(data) < 4:
            return '{}'
        length = struct.unpack('I', data)[0]
        msg = await client_stream.receive_some(length)
        msg = str(msg, encoding='utf-8')
        try:
            msg = self.decrypt(msg)
        except:
            return '{}'
        logger.info(f"Received {msg!r} from {addr!r}", debug = True)
        return msg

    async def send_msg(self, client_stream : trio.SocketStream, msg ,target = ''):
        if not client.connected:
            logger.info("Not connected to the server", debug = True)
            return
        if target != '':
            target = 'to ' + target
        logger.info(f"Send: {msg!r} {target}", debug = True)
        msg = self.encrypt(msg)
        if sys.version_info.major == 3:
            msg = bytes(msg, encoding='utf-8')
        msg = struct.pack('I', len(msg)) + msg
        await client_stream.send_all(msg)


class ClientProcess:
    def __init__(self, client):
        self.client = client
        self.end = 0

    def message_formater(self, client, player, msg):
        if player != "":
            message = f"[{client}] <{player}> {msg}"  # chat message
        else:
            message = f"[{client}] {msg}"
        return message

    def msg_json_formater(self, client, player, msg):
        a = {
                "action": "message",
                "client": client,
                "player": player,
                "message": msg
            }
        return json.dumps(a)

    async def ping_test(self):
        await trio.sleep(0.000001)#for async
        if not self.client.connected:
            return -2
        logger.info(f'Ping to server', debug = True)
        start_time = time.time()
        await self.client.send_msg(self.client.client_stream, '{"action": "keepAlive", "type": "ping"}', 'server')
        await self.ping_result()
        logger.info(f'get ping result from server', debug = True)
        if self.end == -1:
            logger.info(f'No response from server', debug = True)
            return -1
        return round((self.end - start_time)*1000, 1)

    async def ping_result(self):
        self.end = 0
        start = time.time()
        while time.time() - start <= 2:
            await trio.sleep(0.000001)#for async
            if self.end != 0:
                return
        self.end = -1

    def ping_log(self, ping):
        if ping == -2:
            logger.info(f'- Offline')
        elif ping == -1:
            logger.info(f'- No response - time = 2000ms')
        else:
            logger.info(f'- Alive - time = {ping}ms')


    async def process_msg(self, msg, client_stream : trio.SocketStream, addr):
        if 'action' in msg.keys():
            if msg['action'] == 'result':
                if msg['result'] == 'login success':
                    logger.info("Login Success")
                else:
                    logger.info("Login in fail", error = True)
            elif msg['action'] == 'keepAlive':
                if msg['type'] == 'ping':
                    await self.client.send_msg(client_stream, '{"action": "keepAlive", "type": "pong"}')
                elif msg['type'] == 'pong':
                    self.end = time.time()
            elif msg['action'] == 'message':
                message = self.message_formater(msg['client'], msg['player'], msg['message'])
                logger.info(message)
            elif msg['action'] == 'stop':
                await self.client.close_connection()
                logger.info(f'Connection closed from server')
            elif msg['action'] == 'command':
                sender = msg['sender']
                recevier = msg['receiver']
                command = msg['command']
                if msg['result']['responded']:
                    if(self.server.clients[sender]['online']):
                        await self.server.send_msg(self.server.clients[sender]['writer'], json.dumps(msg), sender)
                        logger.info(f'Result of {command} send to {sender}')
                    else:
                        logger.info(f'Client {sender} is Closed', error = True)
                else:
                    if(self.server.clients[recevier]['online']):
                        await self.server.send_msg(self.server.clients[recevier]['writer'], json.dumps(msg), recevier)
                        logger.info(f'Send Command {command} to {recevier}')
                    else:
                        logger.info(f'Client {recevier} not found', debug = True)

class CBRTCPClient(network):
    def __init__(self, config_data):
        self.setup(config_data)

    def setup(self, config_data):
        self.client_stream = False
        self.connected = False
        self.server = None
        self.cancelled = False
        super().__init__(config_data['aes_key'])
        self.ip = config_data['ip_address']
        self.port = config_data['port']
        self.name = config_data['name']
        self.password = config_data['password']
        self.process = ClientProcess(self)
    
    def trystart(self):
        if self.connected == False:
            threading.Thread(target = trio.run, name = 'CBR', args=(self.start,), daemon = True).start()
        else:
            logger.info("Already Connected to server", debug = True)
    
    async def start(self):
        self.cancelled = False
        logger.info(f"Connecting to {self.ip}:{self.port}")
        self.client_stream = await trio.open_tcp_stream(self.ip, self.port)
        self.connected = True
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_echo)
        
    def trystop(self):
        if self.connected == True:
            trio.run(self.close_connection)
            logger.info("Closed connection")
        else:
            logger.info("Connection already closed", error = True)

    async def close_connection(self, target = ''):
        if not self.client_stream == None and self.connected == True:
            await self.send_msg(self.client_stream, json.dumps({'action' : 'stop'}), target)
            await self.client_stream.aclose()
            self.cancelled = True
            self.cancel_scope.cancel()
            logger.info("Connection closed to server", debug = True)
        self.connected = False

    def reload(self):
        logger.info("Reload ChatBridgeReforced Client now")
        trio.run(self.close_connection)
        config = load_config()
        self.setup(config)
        logger.info("Reload Config", debug = True)
        self.trystart()
    
    async def keep_alive(self):
        while not self.client_stream == None and self.connected:
            logger.info("keep alive", debug = True)
            for i in range(ping_time):
                await trio.sleep(1)
                if not self.connected:
                    return
            ping = json.dumps({"action": "keepAlive", "type": "ping"})
            if self.connected:
                await self.send_msg(self.client_stream, ping)

    async def login(self, name, password):
        msg = {"action": "login", "name": name, "password": password}
        await self.send_msg(self.client_stream, json.dumps(msg))

    async def client_process(self):
        try:
            msg = await self.receive_msg(self.client_stream, self.ip)
        except trio.Cancelled and trio.ClosedResourceError:
            self.connected = False
            await trio.sleep(0.0005)
            logger.info("Stop Receive message", debug = True)
            return
        msg = json.loads(msg)
        await self.process.process_msg(msg, self.client_stream, self.ip)

    async def handle_echo(self):
        await self.login(self.name, self.password)
        threading.Thread(target = trio.run, name = 'CBRPing', args = (self.keep_alive,), daemon = True).start()
        while self.client_stream != None and self.connected == True:
            try:
                with trio.fail_after(120) as self.cancel_scope:
                    await self.client_process()
            except trio.TooSlowError:
                await trio.sleep(0.0005)
                if not self.cancelled:
                    logger.info('Connection time out!', error = True)
                    logger.info('Closed connection to server', debug = True)
                else:
                    logger.info("Cancel Process", debug = True)
                break
            except:
                logger.debug()
                break
        self.connected = False

'''if __name__ == '__main__':
    config = load_config()
    client = CBRTCPClient(config)
    client.trystart()
'''

# 这里也加了logger
if __name__ == '__main__':
    logger = CBRLogger(None)
    logger.set_file(log_file)
    config = load_config()
    client = CBRTCPClient(config)
    client.trystart()
    while True:
        a = input()
        if a == 'help':
            show_help() # 当可选参数info不输入时就是直接print
        elif a == 'stop':
            client.trystop()
        elif a == 'start':
            client.trystart()
        elif a == 'ping':
            ping = trio.run(client.process.ping_test)
            client.process.ping_log(ping)
        elif a == 'reload':
            client.reload()
        elif a == 'forcedebug':
            debug_mode = not debug_mode
            logger.info(f'forcedebug: {debug_mode}')
        elif a == 'test':
            for thread in threading.enumerate(): 
                print(thread.name)
        elif client.connected:
            trio.run(client.send_msg, client.client_stream, client.process.msg_json_formater(config['name'], '', a))
        else:
            logger.info("Not Connected")

@new_thread("CBRProcess")
def on_info(server : ServerInterface, info : Info):
    global debug_mode
    if info.is_user:
        args = info.content.strip().split(' ')
        clen = len(args)
        
        # 重写了解析指令，不放过一个打错指令的坏孩子
        if args[0] == prefix:
            info.cancel_send_to_server()
            # !!CBR [help] 插件帮助重写了
            if clen == 0 or bool(clen == 1 and args[1] == 'help'):
                show_help(info)
            # !!CBR start
            elif clen == 1 and args[1] == 'start':
                client.trystart()
            # !!CBR stop
            elif clen == 1 and args[1] == 'stop':
                client.trystop()
            # !!CBR reload
            elif clen == 1 and args[1] == 'reload':
                client.reload()
            # !!CBR restart
            elif clen == 1 and args[1] == 'restart':
                client.trystop()
                client.trystart()
            # !!CBR ping
            elif clen == 1 and args[1] == 'ping':
                ping = trio.run(client.process.ping_test)
                client.process.ping_log(ping)
            # !!CBR forcedebug
            elif clen == 1 and args[1] == 'forcedebug':
                debug_mode = not debug_mode
                logger.info(f'forcedebug: {debug_mode}')
            # !!CBR test
            elif clen == 1 and args[1] == 'test':
                for thread in threading.enumerate(): 
                    logger.info(thread.name)

            else:
                server.reply(info, 'Command not found')

    elif info.is_player:
        if client == None:
            return
        client.trystart()
        if client.connected:
            trio.run(client.send_msg, client.client_stream, client.process.msg_json_formater(client.name, info.player, info.content))



def on_player_joined(server, name, info = None):
    client.trystart()
    trio.run(client.send_msg, client.client_stream, client.process.msg_json_formater(client.name, '', name + ' joined ' + client.name))


def on_player_left(server, name, info = None):
    client.trystart()
    trio.run(client.send_msg, client.client_stream, client.process.msg_json_formater(client.name, '', name + ' left ' + client.name))


def on_unload(server):
    print('unload')
    trio.run(client.close_connection)
    print(client.connected)

# 新增了注册logger, 还有global不写在函数第一行是什么臭习惯???
@new_thread("CBRload")
def on_load(server, old):
    global client, logger
    if old != None:
        old.client.trystop()
    logger = CBRLogger(server)
    logger.set_file(log_file)
    time.sleep(1)
    print('load')
    config = load_config()
    client = CBRTCPClient(config)
    client.trystart()
    client.server = server