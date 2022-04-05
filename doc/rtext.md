ChatBridgeReforged rtext Document
---
this doc is copy and edit form [MCDR](https://github.com/Fallen-Breath/MCDReforged)

Thx [Fallen_Breath](https://github.com/Fallen-Breath)

**Only part of [rtext](https://github.com/Fallen-Breath/MCDReforged/blob/master/mcdreforged/minecraft/rtext.py) function have been included in ChatBridgeReforged's rtext**

## rtext.py

`from cbr.plugin.rtext import *`

Recommend reading the page [Raw JSON text format](https://minecraft.gamepedia.com/Raw_JSON_text_format) in Minecraft Wiki first

This is an advance text component library for Minecraft

modify from the [rtext](https://github.com/Fallen-Breath/MCDReforged/blob/master/mcdreforged/minecraft/rtext.py) by [Fallen_Breath](https://github.com/Fallen-Breath) with GNU LGPL LICENCE v3.0

[rtext](https://github.com/Fallen-Breath/MCDReforged/blob/master/mcdreforged/minecraft/rtext.py) Inspired by the [MCD stext API](https://github.com/TISUnion/rtext) made by [Pandaria98](https://github.com/Pandaria98)

### RAction

`RAction` stores all click event actions

- `RAction.suggest_command`
- `RAction.run_command`
- `RAction.open_url`
- `RAction.open_file`
- `RAction.copy_to_clipboard`

### RTextBase

The base class of `RText` and `RTextList`

#### RTextBase.to_json_object()

Return a `dict` representing its data

#### RTextBase.to_json_str()

Return a json formatted `str` representing its data. It can be used as the second parameter in command `/tellraw <target> <message>` and more

#### RTextBase.to_plain_text()

Return a plain text for console display. Click event and hover event will be ignored

#### RTextBase.__str__()

Return `RTextBase.to_plain_text()`

#### RTextBase.__add__, RTextBase.__radd__

Return a `RTextList` created by merging two operand

### RText

The text component class

#### RText.RText(text, color=RColor.reset, styles=None)

Create a RText object with specific text and color. `styles` can be a `RStyle` or a `list` of `RStyle`

#### Rtext.set_click_event(action, value) -> RText

Set the click event to action `action` and value `value`

`action` and `value` are both `str`

Return the RText itself after applied the click event

#### RText.c(*args) -> RText

The same as `RText.set_click_event`

#### RText.set_hover_text(*args) -> RText

Set the hover text to `*args`

Parameter `*args` will be used to create a `RTextList` instance. For the restrictions check the constructor of `RTextList` below

Return the RText itself after applied the hover text

#### RText.h(*args) -> RText

The same as `RText.set_hover_text`

### RTextList

It's a list of RText

When converted to json object for displaying to the game it will at an extra empty string at the front to prevent the first object's style affecting the later ones

#### RTextList.RTextList(*args)

Objects in `*args` can be a `str`, a `RText`, a `RTextList` or any classes implemented `__str__` method. All of them will be convert to `RText`

---------

`RTextBase` objects can be used as the message parameter in plugin APIs as below:

- `server.tell`
- `server.say`
- `server.reply`
- `add_help_message`

Special judge for console output is unnecessary since `server.reply` etc. will convert `RTextBase` objects into plain text

#### RTextList.append(*args)

Add several elements to the end of the current `RTextList`

Objects in `*args` can be a `str`, a `RText`, a `RTextList` or any classes implemented `__str__` method. All of them will be convert to `RText`
