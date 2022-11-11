# ChatBridgeReforged

- only tested for python 3.7 and 3.8
- python version should be 3.7+
- `pip install -r requirements.txt` to install requirements!
- Please give a **star** if you like this repository
- Preview version at [ChatBridgeReforged_preview](https://github.com/R1ckyH/ChatBridgeReforged/tree/test)

  ![image](./CBR.svg)

## Compare to [ChatBridge](https://github.com/TISUnion/ChatBridge)

- use [trio](https://trio.readthedocs.io/) for Asynchronous processing
- more feature will be release in the future
- not support to [ChatBridge](https://github.com/TISUnion/ChatBridge) clients in release
- [Ricky](https://github.com/R1ckyH) is a suck author
  - But he will try his best to maintain this repository
  - Please cheer him so that he will be happy to maintain this repository

## Basic

use `##help` to get plugin help command

use `##CBR` to get help command

#### CBR Server setup
Put all ChatBridgeReforged server files in a directory like
```
ChatBridgeReforged
-cbr
-ChatBridgeReforged_Server.py
```
Start server with run `ChatBridgeReforged_Server.py`

Put `ChatBridgeReforged_MC.py` in MCDR's plugins file

Setup `config.yml` in previous directory and `config/ChatBridgeReforged_MC.json` in MCDR's directory


## Config

`edit config.yml for config`

### server_setting
`Dict`

| config    | data type | description              |
|-----------|-----------|--------------------------|
| host_name | `string`  | ip address for hosting   |
| port      | `int`     | port for hosting         |
| aes_key   | `string`  | key for `AES` encryption |

### clients
`list`

| config   | data type | description        |
|----------|-----------|--------------------|
| name     | `string`  | name of client     |
| password | `string`  | password of client |

### log
`Dict`

| config           | data type | description                           |
|------------------|-----------|---------------------------------------|
| size_to_zip      | `double`  | size to zip the file `latest.log`(kb) |
| split_log        | `bool`    | split log to chat log and normal log  |
| size_to_zip_chat | `bool`    | size to zip the file `chat.log`(kb)   |

### debug
`Dict`

| config | data type | description       |
|--------|-----------|-------------------|
| all    | `bool`    | debug mode switch |
| CBR    | `bool`    | debug mode switch |
| plugin | `bool`    | debug mode switch |

## cqhttp

[cqhttp document](./doc/cqhttp.md)

## Plugin

[Plugin document](./doc/plugin.md)

Plugin Catalogue will launch soon
