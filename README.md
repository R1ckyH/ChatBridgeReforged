# Chatbridgerforged
- Alpha version, please bear the risk if you use it
- v0.0.1-Alpha
- only tested for python 3.7 and 3.8
- python version should be 3.5+
- `pip install trio` to install [trio](https://trio.readthedocs.io/)
## Compare to [ChatBridge](https://github.com/TISUnion/ChatBridge)
- Better logging(maybe)
- use [trio](https://trio.readthedocs.io/) for Asynchronous processing
- more feature will be release in the future
  - plugin system will launch soon
- support to [Chatbridge](https://github.com/TISUnion/ChatBridge) clients so far
- [Ricky](https://github.com/rickyhoho) is a suck author
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
