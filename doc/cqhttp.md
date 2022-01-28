cqhttp Document
---

**it is a self decision to use cqhttp or not**

**CBR cqhttp client is available for most of the one_bot v9 qq bot with websocket**

it is managed by `plugin/cqhttp.py` or `plugin/ChatBridgeReforged_cqhttp.py` right now.

To use cqhttp in CBR, you should use the plugin `cqhttp.py` or `ChatBridgeReforged_cqhttp.py` as plugin, 

Of course, you can modify it if you want

## Simple setup for [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)

setup it with websocket

CBR cqhttp client is work as a websocket client

Things you need to do
- setup a qq bot like [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)


- CBR client is a websocket client connect to cq bot


- edit `host`, `port`, and `access-token` in `CQHTTP`'s config


- edit the `config` of CBR `ChatBridgeReforged_cqhttp.py`.


- edit the `config/cqhttp.json` of CBR plugin `cqhttp.py` or `ChatBridgeReforged_cqhttp.py`.