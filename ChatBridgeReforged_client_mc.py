import trio
import json
import os
import struct
import sys
import threading
import time
import traceback

from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES
from datetime import datetime
from mcdreforged.api.all import *

debug_mode = False
ping_time = 60
config_file = 'config/ChatBridgeReforged_client.json'
client = None
prefix = '!!CBR'


def rtext_cmd(txt, msg, cmd):
    return RText(txt).h(msg).c(RAction.run_command, cmd)

help_msg = '''§b-----------§fChatBridgeReforged_Client§b-----------§r
''' + rtext_cmd('!!CBR help §ashow help message§r', 'click me to show help message', prefix) + '''
''' + rtext_cmd('!!CBR start §astart ChatBridgeReforged client§r', 'Click me to start', '!!CBR start') + '''
''' + rtext_cmd('!!CBR stop §astop ChatBridgeReforged client§r', 'Click me to stop', '!!CBR stop') + '''
''' + rtext_cmd('!!CBR reload §areload ChatBridgeReforged client§r', 'Click me to reload', '!!CBR reload') + '''
''' + rtext_cmd('!!CBR restart §arestart ChatBridgeReforged client§r', 'Click me to restart', '!!CBR restart') +  '''
''' + rtext_cmd('!!CBR ping §aping ChatBridgeReforged server§r', 'Click me to ping server', '!!CBR ping') +  '''
§b-----------------------------------------------§r'''  

PLUGIN_METADATA = {
    'id': 'chatbridgereforged_client_mc',
    'version': '0.0.1-Alpha-006-pre2',
    'name': 'ChatBridgeReforged_Client_mc',
    'description': 'Reforged of ChatBridge, Client for normal mc server.',
    'author': 'ricky',
    'link': 'https://github.com/rickyhoho/ChatBridgeReforged',
    'dependencies': {
        'mcdreforged': '>=1.3.0'
    }
}


def out_log(msg : str, error = False, debug = False):
    msg = msg.replace('§r', '').replace('§d', '').replace('§c', '').replace('§6', '').replace('§e', '').replace('§a', '')
    heading = '[CBR] ' + datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
    if error == True:
        msg = heading + '[ERROR]: ' + msg
    elif debug_mode == True and debug == True:
        msg = heading + '[DEBUG]: ' + msg
    elif debug == False:
        msg = heading + '[INFO]: ' + msg
    elif debug_mode == False and debug == True:
        return
    print(msg)
    with open('logs/ChatBridgeReforged_Client_mc.log', 'a+') as log:
        log.write(msg + '\n')


def bug_log(error = False):
    print('bug')
    for line in traceback.format_exc().splitlines():
        print(line)
        if error == True:
            out_log(line, error = True)
        else:
            out_log(line, debug = True)


def print_msg(msg, num, info: Info = None, src : CommandSource = None, server : ServerInterface = None):
    if src != None:
        server = src.get_server()
        info = src.get_info()
    if num == 0:
        server.say(msg)
        out_log(str(msg))
    elif num == 1:
        server.tell(info.player, msg)
        out_log(str(msg))


def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r+') as config:
            return json.load(config)
    else:
        out_log("Config file not Found", error=True)
        raise FileNotFoundError

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
            out_log('TypeError when decrypting text', True)
            out_log('text =', text, True)
            raise err
        except ValueError as err:
            out_log(err.args, True)
            out_log('len(text) =' + str(len(text)), True)
            raise err
        if sys.version_info.major == 3:
            try:
                result = str(result, encoding='utf-8')
            except UnicodeDecodeError:
                out_log('error at decrypt string conversion', True)
                out_log('raw result = ' + str(result), True)
                result = str(result, encoding='ISO-8859-1')
                out_log('ISO-8859-1 = ' + str(result), True)
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
        out_log(f"Received {msg!r} from {addr!r}", debug = True)
        return msg

    async def send_msg(self, client_stream : trio.SocketStream, msg ,target = ''):
        if not client.connected:
            out_log("Not connected to the server", debug = True)
            return
        if target != '':
            target = 'to ' + target
        out_log(f"Send: {msg!r} {target}", debug = True)
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
        out_log(f'Ping to server', debug = True)
        start_time = time.time()
        await self.client.send_msg(self.client.client_stream, '{"action": "keepAlive", "type": "ping"}', 'server')
        await self.ping_result()
        out_log(f'get ping result from server', debug = True)
        if self.end == -1:
            out_log(f'No response from server', debug = True)
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
            out_log(f'- Offline')
        elif ping == -1:
            out_log(f'- No response - time = 2000ms')
        else:
            out_log(f'- Alive - time = {ping}ms')


    async def process_msg(self, msg, client_stream : trio.SocketStream, addr):
        if 'action' in msg.keys():
            if msg['action'] == 'result':
                if msg['result'] == 'login success':
                    out_log("Login Success")
                else:
                    out_log("Login in fail", error = True)
            elif msg['action'] == 'keepAlive':
                if msg['type'] == 'ping':
                    await self.client.send_msg(client_stream, '{"action": "keepAlive", "type": "pong"}')
                elif msg['type'] == 'pong':
                    self.end = time.time()
            elif msg['action'] == 'message':
                message = self.message_formater(msg['client'], msg['player'], msg['message'])
                out_log(message)
            elif msg['action'] == 'stop':
                await self.client.close_connection()
                out_log(f'Connection closed from server')
            elif msg['action'] == 'command':
                sender = msg['sender']
                recevier = msg['receiver']
                command = msg['command']
                if msg['result']['responded']:
                    if(self.server.clients[sender]['online']):
                        await self.server.send_msg(self.server.clients[sender]['writer'], json.dumps(msg), sender)
                        out_log(f'Result of {command} send to {sender}')
                    else:
                        out_log(f'Client {sender} is Closed', error = True)
                else:
                    if(self.server.clients[recevier]['online']):
                        await self.server.send_msg(self.server.clients[recevier]['writer'], json.dumps(msg), recevier)
                        out_log(f'Send Command {command} to {recevier}')
                    else:
                        out_log(f'Client {recevier} not found', debug = True)

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
            out_log("Already Connected to server", debug = True)
    
    async def start(self):
        self.cancelled = False
        out_log(f"Connecting to {self.ip}:{self.port}")
        self.client_stream = await trio.open_tcp_stream(self.ip, self.port)
        self.connected = True
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_echo)
        
    def trystop(self):
        if self.connected == True:
            trio.run(self.close_connection)
            out_log("Closed connection")
        else:
            out_log("Connection already closed", error = True)

    async def close_connection(self, target = ''):
        if not self.client_stream == None and self.connected == True:
            await self.send_msg(self.client_stream, json.dumps({'action' : 'stop'}), target)
            await self.client_stream.aclose()
            self.cancelled = True
            self.cancel_scope.cancel()
            out_log("Connection closed to server", debug = True)
        self.connected = False

    def reload(self):
        out_log("Reload ChatBridgeReforced Client now")
        trio.run(self.close_connection)
        config = load_config()
        self.setup(config)
        out_log("Reload Config", debug = True)
        self.trystart()
    
    async def keep_alive(self):
        while not self.client_stream == None and self.connected:
            out_log("keep alive", debug = True)
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
            out_log("Stop Receive message", debug = True)
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
                    out_log('Connection time out!', error = True)
                    out_log('Closed connection to server', debug = True)
                else:
                    out_log("Cancel Process", debug = True)
                break
            except:
                bug_log()
                break
        self.connected = False

'''if __name__ == '__main__':
    config = load_config()
    client = CBRTCPClient(config)
    client.trystart()
'''

if __name__ == '__main__':
    config = load_config()
    client = CBRTCPClient(config)
    client.trystart()
    while True:
        a = input()
        if a == 'help':
            out_log(str(help_msg))
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
            out_log(f'forcedebug: {debug_mode}')
        elif a == 'test':
            for thread in threading.enumerate(): 
                print(thread.name)
        elif client.connected:
            trio.run(client.send_msg, client.client_stream, client.process.msg_json_formater(config['name'], '', a))
        else:
            out_log("Not Connected")

@new_thread("CBRProcess")
def on_info(server : ServerInterface, info : Info):
    global debug_mode
    msg = info.content
    if msg.startswith('!!CBR'):
        #if msg.endswith('<--[HERE]'):
        #    msg = msg.replace('<--[HERE]', '')
        args = msg.split(' ')
        if len(args) == 1 or args[1] == 'help':
            server.tell(info.player, help_msg)
        elif args[1] == 'start':
            client.trystart()
        elif args[1] == 'stop':
            client.trystop()
        elif args[1] == 'reload':
            client.reload()
        elif args[1] == 'restart':
            client.trystop()
            client.trystart()
        elif args[1] == 'ping':
            ping = trio.run(client.process.ping_test)
            client.process.ping_log(ping)
        elif args[1] == 'forcedebug':
            debug_mode = not debug_mode
            out_log(f'forcedebug: {debug_mode}')
        elif args[1] == 'test':
            for thread in threading.enumerate(): 
                print(thread.name)
        else:
            out_log("Command not Found")
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

@new_thread("CBRload")
def on_load(server, old):
    if old != None:
        old.client.trystop()
    time.sleep(1)
    print('load')
    global client
    config = load_config()
    client = CBRTCPClient(config)
    client.trystart()
    client.server = server