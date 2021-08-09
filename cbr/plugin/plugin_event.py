"""
    event
"""
import trio

from typing import TYPE_CHECKING

from cbr.lib.logger import CBRLogger
from cbr.plugin.serverinterface import ServerInterface

if TYPE_CHECKING:
    from cbr.plugin.plugin import Plugin

class PluginEvent:
    def __init__(self, event, logger : CBRLogger):
        self.event = event
        self.logger = logger
        self.register_event_plugins = {}

    def register_all_plugins(self, plugin_dict):
        self.register_event_plugins = {}
        for i in plugin_dict:
            plugin : 'Plugin' = plugin_dict[i]
            if hasattr(plugin.instance, self.event):
                self.register_event_plugins.update({plugin.id : plugin})

    async def plugin_run_event(self, serverinterface : ServerInterface, *args):
        self.logger.debug(f"Start '{self.event}'")
        async with trio.open_nursery() as nursery:
            for i in self.register_event_plugins:
                plugin : 'Plugin' = self.register_event_plugins[i]
                run = getattr(plugin.instance, self.event)
                nursery.start_soon(self._wait_run, plugin.id, run, serverinterface, *args)
    
    async def _wait_run(self, plugin_id, run, serverinterface : ServerInterface, *args):
        self.logger.debug(f"Start '{self.event}' of {plugin_id}")
        with trio.move_on_after(1) as cancel_scope:
            await trio.to_thread.run_sync(self.__run, run, cancel_scope, serverinterface, *args)
            await trio.sleep(1)
        self.logger.debug(f"Finish '{self.event}' of {plugin_id}")

    def __run(self, run, cancel_scope : trio.CancelScope, serverinterface : ServerInterface, *args):
        try:
            run(serverinterface, *args)
        except:
            self.logger.bug(exit_now = False, error = True)
        trio.from_thread.run_sync(cancel_scope.cancel)

class PluginEventManager:
    def __init__(self, logger : CBRLogger):
        self.events = {}
        self.logger = logger
        self.setup()
    
    def setup(self):
        self.__register_events("on_test")
        self.__register_events("on_message")
        self.__register_events("on_load")
    
    def __register_events(self, event):
        self.events.update({event : PluginEvent(event, self.logger)})
    
    def register_plugins(self, plugin_dict):
        for i in self.events:
            event : PluginEvent = self.events[i]
            event.register_all_plugins(plugin_dict)
    
    async def run_event(self, event, serverinterface : ServerInterface, *args):
        if event not in self.events:
            self.logger.error(f"Event '{event}' haven't been register")
            return
        await self.events[event].plugin_run_event(serverinterface, *args)
        self.logger.debug(f"Finish event '{event}'")