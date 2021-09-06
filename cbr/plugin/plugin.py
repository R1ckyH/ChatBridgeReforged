"""
plugin run here
"""

import importlib
import os
import trio

from cbr.lib.logger import CBRLogger
from cbr.plugin.plugin_event import PluginEventManager
from cbr.plugin.cbrinterface import CBRInterface


class Plugin:
    def __init__(self, path):
        self.path_name = path
        self.metadata = self.__get_default_metadata()
        self.last_edit_time = os.path.getmtime(f'./plugins/{self.path_name}.py')
        self.instance = importlib.import_module('plugins.' + path)
        self.setup()

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

    def reload(self):
        self.instance = importlib.reload(self.instance)
        self.setup()

    def __get_default_metadata(self, data=None):
        metadata = {
            'id': self.path_name,
            'version': '0.0.0',
            'name': self.path_name,
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
    def __init__(self, server_interface: CBRInterface, logger: CBRLogger):
        self.server_interface = server_interface
        self.logger = logger
        self.event_manager = PluginEventManager(self.logger)
        self.plugins = {}
        self.dir_plugin = {}

    async def __get_plugin_list(self):
        plugins = []
        for entry in os.scandir('./plugins'):
            if entry.is_file() and entry.name.endswith('.py'):
                plugins.append(entry.name)
        return plugins

    async def reload_all_plugins(self):
        self.logger.debug("Start reload plugins", module='plugin')
        await self.unload_all_plugins()
        await self.load_all_plugins()
        self.logger.debug("Finish reload plugins", module='plugin')

    async def load_all_plugins(self):
        self.logger.debug("Start load plugins", module='plugin')
        plugins = await self.__get_plugin_list()
        for i in plugins:
            await self.load_plugin(i)
        self.logger.debug("Finish load plugins", module='plugin')

    async def load_plugin(self, plugin_file_name):
        if plugin_file_name in self.dir_plugin:
            last_edit_time = os.path.getmtime(f'./plugins/{plugin_file_name}')
            plugin: Plugin = self.plugins[self.dir_plugin[plugin_file_name]]
            if plugin.last_edit_time != last_edit_time:
                self.logger.info(f"Reload plugin {plugin_file_name}")
                plugin.reload()
            else:
                self.logger.info(f"Plugin {plugin_file_name} not change")
        else:
            self.logger.info(f"Load plugin {plugin_file_name}")
            plugin_instance = Plugin(plugin_file_name[:-3])
            plugin_instance.reload()
            self.dir_plugin.update({plugin_file_name: plugin_instance.id})
            self.event_manager.register_plugin(plugin_instance)
            await self.plugin_run_event('on_load', plugin_instance.id, nursery=None)
            self.plugins[plugin_instance.id] = plugin_instance

    async def unload_all_plugins(self):
        self.logger.debug("Start unload plugins", module='plugin')
        self.event_manager.unloading = True
        async with trio.open_nursery() as nursery:
            for i in self.dir_plugin:
                nursery.start_soon(self.unload_plugin, i, nursery)
        self.event_manager.unloading = False
        self.logger.debug("Finish unload plugins", module='plugin')

    async def unload_plugin(self, plugin_file_name, nursery):
        if plugin_file_name in self.dir_plugin:
            plugin_id = self.dir_plugin[plugin_file_name]
            await self.event_manager.plugin_run_event('on_unload', plugin_id, nursery, self.server_interface)
            self.event_manager.remove_plugin(self.dir_plugin[plugin_file_name])
            await self.__remove_plugin(plugin_file_name)
            self.logger.info(f"Unload plugin {plugin_file_name}")

    async def __remove_plugin(self, plugin_file_name):
        plugin_id = self.dir_plugin[plugin_file_name]
        self.dir_plugin.pop(plugin_file_name)
        self.plugins.pop(plugin_id)

    async def run_event(self, event, *args, wait_time=1, nursery=None):
        if nursery is None:
            self.logger.debug("no nursery exist, spawn nursery now")
            async with trio.open_nursery() as nursery:
                await self.event_manager.run_event(event, wait_time, nursery, self.server_interface, *args)
        else:
            await self.event_manager.run_event(event, wait_time, nursery, self.server_interface, *args)

    async def plugin_run_event(self, event, plg_id, *args, wait_sec=1, nursery=None):
        server = self.server_interface
        if nursery is None:
            self.logger.debug("no nursery exist, spawn nursery now")
            async with trio.open_nursery() as nursery:
                await self.event_manager.plugin_run_event(event, plg_id, nursery, server, *args, wait_time=wait_sec)
        else:
            await self.event_manager.plugin_run_event(event, plg_id, nursery, server, *args, wait_time=wait_sec)
