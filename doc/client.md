Client Document
---

**it is a self decision to use other clients or not**

**CBR CQHTTP Client is available for most of the one_bot v9 qq bot with websocket**

**Discord Client and KHL Client are only available with their official bot token**

it is managed by `plugin/[Client_Name].py` or `plugin/ChatBridgeReforged_[Client_Name].py` right now.

To use them in CBR, you should use the plugin `[Client_Name].py` as manager and run they independently or `ChatBridgeReforged_[Client_Name].py` as plugin, 

Of course, you can modify it if you want

## Simple setup for CBR Clients

setup [go-cqhttp](https://github.com/Mrs4s/go-cqhttp) as websocket server

CBR cqhttp client is work as a websocket client

Things you need to do
- setup a bot like [go-cqhttp](https://github.com/Mrs4s/go-cqhttp) / [Discord](https://discord.com/developers/applications) / [KHL](https://www.kaiheila.cn/)

- CBR cqhttp client is a websocket client connect to cq bot

- CBR [Discord](https://discord.com/developers/applications) / [KHL](https://www.kaiheila.cn/) client is a client connect to bot with their own library with bot token


- edit config `[Client_Name].json`


- edit config `ChatBridgeReforged_[Client_Name].json`.