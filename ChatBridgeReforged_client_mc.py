import json
import os
import struct
import sys
import threading
import time
import traceback
import trio

from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES
from datetime import datetime
from mcdreforged.api.all import *

debug_mode = False
ping_time = 60
config_file = 'config/ChatBridgeReforged_client.json'
client = None
prefix = '!!CBR'
prefix2 = '!!cbr'
client_color = '6'#minecraft color code


def rtext_cmd(txt, msg, cmd):
    return RText(txt).h(msg).c(RAction.run_command, cmd)

help_msg = '''§b-----------§fChatBridgeReforged_Client§b-----------§r
''' + rtext_cmd(f'{prefix} help §ashow help message§r', 'click me to show help message', f'{prefix} help') + '''
''' + rtext_cmd(f'{prefix} start §astart ChatBridgeReforged client§r', 'Click me to start', f'{prefix} start') + '''
''' + rtext_cmd(f'{prefix} stop §astop ChatBridgeReforged client§r', 'Click me to stop', f'{prefix} stop') + '''
''' + rtext_cmd(f'{prefix} stauts §ashow status ChatBridgeReforged client§r', 'Click me to show status', f'{prefix} status') + '''
''' + rtext_cmd(f'{prefix} reload §areload ChatBridgeReforged client§r', 'Click me to reload', f'{prefix} reload') + '''
''' + rtext_cmd(f'{prefix} restart §arestart ChatBridgeReforged client§r', 'Click me to restart', f'{prefix} restart') +  '''
''' + rtext_cmd(f'{prefix} ping §aping ChatBridgeReforged server§r', 'Click me to ping server', f'{prefix} ping') +  '''
§b-----------------------------------------------§r'''  

PLUGIN_METADATA = {
    'id': 'chatbridgereforged_client_mc',
    'version': '0.0.1-Alpha-006-pre3',
    'name': 'ChatBridgeReforged_Client_mc',
    'description': 'Reforged of ChatBridge, Client for normal mc server.',
    'author': 'ricky',
    'link': 'https://github.com/rickyhoho/ChatBridgeReforged',
    'dependencies': {
        'mcdreforged': '>=1.3.0'
    }
}

DEFAULT_CONFIG = {
    "name" : "survival",
	"password": "survival",
	"ip_address" : "127.0.0.1",
	"port" : 30001,
	"aes_key" : "ThisIstheSecret"
}


def out_log(msg : str, error = False, debug = False):
    for i in range(6):
        msg = msg.replace('§' + str(i), '').replace('§' + chr(97 + i), '')
    msg = msg.replace('§6', '').replace('§7', '').replace('§8', '').replace('§9', '')
    heading = '[CBR] ' + datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
    if error:
        msg = heading + '[ERROR]: ' + msg
    elif debug:
        if not debug_mode:
            return
        msg = heading + '[DEBUG]: ' + msg
    else:
        msg = heading + '[INFO]: ' + msg
    print(msg)
    with open('logs/ChatBridgeReforged_Client_mc.log', 'a+') as log:
        log.write(msg + '\n')


def bug_log(error = False):
    print('bug')
    for line in traceback.format_exc().splitlines():
        if error == True:
            out_log(line, error = True)
        else:
            out_log(line, debug = True)


def print_msg(msg, num, info: Info = None, src : CommandSource = None, server : ServerInterface = None, error = False, debug = False):
    if src != None:
        server = src.get_server()
        info = src.get_info()
    if num == 0:
        if not server == None:
            server.say(msg)
        out_log(str(msg))
    elif num == 1:
        server.reply(info, msg)
        out_log(str(msg))
    elif num == 2:
        if info == None or not info.is_player:
            out_log(msg, error, debug)
        else:
            server.reply(info, msg)


def load_config():
    sync = False
    if not os.path.exists(config_file):
        os.makedirs(os.path.dirname(config_file), exist_ok = True)
        out_log('Config not find', error = True)
        out_log('Generate default config')
        with open(config_file, 'w') as config:
            json.dump(DEFAULT_CONFIG, config, indent=4)
        return DEFAULT_CONFIG
    with open(config_file, 'r') as config:
        data = dict(json.load(config))
    for config in DEFAULT_CONFIG.keys():
        if not config in data.keys():
            out_log(f"Config {config} not found, use default value {DEFAULT_CONFIG[config]}", Error)
            data.update({config : DEFAULT_CONFIG[config]})
            sync = True
    if sync:
        with open(config_file, 'w') as config:
            json.dump(data, config, indent = 4)
    return data

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
            message = f"§7[§{client_color}{client}§7] <{player}> {msg}"  # chat message
        else:
            message = f"§7[§{client_color}{client}§7] {msg}"
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

    def ping_log(self, ping, info = None, server = None):
        if ping == -2:
            print_msg(f'- Offline', 2, info, server = server)
        elif ping == -1:
            print_msg(f'- No response - time = 2000ms', 2, info, server = server)
        else:
            print_msg(f'- Alive - time = {ping}ms', 2, info, server = server)


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
                print_msg(message, num = 0, server=client.server)
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
        self.server = None

    def setup(self, config_data):
        self.client_stream = False
        self.connected = False
        self.cancelled = False
        super().__init__(config_data['aes_key'])
        self.ip = config_data['ip_address']
        self.port = config_data['port']
        self.name = config_data['name']
        self.password = config_data['password']
        self.process = ClientProcess(self)
    
    def trystart(self, info = None):
        if self.connected == False:
            threading.Thread(target = trio.run, name = 'CBR', args=(self.start, info), daemon = True).start()
        else:
            if info != None:
                print_msg("Already Connected to server", 2, info, server = self.server, error = True)
            else:
                out_log("Already Connected to server", debug = True)

    async def start(self, info):
        self.cancelled = False
        print_msg(f"Connecting to server", 2, info, server = self.server)
        out_log(f'Open connection to {self.ip}:{self.port}')
        self.client_stream = await trio.open_tcp_stream(self.ip, self.port)
        self.connected = True
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_echo)

    def trystop(self, info = None):
        if self.connected == True:
            trio.run(self.close_connection)
            print_msg("Closed connection", 2, info, server = self.server)
        else:
            print_msg("Connection already closed", 2, info, server = self.server)

    async def close_connection(self, target = ''):
        if not self.client_stream == None and self.connected == True:
            self.cancelled = True
            await self.send_msg(self.client_stream, json.dumps({'action' : 'stop'}), target)
            await self.client_stream.aclose()
            self.cancel_scope.cancel()
            out_log("Connection closed to server")
        self.connected = False

    def reload(self, info = None):
        print_msg("Reload ChatBridgeReforced Client now", 2, info, server = self.server)
        trio.run(self.close_connection)
        config = load_config()
        time.sleep(0.1)
        self.setup(config)
        print_msg("Reload Config", 2, info, server = self.server)
        self.trystart(info)
        time.sleep(0.1)
        print_msg(f"CBR status: Online = {client.connected}", 2, info, server = self.server)

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


if __name__ == '__main__':
    config = load_config()
    client = CBRTCPClient(config)
    client.trystart()
    while True:
        a = input()
        if a == 'help':
            for line in str(help_msg).splitlines():
                out_log(line)
        elif a == 'stop':
            client.trystop()
        elif a == 'start':
            client.trystart()
        elif a == 'status':
            print_msg(f"CBR status: Online = {client.connected}", 2)
        elif a == 'ping':
            ping = trio.run(client.process.ping_test)
            client.process.ping_log(ping)
        elif a == 'reload':
            client.reload()
        elif a == 'restart':
            client.trystop()
            time.sleep(0.1)
            client.trystart()
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
    if msg.startswith(prefix) or msg.startswith(prefix2):
        info.cancel_send_to_server()
        #if msg.endswith('<--[HERE]'):
        #    msg = msg.replace('<--[HERE]', '')
        args = msg.split(' ')
        if len(args) == 1 or args[1] == 'help':
            server.reply(info, help_msg)
        elif args[1] == 'start':
            client.trystart(info)
        elif args[1] == 'status':
            print_msg(f"CBR status: Online = {client.connected}", 2, info, server = server)
        elif args[1] == 'stop':
            client.trystop(info)
        elif args[1] == 'reload':
            client.reload(info)
        elif args[1] == 'restart':
            client.trystop(info)
            time.sleep(0.1)
            client.trystart(info)
            time.sleep(0.1)
            print_msg(f"CBR status: Online = {client.connected}", 2, info, server = server)
        elif args[1] == 'ping':
            ping = trio.run(client.process.ping_test)
            client.process.ping_log(ping, info, server = server)
        elif args[1] == 'forcedebug' and server.get_permission_level(info.player) > 2:
            debug_mode = not debug_mode
            print_msg(f'forcedebug: {debug_mode}', 2, info, server = server)
        elif args[1] == 'test':
            for thread in threading.enumerate(): 
                print(thread.name)
        else:
            print_msg("Command not Found", 2, info, server = server)
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
    global client
    if old != None:
        old.client.trystop()
    time.sleep(1)
    print('load')
    config = load_config()
    client = CBRTCPClient(config)
    client.trystart()
    client.server = server