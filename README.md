# Chatbridgerforged
- v0.0.1-Alpha004
- only tested for python 3.7.3 and 3.8.6
- python version should be 3.5+
## Compare to [ChatBridge](https://github.com/TISUnion/ChatBridge)
- Better logging
- use [asyncio](https://docs.python.org/3/library/asyncio.html) for Asynchronous processing
- more feature will be release in the future
  - plugin system will luanch
- support to [Chatbridge](https://github.com/TISUnion/ChatBridge) clients so far
## Config
`edit config.yml for config`
|config|data type| descritpion |
|-|-|-|
|server-setting| `dict` | basic setting of server|
|ip address|`string`| ip address for hosting|
|port| `int` | port for hosting|
|aes_key| `string` | key for `AES` encrytion|
|clients| `list` | list of clients|
|name| `string` | name of client|
|password| `string`| password of client|
|debug| `dict` | debug mode|
|all| `bool` | debug mode switch|
|CBR| `bool` | not available to use now|
|plugin| `bool` | not available to use now|
