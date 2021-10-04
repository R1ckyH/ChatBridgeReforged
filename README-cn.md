**中文** | [English](https://github.com/rickyhoho/ChatBridgeReforged/blob/master/README.md)

# ChatBridgeReforged

## 简介

重新定义跨服聊天。

令世人大为震惊的 ChatBridgeReforged 总是出其不意地为你带来骇人听闻的新特性从而使得你虎躯一震并惊呼真神奇。

### 大家怎么说

- **Alex3236**: CBR 真是令人难忘，我用过一次就把它丢掉了。
- **Foo**: 只有收废品的人才愿意使用 CBR，因为它在我的废纸篓里躺着。

### CBR 是否值得一用？

尽管 CBR 的评价如此美妙，但我们仍然建议你尝试，这样你的废纸篓就会多一名新成员了。

### 提示

只有使用过 CBR 的人才真正使用过 ChatBridgeReforged。

## ⚠️警告

- 插件仍处于测试阶段，如果你用这个插件导致服炸了，不赔钱
- 你的 Python 版本要能装得上 MCDReforged，不然别想用
- 如果你不想被骂，建议提前 `pip install -r requirements.txt` 安装前置

## 示意图
  ![image](./CBR.svg)

## CBR 是如何吊打 [ChatBridge](https://github.com/TISUnion/ChatBridge) 的

- 使用 [trio](https://trio.readthedocs.io/) 进行异步处理。
- 更多的功能还在咕咕咕
- [Ricky](https://github.com/rickyhoho) 是个菜鸡。
  - 但他会尽力维护这玩意。
  - 请为他加油，这样他就会很高兴地继续咕咕咕。

## 配置

编辑那该死的 `config.yml`。

### server_setting - 服务端设置
`Dict`

| config | data type | description |
|----|----|----|
| host_name | `string`| 服务端 IP |
| port | `int` | 服务端端口 |
| aes_key | `string` | AES 密钥 |

### clients - 客户端设置
`list`

| config | data type | description |
|----|----|----|
| name | `string` | 客户端叫啥 |
| password | `string`| 客户端密码 |
| config | data type | 客户端简介 |

### debug - 调试设置
`Dict`

| config | data type | description |
|----|----|----|
| all | `bool` | 调试模式 |
| CBR | `bool` | 调试模式 |
| plugin | `bool` | 调试模式 |

## 酷Q协议

[cqhttp 文档](https://github.com/rickyhoho/ChatBridgeReforged/tree/master/doc/cqhttp.md)

## 插件

[插件文档](https://github.com/rickyhoho/ChatBridgeReforged/tree/master/doc/plugin.md)

插件库还在鸽。
