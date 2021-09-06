# ChatBridgeReforged

- Beta version, please bear the risk if you use it
- v0.0.1-Beta
- only tested for python 3.7 and 3.8
- python version should be 3.6+
- `pip install -r requirements.txt` to install requirements!

## Compare to [ChatBridge](https://github.com/TISUnion/ChatBridge)

- Better logging(maybe)
- use [trio](https://trio.readthedocs.io/) for Asynchronous processing
- more feature will be release in the future
  - permission system will launch soon
- support to [ChatBridge](https://github.com/TISUnion/ChatBridge) clients so far
  - Some function in ChatBridge will not be supported
- [Ricky](https://github.com/rickyhoho) is a suck author
  - But he will try his best to maintain this repository
  - Please cheer him so that he will be happy to maintain this repository

## Config

`edit config.yml for config`

| config | data type | description |
|----|----|----|
| server-setting | `dict` | basic setting of server |
| host_name | `string`| ip address for hosting |
| port | `int` | port for hosting |
| aes_key | `string` | key for `AES` encryption |
| clients | `list` | list of clients |
| name | `string` | name of client |
| password | `string`| password of client |
| debug | `dict` | debug mode |
| all | `bool` | debug mode switch |
| CBR | `bool` | debug mode switch |
| plugin | `bool` | debug mode switch |

## cqhttp
[cqhttp document](https://github.com/rickyhoho/ChatBridgeReforged/tree/master/doc/cqhttp.md)

## Plugin

[Plugin document](https://github.com/rickyhoho/ChatBridgeReforged/tree/master/doc/plugin.md)