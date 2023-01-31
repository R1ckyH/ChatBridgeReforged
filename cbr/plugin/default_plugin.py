"""
    Default CBR plugin
    ##################
    Don"t imitate it
    ##################
"""
import sys
import threading
import trio


import cbr
from cbr.plugin.info import MessageInfo
from cbr.plugin.cbrinterface import CBRInterface
from cbr.net.process import ServerProcess
from cbr.resources import formatter

METADATA = {
    "id": "ChatBridgeReforged",
    "version": cbr.__version__,
    "name": "ChatBridgeReforged",
    "description": "The core of CBR",
    "author": "Ricky",
    "link": "https://github.com/R1ckyH/ChatBridgeReforged"
}


async def reply(server: CBRInterface, info: MessageInfo, msg, chat=False):
    msg = "§7[§6CBR§7] " + msg
    if info.source_client == "CBR" and not chat:
        msg = formatter.no_color_formatter(msg)
        for i in msg.splitlines():
            server.cbr_logger.info(i)
    else:
        await trio.to_thread.run_sync(server.reply, info, msg)


async def unknown_cmd(command, server: CBRInterface, info: MessageInfo):
    if command != "":
        command = " " + command
    command = "##CBR" + command
    msg = f"Unknown command, use {command} help for help message"
    if info.source_client == "CBR":
        server.cbr_logger.error(msg)
    else:
        await reply(server, info, msg, chat=True)


def reload_result(loaded_plugin, unloaded_plugin, reloaded_plugin, failed_plugin, num):
    msg = f"Total plugin amount: {num}"
    if loaded_plugin == 0 and unloaded_plugin == 0 and reloaded_plugin == 0 and failed_plugin == 0:
        msg = "0 plugin changed, " + msg
    if failed_plugin != 0:
        msg = f"{failed_plugin} plugin fail to load, " + msg
    if reloaded_plugin != 0:
        msg = f"{reloaded_plugin} plugin reloaded, " + msg
    if loaded_plugin != 0:
        msg = f"{loaded_plugin} plugin loaded, " + msg
    if unloaded_plugin != 0:
        msg = f"{unloaded_plugin} plugin unloaded, " + msg
    return msg


# TODO: permission system(may do)
async def msg_process(self: ServerProcess, msg: str, nursery: trio.Nursery, server: CBRInterface, info: MessageInfo, command=False):
    args = msg.split(" ")
    length = len(args)
    if args[0] == "help" or args[0] == "?" or args[0] == "":
        await reply(server, info, self.get_help_msg(), chat=True)
    elif args[0] == "##help":
        await reply(server, info, self.server.get_register_help_msg(), chat=True)
    elif args[0] == "reload" or args[0] == "r":
        if length == 1 or args[1] == "help":
            await reply(server, info, self.get_help_msg("reload"), chat=True)
        elif args[1] == "plugin" or args[1] == "plg":
            load_plugin, unload_plugin, reloaded_plugin, failed_plugin, num = await self.plugin_manager.check_reload_all_plugins()
            msg = reload_result(load_plugin, unload_plugin, reloaded_plugin, failed_plugin, num)
            await reply(server, info, msg)
        elif (args[1] == "config" or args[1] == "conf") and False:
            pass  # TODO reload config(next version)?
            # self.server.config.init_config(self.logger)
            # await reply("Config reloaded", server, info)
        elif args[1] == "all":
            loaded_plugin, unloaded_plugin, reloaded_plugin, failed_plugin, num = await self.plugin_manager.check_reload_all_plugins()
            msg = reload_result(loaded_plugin, unloaded_plugin, reloaded_plugin, failed_plugin, num)
            await reply(server, info, msg)
        else:
            await unknown_cmd("reload", server, info)
    elif args[0] == "status" or args[0] == "stat":
        if length == 1 or args[1] == "help":
            await reply(server, info, self.get_help_msg("status"), chat=True)
        elif args[1] == "online":
            await reply(server, info, self.online_list(), chat=True)
        elif args[1] == "CBR":
            await reply(server, info, self.get_status(), chat=True)
        elif args[1] == "ping":
            if length == 2:
                message = await self.ping_all()
                await reply(server, info, "Ping clients:" + message, chat=True)
            else:
                if length > 2 and args[2] in self.server.clients.keys():
                    ping = await self.ping_test(args[2])
                    await reply(server, info, self.ping_log(ping, args[2]), chat=True)
                else:
                    await reply(server, info, "Client not found", chat=True)
        elif args[1] == "all":
            msg = self.get_status()
            msg += await self.ping_all()
            await reply(server, info, msg, chat=True)
        else:
            await unknown_cmd("status", server, info)
    elif args[0] == "plugin" or args[0] == "plg":
        if length == 1 or args[1] == "help":
            await reply(server, info, self.get_help_msg("plugin"), chat=True)
        elif args[1] == "list":
            loaded_plugin = await self.plugin_manager.get_loaded_plugins()
            disabled_plugin = await self.plugin_manager.get_disable_plugins()
            not_loaded_plugin = await self.plugin_manager.check_not_load_plugins()
            msg = f"§rLoaded plugins: {len(loaded_plugin)}"
            for i in loaded_plugin:
                msg = msg + f"\n- {i}"
            msg = msg + f"\n§rDisabled plugins: {len(disabled_plugin)}"
            for i in disabled_plugin:
                msg = msg + f"\n- {i}"
            msg = msg + f"\n§rNot loaded plugins: {len(not_loaded_plugin)}"
            for i in not_loaded_plugin:
                msg = msg + f"\n- {i}"
            await reply(server, info, msg)
        elif args[1] == "load" and length == 3:
            await reply(server, info, await self.plugin_manager.load_plugin(args[2]))
        elif (args[1] == "reload" or args[1] == "r") and length == 3:
            result = await self.plugin_manager.reload_plugin(args[2])
            if result is None:
                await reply(server, info, f"Plugin {args[2]} not exist")
            elif result:
                await reply(server, info, f"Plugin {args[2]} reloaded success")
            else:
                await reply(server, info, f"Plugin {args[2]} success unloaded, failed to load")
        elif args[1] == "reloadall":
            nursery.start_soon(self.plugin_manager.reload_all_plugins)
        elif args[1] == "enable" and length == 3:
            await reply(server, info, await self.plugin_manager.enable_plugin(args[2]))
        elif command:
            if args[1] == "unload" and length == 3:
                if await self.plugin_manager.unload_plugin(args[2]):
                    await reply(server, info, f"Plugin {args[2]} unloaded")
                else:
                    await reply(server, info, f"Plugin {args[2]} not found")
            elif args[1] == "disable" and length == 3:
                if await self.plugin_manager.disable_plugin(args[2]):
                    await reply(server, info, f"Plugin ID: '{args[2]}' disabled")
                else:
                    await reply(server, info, f"Plugin ID: '{args[2]}' Not exist")
            else:
                await unknown_cmd("plugin", server, info)
        else:
            await unknown_cmd("plugin", server, info)
    elif command:
        if msg.startswith("say"):
            msg = msg.replace("say ", "")
            self.logger.debug("on_message active")
            nursery.start_soon(self.message_process, "CBR", "", msg, "CBR")
        elif msg == "test":
            for thread in threading.enumerate():
                print(thread.name)
        elif args[0] == "stop" or args[0] == "end":
            if length == 1:
                await self.server.stop()
            else:
                if args[1] in self.server.clients.keys():
                    await self.close_connection(self.server.clients[args[1]].stream, args[1])
                else:
                    self.logger.error("Client not found")
        elif msg.startswith("cmd"):
            if length > 1 and args[1] in self.server.clients.keys():
                if self.server.clients[args[1]].online:
                    cmd = msg.replace("cmd " + args[1] + " ", "")
                    stream = self.server.clients[args[1]].stream
                    await self.server.send_command(stream, cmd, args[1])
                else:
                    self.logger.error("Client not online")
            else:
                self.logger.error("Client not found")
        elif msg.startswith("forcedebug"):
            if length > 1:
                if args[1] in ["CBR", "plugin"]:
                    module = args[1]
                    self.logger.force_debug(module)
                elif args[1] == "list":
                    self.logger.info(self.logger.debug_config)
                else:
                    self.logger.error("Debug option not found")
            else:
                self.logger.force_debug()
        else:
            return False
    else:
        return False
    info.cancel_send_message()
    return True


def run_process(server: CBRInterface, info: MessageInfo, command=False):
    msg = info.content.replace("##CBR ", "").replace("##CBR", "")
    cbr_server = server._server
    process = cbr_server.process
    nursery = cbr_server.nursery
    token = cbr_server.token
    trio.from_thread.run(msg_process, process, msg, nursery, server, info, command, trio_token=token)


def on_message(server: CBRInterface, info: MessageInfo):
    if info.content == "##help":
        server.reply(info, server._server.get_register_help_msg())
    if info.content.startswith("##CBR") and info.client_type == "mc":  # for some reason, only mc client can access now
        info.cancel_send_message()
        run_process(server, info)


def on_command(server: CBRInterface, info: MessageInfo):  # not recommend doing, but you can do it
    run_process(server, info, command=True)


def on_load(server: CBRInterface):
    sys.path.append("plugins/")
    server.register_help_message("##CBR", "CBR control command")
