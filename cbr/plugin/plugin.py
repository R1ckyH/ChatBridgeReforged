'''
plugin run here
'''

import importlib
import os
import trio

from cbr.lib.logger import CBRLogger
from cbr.plugin.plugin_event import PluginEventManager
from cbr.plugin.serverinterface import ServerInterface

class Plugin:
    def __init__(self, path):
        self.path_name = path
        self.instance = importlib.import_module('plugins.' + path)
        self.setup()

    def setup(self):
        self.last_edit_time = os.path.getmtime(f'./plugins/{self.path_name}.py')
        self.__init_metadata()

    def reload(self):
        self.instance = importlib.reload(self.instance)
        self.setup()

    def __get_default_metadata(self, data = None):
        metadata = {
            'id' : self.path_name,
            'version': '0.0.0',
            'name': self.path_name,
            'description': "A CBR plugin",
            'author': None,
            'link': None,
            'dependencies': None
        }
        if data != None:
            return metadata[data]
        return metadata

    def gen_metadata(self):
        try:
            self.metadata = self.instance.PLUGIN_METADATA
        except:
            self.metadata = self.__get_default_metadata()

    def get_data(self, data):
        try:
            data = self.metadata[data]
        except:
            data = self.__get_default_metadata(data)
        return str(data)

    def __init_metadata(self):
        self.gen_metadata()
        self.id = self.get_data('id')
        self.version = self.get_data('version')
        self.name = self.get_data('name')
        self.description = self.get_data('description')
        self.author = self.get_data('author')
        self.link = self.get_data('link')
        self.dependencies = self.get_data('dependencies')

class PluginManager:
    def __init__(self, serverinterface : ServerInterface, logger : CBRLogger):
        self.serverinterface = serverinterface
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
        self.logger.debug("Start reload plugins")
        plugins = await self.__get_plugin_list()
        for i in plugins:
            await self.unload_plugin(i)
            await self.load_plugin(i)
        self.event_manager.register_plugins(self.plugins)
        self.logger.debug("Finish reload plugins")

    async def unload_plugin(self, plugin_file_name):
        if plugin_file_name in self.dir_plugin:
            self.logger.info(f"Unload plugin {plugin_file_name}")

    async def load_plugin(self, plugin_file_name):
        if plugin_file_name in self.dir_plugin:
            last_edit_time = os.path.getmtime(f'./plugins/{plugin_file_name}')
            plugin : Plugin = self.plugins[self.dir_plugin[plugin_file_name]]
            if plugin.last_edit_time != last_edit_time:
                self.logger.info(f"Reload plugin {plugin_file_name}")
                plugin.reload()
            else:
                self.logger.info(f"Plugin {plugin_file_name} not change")
        else:
            self.logger.info(f"Load plugin {plugin_file_name}")
            plugin_instance = Plugin(plugin_file_name[:-3])
            self.dir_plugin.update( { plugin_file_name : plugin_instance.id } )
            self.plugins[plugin_instance.id] = plugin_instance

    async def run_event(self, event, *args):
        await self.event_manager.run_event(event, self.serverinterface, *args)

if __name__ == '__main__':
    manager = PluginManager()
    trio.run(manager.reload_all_plugins)
    #trio.run(manager.run_event, 'on_test', 123)
    trio.run(manager.run_event, 'on_test2', 123)
    trio.run(manager.run_event, 'on_load', 123)
    input()
    trio.run(manager.reload_all_plugins)
    trio.run(manager.run_event, 'on_test2', 123)