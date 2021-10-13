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
| on_load(CBRInterface) | A plugin gets loaded | YES | The new plugin inherits information from the old plugin |
| on_unload(CBRInterface) | A plugin gets unloaded | YES | Clean up or turn off functionality of the old plugin |
| on_message(CBRInterface, MessageInfo) | A message action have been receive in server | YES | Response to the message from the clients |
| on_command(CBRInterface, MessageInfo) | A command action have been receive in server | YES | Response to the command from the server |
| on_player_joined(CBRInterface, player, MessageInfo) | A player joined the server | No | Response to player joining with the given info instance |
| on_player_left(CBRInterface, player, MessageInfo) | A player left the server | No | Response to player leaving |

Note: the plugin doesn't need to implement all methods above. **Just implement what you need**

Among them, the information of each parameter object is as follows:

### server

**Read `cbr/plugin/cbrinterface.py` to help you understand its functionality**

This is an object for the plugin to interact with the server. It belongs to the ServerInterface class in `cbr/plugin/cbrinterface.py`

It has the following variables:

| Variable | Type | Usage |
|---|---|---|
| logger | modified `CBRLogger` with only `info`, `error`, `warning` and `debug` | A logger of CBR. It is better to use `server.logger.info (message)` instead of `print (message)` to output information to the console. |
| cbr_logger | CBRLogger(like `logging.Logger`) | A logger of CBR like [logger](https://docs.python.org/3/library/logging.html#logger-objects)| |
| logger.chat | CBRLogger | A new constant of cbr using to log chat message |
It also has these following functions:

**Server Control TODO in future**

| Function | Usage |
|---|---|
| get_server_pid() | Return the pid of the server process. Notes the process with this pid is a bash process, which is the parent process of real server process you might be interested in |

**Text Interaction**

| Function | Usage |
|---|---|
| send_message(msg, target) | Send `msg` to `target` server |
| tell_message(msg, target, player) | Send `msg` to `player` in `target` server |
| reply(msg, MessageInfo) | replay `msg` to `MessageInfo` sender |
| send_custom_message(target, msg, client, player) | Send custom message to target server **NOT recommend to use unless you know what you are doing** |
| execute_command(command, targets) | Execute `command` in `target` server without waiting result |
| execute_mcdr_command(command, targets) | Execute `mcdr` `command` in `target` server without waiting result **only work with command that starts with `!!` now** |
| command_query | Send a string `command` to `target`(`str`) to use `rcon_query`. Will wait at most 2 second for result, return `result`(str) if success, else return `None` |
| servers_command_query(command, targets) | Send strings `command` to `targets`(`list`) to use `rcon_query`. Will wait at most 2 second for result, return `results`(dict) if success, else return `None` |
| api_query(target, plugin_id, function_name, keys) | query for get the result of api in mcdr plugin, function name can include package name, keys is a list which store non object value. Will wait at most 2 second for result, return `result`(str/bool/list/dict) if success, else return `None`  |

**Other**

| Function | Usage |
|---|---|
| get_permission_level(obj) | todo |
| set_permission_level(player, level) | todo |
| register_help_message(prefix, message) | Add a help message with prefix `prefix` and message `message` to the `##help` data of CBR. The `##help` data of CBR will be reset before plugin reloading **(todo)** . **It is recommended to add relevant information in `on_load ()` method call.** |
| get_client_type() | get `type` that client register at login. `client` will **register** `type` itself while **login** if need |
| is_client_online(client) | Check `client` is **online** or not. |
| get_online_clients() | get list of `online` clients |
| is_mc_client(client) | Check `client` **register** as `mc` or not. |
| get_mc_clients() | get list of `mc` clients |
| is_client_online(client) | Check `client` is **online** or not |
| get_online_mc_clients() | get list of **online** `mc` clients |

### info

This is a parsed information object. It belongs to the Info class in `cbr/plugin/info.py`. It has the following attributes:

| Attribute | Content |
|---|---|
| content | If the info is player's chat message, the value is the player's chat content. Otherwise, the value is a string that server receive from tcp |
| sender | If the info is player's chat message, the value is a string representing the player's name, otherwise `''` |
| source_client | A `string` that represent the sender clients |
| client_type | Ａ`string` that represent the `type` that **register** when `client` **login** | 
| is_player() | Equivalent to `player != ''` |
| extra | A place for storing special message that plugin want to store when communicate. It wont effect the message sending. **May delete at future version** |
| should_send_message() | let the message continues to send other mc server |
| cancel_send_message() | let the message cancel to send other mc server |

### Samples

For the following message from the message's standard output：

`[CBR] [09:00:00] [MainThread/INFO]: [survival] <TFC> Welcome to TFC`

The attributes of the info object are:

| Attribute | Value |
|---|---|
| content | `Welcome to TFC` |
| sender | `TFC` |
| source_client | `survival` |
| client_type | `mc` |
| is_player() | `True` |

------

For the following message from the message's standard output：

`[CBR] [09:00:00] [MainThread/INFO]: [CBR] TFC QQ : 1073626979`

The attributes of the info object are:

| Attribute | Value |
|---|---|
| content | `TFC QQ : 1073626979` |
| sender | ``|
| source_client | `CBR` |
| client_type | `` |
| is_player() | False |

## Some tips for writing plugin

- The current working directory is the folder where CBR is in. **DO NOT** change it since that will mess up everything
- For the `info` parameter in `on_message` don't modify it, just only read it
- Call `server.register_help_message()` in `on_load()` to add some necessary tips for your plugin so the player can use `!!help` command to know about your plugin **TODO**
- Keep the environment clean. Store your data files in a custom folder in `plugins/`, your config file in `config/` folder and your log file in `log/` folder will be a good choice
- `on_unload()` allows you to have as many times as you want to save your data, **never stuck it**. Be carefully, don't enter an endless loop, CBR will waiting for you to finish

## Something I want to say
- if you want to contact me, please find me with discord `rickyho#0941` or
find me in MCDR discuss group
- Please give me a `star` if you like this project
- If you have some good idea, please share it to me
- plugin.md copy and edit form [MCDR](https://github.com/Fallen-Breath/MCDReforged)
- Thx [Fallen_Breath](https://github.com/Fallen-Breath)