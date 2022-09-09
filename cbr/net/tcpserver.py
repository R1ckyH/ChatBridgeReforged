import json
import trio

from functools import partial

from cbr.lib.client import Client
from cbr.lib.config import Config
from cbr.lib.logger import CBRLogger
from cbr.net.network import Network
from cbr.net.process import ServerProcess, ClientProcess
from cbr.plugin.plugin import PluginManager
from cbr.plugin.rtext import *


def rtext_cmd(txt, msg, cmd):
    return RText(txt).h(msg).c(RAction.suggest_command, cmd)


class CBRTCPServer(Network):
    def __init__(self, logger: CBRLogger, config: "Config"):
        self.logger = logger
        self.config = config
        self.ip = self.config.ip
        self.port = self.config.port
        self.clients = self.setup_client()
        super().__init__(logger, self.config.aes_key, self.clients)
        self.plugin_manager = None
        self.process = None
        self.nursery = None
        self.__register_help_msg = []
        self.token = None
        self.server_running = False
        # TODO: better exception

    async def run(self):
        self.server_running = True
        self.token = trio.lowlevel.current_trio_token()
        self.plugin_manager = PluginManager(self, self.logger)
        self.process = ServerProcess(self, self.logger)
        await self.main()

    async def start_server(self):
        try:
            await trio.serve_tcp(self.handle_echo, self.port, host=self.ip)
        except OSError:
            self.logger.bug(exit_now=True)
            await self.stop()

    async def stop(self):
        self.logger.debug("Server closing", "CBR")
        self.process.cancelled = True
        await self.close_all_connection()
        self.nursery.cancel_scope.cancel()
        self.server_running = False
        await self.plugin_manager.unload_all_plugins()
        self.logger.info("Server closed")

    def setup_client(self):
        client_config = self.config.clients
        client_dict = {}
        for i in client_config:
            client_dict.update({i["name"]: Client(i["name"], i["password"])})
        return client_dict

    async def close_all_connection(self):
        for i in self.clients.keys():
            if self.clients[i].online:
                stream = self.clients[i].stream
                await self.process.close_connection(stream, i)
                self.logger.info(f"Closed connection to {i}")

    async def main(self):
        try:
            async with trio.open_nursery() as self.nursery:
                self.nursery.start_soon(self.start_server)
                self.logger.info(f"The Server is now serving on {self.ip}:{self.port}")
                await self.plugin_manager.reload_all_plugins()
                self.nursery.start_soon(partial(trio.to_thread.run_sync, self.input_process, cancellable=True))
        except KeyboardInterrupt:
            await self.stop()

    def register_process(self, process: ClientProcess, client_name):
        self.clients[client_name].process = process

    async def handle_echo(self, stream: trio.SocketStream):
        try:
            address = stream.socket.getpeername()
        except Exception:
            self.logger.bug()
            self.logger.critical("Error in get peer name")
            address = "ERROR ADDRESS"
        self.logger.debug(f"new session started from {address}", "CBR")
        client_process = ClientProcess(self, self.logger)
        async with trio.open_nursery() as nursery:
            while not client_process.cancelled:
                try:
                    with trio.fail_after(120) as client_process.cancel_scope:
                        await self.server_process(stream, client_process, address, nursery)
                except trio.TooSlowError:
                    if not client_process.cancelled:
                        self.logger.error("Connection time out!")
                    else:
                        self.logger.debug("Cancel Process", "CBR")
                    break
                except trio.BrokenResourceError:
                    self.logger.debug("Process broken", "CBR")
                    break
                except trio.ClosedResourceError:
                    self.logger.debug("Process Closed", "CBR")
                    break
                except trio.Cancelled:
                    self.logger.debug(f"Cancel Process to {client_process.current_client}", "CBR")
                    break
                except Exception:
                    self.logger.bug()
                    if client_process.current_client != "":
                        self.logger.info(f"Closed Process to {client_process.current_client}")
                    break
            client_process.cancelled = True
            if client_process.current_client != "":
                self.clients[client_process.current_client].online = False

    async def server_process(self, stream: trio.SocketStream, client_process: ClientProcess, address, nursery):
        msg = await self.receive_msg(stream, address)
        try:
            msg = json.loads(msg)
        except Exception:
            await self.send_stop(stream)
            self.logger.info(f"Failed decode message from {address}, please check encryption keys")
            self.logger.bug(error=False)
            self.logger.info(f"message: {msg}")
            await stream.aclose()
            return
        await client_process.process_msg(msg, stream, address, nursery)

    def input_process(self):
        while not self.process.cancelled:
            try:
                msg = input()
            except EOFError:
                return
            except UnicodeDecodeError:
                self.logger.bug()
            try:
                trio.from_thread.run(self.process.msg_process, msg, self.nursery)
            except Exception:
                self.logger.bug()

    def get_register_help_msg(self):
        msg = ""
        for i in self.__register_help_msg:
            if msg != "":
                msg += "\n"
            msg += rtext_cmd(f"§7{i['prefix']}", i["plugin_id"], i["prefix"]) + f"§f: {i['msg']}"
        return msg

    def add_register_help_msg(self, plugin_id, prefix, msg):
        for i in range(len(self.__register_help_msg)):
            if self.__register_help_msg[i]["prefix"] == prefix:
                self.__register_help_msg.pop(i)
                break
        self.__register_help_msg.append({"prefix": prefix, "msg": msg, "plugin_id": plugin_id})

    def deregister_help_msg(self, plugin_id):
        for i in range(len(self.__register_help_msg)):
            if self.__register_help_msg[i]["plugin_id"] == plugin_id:
                self.__register_help_msg.pop(i)
                break
