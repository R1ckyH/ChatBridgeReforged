ChatBridgeReforged Plugin Document
---
copy and edit form [MCDR](https://github.com/Fallen-Breath/MCDReforged)

Thx [Fallen_Breath](https://github.com/Fallen-Breath)

Like MCDaemon and MCDR's single file plugin, a CBR plugin is a `.py` file locating in the `plugins/` folder. CBR will automatically load every plugin inside this folder

There is a sample plugin named `not_sample_plugin.py` in the `plugins/` folder, and you can check its content for reference

## Event

When the server has trigger specific event, CBR will call relevant `Function` of each plugin if the plugin has declared the method. CBR will create a separated thread for the called method to run

| Function | When to call | Available | Reference usage |
|---|---|---|---|
| on_load(server, old_module) | A plugin gets loaded | No | The new plugin inherits information from the old plugin |
| on_unload(server) | A plugin gets unloaded | No | Clean up or turn off functionality of the old plugin |
| on_message(server, info) | A message action have been receive in server | YES | Response to the message from the clients |
| on_player_joined(server, player, info) | A player joined the server | No | Response to player joining with the given info instance |
| on_player_left(server, player, info) | A player left the server | No | Response to player leaving |

Note: the plugin doesn't need to implement all methods above. Just implement what you need

Among them, the information of each parameter object is as follows:

### server

**Read `cbr/plugin/server_interface.py` to help you understand its functionality**

This is an object for the plugin to interact with the server. It belongs to the ServerInterface class in `cbr/plugin/server_interface.py`

It has the following constants:

It has the following variables:

| Variable | Type | Usage |
|---|---|---|
| logger | (CBRLogger)logging.Logger | A logger of CBR. It is better to use `server.logger.info (message)` instead of `print (message)` to output information to the console. [docs](https://docs.python.org/3/library/logging.html#logger-objects)

It also has these following methods:

**Server Control**

| Function | Usage |
|---|---|
| stop() | Stop CBR server and exit |
| get_server_pid() | Return the pid of the server process. Notes the process with this pid is a bash process, which is the parent process of real server process you might be interested in |

**Text Interaction**

| Function | Usage |
|---|---|
| send_command(target, command) | Send a string `command` to `target`(`str`) to use `rcon_query`. Will wait at most 2 second for result, return `result`(str) if success, else return `None`|
| send_servers_command(targets, command) | Send strings `command` to `targets`(`list`) to use `rcon_query`. Will wait at most 2 second for result, return `results`(dict) if success, else return `None`|
| send_msg(target, msg) | Send msg to `target` server|
| tell_msg(target, player, text) | todo|

**Other**

| Function | Usage |
|---|---|
| get_permission_level(obj) | todo |
| set_permission_level(player, level) | todo |
| add_help_message(prefix, message) | Add a help message with prefix `prefix` and message `message` to the `##help` data of CBR. The `##help` data of CBR will be reset before plugin reloading. **It is recommended to add relevant information in `on_load ()` method call.** |
| is_client_online(client) | Check `client` is online or not |
| is_mc_client(client) | Check `client` is `mc_client` or not. **`client` will register itself as `mc_client` if need** |
| is_client_online(client) | Check `client` is online or not |
| get_online_clients() | get list of `online` clients|
| get_mc_clients() | get list of `mc` clients|
| get_online_mc_clients() | get list of `online` `mc` clients|

### info

This is a parsed information object. It belongs to the Info class in `cbr/plugin/info.py`. It has the following attributes:

| Attribute | Content |
|---|---|
| content | If the info is player's chat message, the value is the player's chat content. Otherwise, the value is a string that server receive from tcp |
| player | If the info is player's chat message, the value is a string representing the player's name, otherwise `''` |
| client | A `string` that represent the sender clients |
| is_player() | Equivalent to `player != ''` |
| should_send_message() | let the message continues to send other mc server |
| cancel_send_message() | let the message cancel to send other mc server |

### Samples

For the following message from the message's standard output：

`[CBR][09:00:00][MainThread/INFO]: [survival] <TFC> Welcome to TFC`

The attributes of the info object are:

| Attribute | Value |
|---|---|
| content | `Welcome to TFC` |
| player | `TFC` |
| client | `survival` |
| is_player() | True |

------

For the following message from the message's standard output：

`[CBR][09:00:00][MainThread/INFO]: [CBR] TFC QQ : 1073626979`

The attributes of the info object are:

| Attribute | Value |
|---|---|
| content | `TFC QQ : 1073626979` |
| player | `''`|
| client | `CBR` |
| is_player() | False |

## Some tips for writing plugin

- The current working directory is the folder where CBR is in. **DO NOT** change it since that will mess up everything
- For the `info` parameter in `on_message` don't modify it, just only read it
- Call `server.add_help_message()` in `on_load()` to add some necessary tips for your plugin so the player can use `!!help` command to know about your plugin **TODO**
- Keep the environment clean. Store your data files in a custom folder in `plugins/`, your config file in `config/` folder and your log file in `log/` folder will be a good choice
- `on_unload()` allows you to have as many times as you want to save your data, **never stuck it**. Be carefully, don't enter an endless loop, CBR will waiting for you to finish

## Something I want to say
- if you want to contact me, please find me with discord `rickyho#0941` or
find me in MCDR discuss group
- Please give me a `star` if you like this project
- If you have some good idea, please share it to me
- copy and edit form [MCDR](https://github.com/Fallen-Breath/MCDReforged)
- Thx [Fallen_Breath](https://github.com/Fallen-Breath)