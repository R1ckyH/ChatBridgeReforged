"""
    Default CBR plugin
"""
import threading
import trio

from cbr.lib.config import CHATBRIDGEREFORGED_VERSION
from cbr.plugin.info import MessageInfo
from cbr.plugin.cbrinterface import CBRInterface
from cbr.net.process import ServerProcess

METADATA = {
    'id': 'ChatBridgeReforged',
    'version': CHATBRIDGEREFORGED_VERSION,
    'name': 'ChatBridgeReforged',
    'description': 'The core of CBR',
    'author': 'Ricky',
    'link': 'https://github.com/rickyhoho/ChatBridgeReforged'
}


async def reply(msg, server: CBRInterface, info: MessageInfo):
    await trio.to_thread.run_sync(server.reply, msg, info)


def unknown_cmd(command=''):
    if command != '':
        command = ' ' + command
    command = '##CBR' + command
    msg = f"Unknown command, use {command} help for help message"
    return msg


def reload_result(loaded_plugin, unloaded_plugin, reloaded_plugin, num):
    msg = f"Total plugin amount: {num}"
    if loaded_plugin == 0 and unloaded_plugin == 0 and reloaded_plugin == 0:
        msg = "0 plugin changed, " + msg
    if reloaded_plugin != 0:
        msg = f"{reloaded_plugin} plugin reloaded, " + msg
    if loaded_plugin != 0:
        msg = f"{loaded_plugin} plugin loaded, " + msg
    if unloaded_plugin != 0:
        msg = f"{unloaded_plugin} plugin unloaded, " + msg
    return msg


# TODO: permission system(may do)
async def msg_process(self: ServerProcess, msg: str, nursery: trio.Nursery, server: CBRInterface, info: MessageInfo, command=False):
    args = msg.split(' ')
    length = len(args)
    if args[0] == 'help' or args[0] == '?' or args[0] == '':
        await reply(self.get_help_msg(), server, info)
    elif args[0] == '##help':
        await reply(self.server.get_register_help_msg(), server, info)
    elif args[0] == 'reload' or args[0] == 'r':
        if length == 1 or args[1] == 'help':
            await reply(self.get_help_msg('reload'), server, info)
        elif args[1] == 'plugin' or args[1] == 'plg':
            load_plugin, unload_plugin, reloaded_plugin, num = await self.plugin_manager.check_reload_all_plugins()
            msg = reload_result(load_plugin, unload_plugin, reloaded_plugin, num)
            await reply(msg, server, info)
        elif (args[1] == 'config' or args[1] == 'conf') and False:
            pass  # TODO reload config(next version)?
            # self.server.config.init_config(self.logger)
            # await reply("Config reloaded", server, info)
        elif args[1] == 'all':
            loaded_plugin, unloaded_plugin, reloaded_plugin, num = await self.plugin_manager.check_reload_all_plugins()
            msg = reload_result(loaded_plugin, unloaded_plugin, reloaded_plugin, num)
            await reply(msg, server, info)
        else:
            await reply(unknown_cmd('reload'), server, info)
    elif args[0] == 'status':
        if length == 1 or args[1] == 'help':
            await reply(self.get_help_msg('status'), server, info)
        elif args[1] == 'online':
            await reply(self.online_list(), server, info)
        elif args[1] == 'CBR':
            await reply(self.get_status(), server, info)
        elif args[1] == 'ping':
            if length == 2:
                message = await self.ping_all()
                await reply('Ping clients:' + message, server, info)
            else:
                if length > 2 and args[2] in self.server.clients.keys():
                    ping = await self.ping_test(args[2])
                    await reply(self.ping_log(ping, args[2]), server, info)
                else:
                    await reply("Client not found", server, info)
        elif args[1] == 'all':
            msg = self.get_status()
            msg += f"{await self.ping_all()}"
            await reply(msg, server, info)
        else:
            await reply(unknown_cmd('status'), server, info)
    elif args[0] == 'plugin' or args[0] == 'plg':
        if length == 1 or args[1] == 'help':
            await reply(self.get_help_msg('plugin'), server, info)
        elif args[1] == 'list':
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
            await reply(msg, server, info)
        elif args[1] == 'load' and length == 3:
            await reply(await self.plugin_manager.load_plugin(args[2]), server, info)
        elif args[1] == 'reload' and length == 3:
            result = await self.plugin_manager.reload_plugin(args[2])
            if result is None:
                await reply(f"Plugin {args[2]} not exist", server, info)
            elif result:
                await reply(f"Plugin {args[2]} reloaded success", server, info)
            else:
                await reply(f"Plugin {args[2]} success unloaded, failed to load", server, info)
        elif args[1] == 'reloadall':
            nursery.start_soon(self.plugin_manager.reload_all_plugins)
        elif args[1] == 'enable' and length == 3:
            await reply(await self.plugin_manager.enable_plugin(args[2]), server, info)
        elif command:
            if args[1] == 'unload' and length == 3:
                if await self.plugin_manager.unload_plugin(args[2]):
                    await reply(f"Plugin {args[2]} unloaded", server, info)
                else:
                    await reply(f"Plugin {args[2]} not found", server, info)
            elif args[1] == 'disable' and length == 3:
                if await self.plugin_manager.disable_plugin(args[2]):
                    await reply(f"Plugin ID: '{args[2]}' disabled", server, info)
                else:
                    await reply(f"Plugin ID: '{args[2]}' Not exist", server, info)
        else:
            await reply(unknown_cmd('plugin'), server, info)
    elif command:
        if msg.startswith('say'):
            msg = msg.replace('say ', '')
            nursery.start_soon(self.message_process, "CBR", '', msg, "CBR")
        elif msg == 'test':
            for thread in threading.enumerate():
                print(thread.name)
        elif args[0] == 'stop' or args[0] == 'end':
            if length == 1:
                await self.server.stop()
            else:
                if args[1] in self.server.clients.keys():
                    await self.close_connection(self.server.clients[args[1]].stream, args[1])
                else:
                    self.logger.error("Client not found")
        elif msg.startswith('cmd'):
            if length > 1 and args[1] in self.server.clients.keys():
                if self.server.clients[args[1]].online:
                    cmd = msg.replace('cmd ' + args[1] + ' ', '')
                    stream = self.server.clients[args[1]].stream
                    await self.server.send_command(stream, cmd, args[1])
                else:
                    self.logger.error("Client not online")
            else:
                self.logger.error("Client not found")
        elif msg.startswith('forcedebug'):
            if length > 1:
                if args[1] in ["CBR", "plugin"]:
                    module = args[1]
                    self.logger.force_debug(module)
                elif args[1] == 'list':
                    self.logger.info(self.logger.debug_config)
                else:
                    self.logger.error("Debug option not found")
            else:
                self.logger.force_debug()
        else:
            self.logger.error(unknown_cmd())
    else:
        await reply(unknown_cmd(), server, info)


def run_process(server: CBRInterface, info: MessageInfo, command=False):
    info.cancel_send_message()
    msg = info.content.replace("##CBR ", '').replace("##CBR", '')
    cbr_server = server._server
    process = cbr_server.process
    nursery = cbr_server.nursery
    token = cbr_server.token
    trio.from_thread.run(msg_process, process, msg, nursery, server, info, command, trio_token=token)


def on_message(server: CBRInterface, info: MessageInfo):
    if info.content == '##help':
        server.reply(server._server.get_register_help_msg(), info)
    if info.content.startswith('##CBR') and info.client_type == 'mc':  # for some reason, only mc client can access now
        run_process(server, info)


def on_command(server: CBRInterface, info: MessageInfo):  # not recommend to do, but you can do it
    run_process(server, info, command=True)


def on_load(server: CBRInterface):
    server.register_help_message("##CBR", "CBR control command")
