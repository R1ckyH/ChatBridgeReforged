"""
plugin run here
"""

import importlib
import importlib.util
import os
import trio

from cbr.lib.logger import CBRLogger
from cbr.plugin.plugin_event import PluginEventManager

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cbr.net.tcpserver import CBRTCPServer


class Plugin:
    def __init__(self, logger: CBRLogger, path, name):
        self.logger = logger
        self.path_name = path
        self.name = name
        self.metadata = self.__get_default_metadata()
        try:
            self.last_edit_time = os.path.getmtime(path)
            self.spec = importlib.util.spec_from_file_location(name, path)
            self.instance = importlib.util.module_from_spec(self.spec)
            self.spec.loader.exec_module(self.instance)
        except Exception as e:
            self.logger.bug(exit_now=False, error=True)
            raise e
        self.setup()  # TODO: CBRInterface in plugin?(considering)

    def setup(self):
        self.__init_metadata()

    def __init_metadata(self):
        self.gen_metadata()
        self.id = self.get_data('id')
        self.version = self.get_data('version')
        self.name = self.get_data('name')
        self.description = self.get_data('description')
        self.author = self.get_data('author')
        self.link = self.get_data('link')
        self.dependencies = self.get_data('dependencies')

    def check_change(self):
        last_edit_time = os.path.getmtime(self.path_name)
        if self.last_edit_time != last_edit_time:
            return True
        else:
            return False

    def reload(self):
        try:
            self.spec.loader.exec_module(self.instance)
        except Exception as e:
            self.logger.bug(exit_now=False, error=True)
            raise e
        self.last_edit_time = os.path.getmtime(self.path_name)
        self.setup()

    def __get_default_metadata(self, data=None):
        metadata = {
            'id': self.name,
            'version': '0.0.0',
            'name': self.name,
            'description': "A CBR plugin",
            'author': None,
            'link': None,
            'dependencies': None
        }
        if data is not None:
            return metadata[data]
        return metadata

    def gen_metadata(self):
        try:
            self.metadata = self.instance.METADATA
        except AttributeError:
            pass

    def get_data(self, data):
        try:
            data = self.metadata[data]
        except KeyError:
            data = self.__get_default_metadata(data)
        return str(data)


class PluginManager:
    def __init__(self, server: 'CBRTCPServer', logger: CBRLogger):
        self.server = server
        self.logger = logger
        self.event_manager = PluginEventManager(server, logger)
        self.plugins = {}
        self.plugin_dir = {}

    async def __get_plugin_path_list(self):
        plugins = ['./cbr/plugin/default_plugin.py']
        for entry in os.scandir('./plugins'):
            if entry.is_file() and entry.name.endswith('.py'):
                plugins.append(entry.path)
        return plugins

    async def reload_all_plugins(self):
        self.logger.debug("Start reload plugins", module='plugin')
        await self.unload_all_plugins()
        await self.load_all_plugins()
        self.logger.debug("Finish reload plugins", module='plugin')

    async def get_loaded_plugins(self):
        plugins = []
        for i in self.plugins.values():
            plugins.append(f"§r{i.name}: §7[{i.id}@{i.version}]")
        return plugins

    async def check_not_load_plugins(self):
        cache_list = await self.__get_plugin_path_list()
        for i in self.plugins.values():
            if i.path_name in cache_list:
                cache_list.remove(i.path_name)
        for i in range(len(cache_list)):
            cache_list[i] = os.path.basename(cache_list[i])
        return cache_list

    async def get_disable_plugins(self):
        plugins = []
        for entry in os.scandir('./plugins'):
            if entry.is_file() and entry.name.endswith('.disable'):
                plugins.append(entry.name)
        return plugins

    async def load_plugin(self, plugin_file_name):
        plugin_file_path = './plugins/' + plugin_file_name
        if not os.path.exists(plugin_file_path):
            return f"Fail to load {plugin_file_name}, file not find"
        elif not plugin_file_name.endswith('.py') or not os.path.isfile(plugin_file_path):
            return f"Fail to load {plugin_file_name}, invalid file"
        else:
            if await self.__load_plugin(plugin_file_path, plugin_file_name):
                return f"Loaded Plugin {plugin_file_name}"
            elif plugin_file_name not in self.plugin_dir.keys():
                return f"Failed to load {plugin_file_name}"
            else:
                return f"Reload plugin {plugin_file_name}"

    async def __load_plugin(self, plugin_path, plugin_file_name):
        if plugin_file_name in self.plugin_dir:
            plugin: Plugin = self.plugins[self.plugin_dir[plugin_file_name]]
            if plugin.check_change():
                await self.plugin_run_event('on_unload', plugin.id)
                self.logger.info(f"Reload plugin {plugin.id}@{plugin.version}")
                try:
                    plugin.reload()
                except Exception:
                    self.logger.info(f"Fail to Load plugin {plugin_file_name}")
                    return False
                await self.plugin_run_event('on_load', plugin.id)
                return True
            else:
                return False
        else:
            try:
                plugin = Plugin(self.logger, plugin_path, plugin_file_name[:-3])
                plugin.reload()
                self.logger.info(f"Load plugin {plugin.id}@{plugin.version}")
                self.plugin_dir.update({plugin_file_name: plugin.id})
                self.event_manager.register_plugin(plugin)
                self.plugins[plugin.id] = plugin
                await self.plugin_run_event('on_load', plugin.id)
                return True
            except Exception:
                self.logger.info(f"Fail to Load plugin {plugin_file_name}")
                return False

    async def unload_plugin(self, plugin_id, nursery=None):
        if plugin_id in self.plugins.keys():
            plugin_file_name = ''
            for i in self.plugin_dir.keys():
                if self.plugin_dir[i] == plugin_id:
                    plugin_file_name = i
            await self.plugin_run_event('on_unload', plugin_id, nursery=nursery)
            await self.__remove_plugin(plugin_file_name, plugin_id)
            return True
        else:
            return False

    async def enable_plugin(self, plugin_file_name):
        plugin_file_path = './plugins/' + plugin_file_name
        if not os.path.exists(plugin_file_path):
            return f"Fail to enable {plugin_file_name}, file not find"
        elif not plugin_file_name.endswith('.py.disable') or not os.path.isfile(plugin_file_path):
            return f"Fail to enable {plugin_file_name}, invalid file"
        else:
            os.rename(plugin_file_path, plugin_file_path[:-8])
            if await self.__load_plugin(plugin_file_path[:-8], plugin_file_name):
                return f"Enabled and loaded Plugin {plugin_file_name}"
            else:
                return f"Enabled {plugin_file_name}, Load failed"

    async def reload_plugin(self, plugin_id):
        if plugin_id in self.plugins.keys():
            plugin = self.plugins[plugin_id]
            path = plugin.path_name
            file_name = os.path.basename(path)
            await self.unload_plugin(plugin_id)
            return await self.__load_plugin(path, file_name)
        else:
            return None

    async def disable_plugin(self, plugin_id):
        if plugin_id in self.plugins.keys():
            plguin_path = self.plugins[plugin_id].path_name
            await self.unload_plugin(plugin_id)
            os.rename(plguin_path, plguin_path + ".disable")
            return True
        else:
            return False

    async def load_all_plugins(self):
        self.logger.debug("Start load plugins", module='plugin')
        plugins = await self.__get_plugin_path_list()
        for i in plugins:
            await self.__load_plugin(i, os.path.basename(i))
        self.logger.debug("Finish load plugins", module='plugin')

    async def unload_all_plugins(self):
        self.logger.debug("Start unload plugins", module='plugin')
        self.event_manager.unloading = True
        async with trio.open_nursery() as nursery:
            for i in self.plugin_dir.values():
                nursery.start_soon(self.unload_plugin, i, nursery)
        self.event_manager.unloading = False
        self.logger.debug("Finish unload plugins", module='plugin')

    async def check_reload_all_plugins(self):
        cache_plugin = list(self.plugin_dir.keys())
        cache_list = await self.__get_plugin_path_list()
        load_plugins = 0
        unload_plugins = 0
        reloaded_plugins = 0
        for i in self.plugin_dir.keys():
            for j in cache_list:
                name = os.path.basename(j)
                if i == name:
                    self.logger.debug(f"Check reload of {i}")
                    cache_list.remove(j)
                    cache_plugin.remove(i)
                    if await self.__load_plugin(j, name):
                        reloaded_plugins += 1
                    break
        for i in cache_plugin:
            await self.unload_plugin(self.plugin_dir[i])
            unload_plugins += 1
        for i in cache_list:
            await self.__load_plugin(i, os.path.basename(i))
            load_plugins += 1
        return load_plugins, unload_plugins, reloaded_plugins, len(self.plugins)

    async def __remove_plugin(self, plugin_file_name, plugin_id):
        self.event_manager.remove_plugin(self.plugin_dir[plugin_file_name])
        self.server.del_register_help_msg(plugin_id)
        self.plugin_dir.pop(plugin_file_name)
        self.plugins.pop(plugin_id)
        self.logger.info(f"Unload plugin {plugin_file_name}")

    async def run_event(self, event, *args, wait_time=1, nursery=None):
        if nursery is None:
            self.logger.debug("no nursery exist, spawn nursery now")
            async with trio.open_nursery() as nursery:
                await self.event_manager.run_event(event, wait_time, nursery, *args)
        else:
            await self.event_manager.run_event(event, wait_time, nursery, *args)

    async def plugin_run_event(self, event, plg_id, *args, wait_sec=1, nursery=None):
        if nursery is None:
            self.logger.debug("no nursery exist, spawn nursery now")
            async with trio.open_nursery() as nursery:
                await self.event_manager.plugin_run_event(event, plg_id, nursery, *args, wait_time=wait_sec)
        else:
            await self.event_manager.plugin_run_event(event, plg_id, nursery, *args, wait_time=wait_sec)
