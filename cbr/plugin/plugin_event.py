"""
    event
"""
import trio

from typing import TYPE_CHECKING

from cbr.lib.logger import CBRLogger
from cbr.plugin.cbrinterface import CBRInterface

if TYPE_CHECKING:
    from cbr.plugin.plugin import Plugin


class PluginEvent:
    def __init__(self, event, logger: CBRLogger):
        self.event = event
        self.logger = logger
        self.register_event_plugins = {}

    def register_all_plugins(self, plugin_dict):
        self.register_event_plugins = {}
        for i in plugin_dict:
            plugin: 'Plugin' = plugin_dict[i]
            self.register_plugin(plugin)

    def register_plugin(self, plugin: 'Plugin'):
        if hasattr(plugin.instance, self.event):
            self.register_event_plugins.update({plugin.id: plugin})
            self.logger.debug(f"Plugin {plugin.id} register to event {self.event}", "plugin")

    def remove_plugin(self, plugin_id):
        if plugin_id in self.register_event_plugins.keys():
            self.register_event_plugins.pop(plugin_id)
            self.logger.debug(f"Plugin '{plugin_id}' removed in event '{self.event}'", "plugin")

    async def plugins_run_event(self, wait_time, nursery, server_interface: CBRInterface, *args):
        self.logger.debug(f"Start '{self.event}'", module='plugin')
        async with trio.open_nursery() as nursery2:
            for i in self.register_event_plugins:
                plugin: 'Plugin' = self.register_event_plugins[i]  # TODO permanent plugin
                run = getattr(plugin.instance, self.event)
                nursery2.start_soon(self.wait_run, plugin.id, run, server_interface, nursery, wait_time, *args)
        self.logger.debug(f"Finish event '{self.event}'", module='plugin')

    async def wait_run(self, plugin_id, run, server_interface: CBRInterface, nursery, wait_time=1, *args):
        self.logger.debug(f"Start '{self.event}' of {plugin_id}", module='plugin')
        if wait_time == -1:
            cancel_scope = trio.CancelScope()
        else:
            cancel_scope = trio.move_on_after(wait_time)
        with cancel_scope:
            nursery.start_soon(trio.to_thread.run_sync, self.__run, run, cancel_scope, server_interface, *args)
            await trio.sleep_forever()
        self.logger.debug(f"Finish '{self.event}' of {plugin_id}", module='plugin')

    def __run(self, run_plugin, cancel_scope: trio.CancelScope, server_interface: CBRInterface, *args):
        try:
            run_plugin(server_interface, *args)
        except Exception:
            self.logger.bug(exit_now=False, error=True)
        trio.from_thread.run_sync(cancel_scope.cancel)


class PluginEventManager:
    def __init__(self, logger: CBRLogger):
        self.events = {}
        self.logger = logger
        self.unloading = False
        self.setup()

    def setup(self):
        self.__register_events("on_load")
        self.__register_events("on_unload")
        self.__register_events("on_message")
        self.__register_events("on_command")
        # TODO: on_player_join and on_player_left(may do in 1.0)
        # TODO: register event by plugin(may not do)(may do in 1.0)

    def __register_events(self, event):
        self.events.update({event: PluginEvent(event, self.logger)})

    def register_plugins(self, plugin_dict):
        for i in self.events:
            event: PluginEvent = self.events[i]
            event.register_all_plugins(plugin_dict)

    def register_plugin(self, plugin: 'Plugin'):
        for i in self.events:
            event: PluginEvent = self.events[i]
            event.register_plugin(plugin)

    def remove_plugin(self, plugin_id):
        for i in self.events:
            self.events[i].remove_plugin(plugin_id)

    async def run_event(self, event, wait_time, nursery, server_interface: CBRInterface, *args):
        if event not in self.events:
            self.logger.error(f"Event '{event}' haven't been register")
            return
        if self.unloading and event != 'on_unload':
            self.logger.warning(f"Plugin unloading, event '{event}' skipped")
            return
        await self.events[event].plugins_run_event(wait_time, nursery, server_interface, *args)

    async def plugin_run_event(self, event, plugin_id, nursery, server_interface, *args, wait_time=-1):
        if event not in self.events:
            self.logger.error(f"Event '{event}' haven't been register")
            return
        if self.unloading and event != 'on_unload':
            self.logger.warning(f"Plugin unloading, event '{event}' skipped")
            return
        if plugin_id in self.events[event].register_event_plugins.keys():
            plugin: 'Plugin' = self.events[event].register_event_plugins[plugin_id]
            run = getattr(plugin.instance, event)
            await self.events[event].wait_run(plugin_id, run, server_interface, nursery, wait_time=wait_time, *args)
