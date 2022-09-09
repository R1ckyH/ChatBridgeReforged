"""
Advanced text container for Minecraft
Credit: Pandaria98
Github: https://github.com/Pandaria98
        https://github.com/TISUnion/stext
Credit: Fallen-Breath
Github: https://github.com/Fallen-Breath
        https://github.com/Fallen-Breath/MCDReforged
Notice, this is not the full code in MCDR,
so part of the function will not be support by ChatBridgeReforged

Formatted by XiaoHuiHui
"""

import json
import re
import typing
from enum import Enum, auto
from typing import (TYPE_CHECKING, Any, Dict, Iterable, List, NamedTuple,
                    Optional, Tuple, Union)

if TYPE_CHECKING:
    # Due to some reason, define JSON type for Python
    # is not a easy thing to do.
    # Some discussions here: https://github.com/python/typing/issues/182
    JSON = Union[None, float, str, List[Any], Dict[str, Any]]


class RAction(Enum):
    suggest_command = auto()
    run_command = auto()
    open_url = auto()
    open_file = auto()
    copy_to_clipboard = auto()


class RTextBase:

    def to_json_object(self) -> JSON:
        raise NotImplementedError()

    def to_json_str(self) -> str:
        return json.dumps(self.to_json_object(), ensure_ascii=False)

    def to_plain_text(self) -> str:
        raise NotImplementedError()

    def to_colored_text(self) -> str:
        raise NotImplementedError()

    def copy(self) -> 'RTextBase':
        raise NotImplementedError()

    def set_click_event(self, action: RAction, value: str) -> 'RTextBase':
        raise NotImplementedError()

    def set_hover_text(self, *args: object) -> 'RTextBase':
        raise NotImplementedError()

    def c(self, action: RAction, value: str) -> 'RTextBase':
        return self.set_click_event(action, value)

    def h(self, *args: object) -> 'RTextBase':
        return self.set_hover_text(*args)

    def __str__(self) -> str:
        return self.to_plain_text()

    def __add__(self, other: object) -> 'RTextList':
        return RTextList(self, other)

    def __radd__(self, other: object) -> 'RTextList':
        return RTextList(other, self)

    @staticmethod
    def from_any(text: object) -> 'RTextBase':
        """
        :param text: can be a RTextBase, or a str, or anything
        :rtype: RTextBase
        """
        if isinstance(text, RTextBase):
            return text
        return RText(text)

    @staticmethod
    def join(divider: Any, iterable: Iterable[Any]) -> 'RTextBase':
        result = RTextList()
        for i, item in enumerate(iterable):
            if i > 0:
                result.append(divider)
            result.append(item)
        return result

    @staticmethod
    def format(fmt: str, *args: object, **kwargs: object) -> 'RTextBase':
        lsargs = list(args)
        kwargs = kwargs.copy()
        counter = 0
        rtext_elements: List[Tuple[str, RTextBase]] = []

        def get():
            nonlocal counter
            rv = '@@MCDR#RText.format#Placeholder#{}@@'.format(counter)
            counter += 1
            return rv

        for i, arg in enumerate(lsargs):
            if isinstance(arg, RTextBase):
                placeholder = get()
                rtext_elements.append((placeholder, arg))
                lsargs[i] = placeholder
        for key, value in kwargs.items():
            if isinstance(value, RTextBase):
                placeholder = get()
                rtext_elements.append((placeholder, value))
                kwargs[key] = placeholder

        texts = [fmt.format(*args, **kwargs)]
        for placeholder, rtext in rtext_elements:
            new_texts: List[Any] = []
            for text in texts:
                processed_text: List[Any] = []
                # if isinstance(text, str):
                for j, ele in enumerate(text.split(placeholder)):
                    if j > 0:
                        processed_text.append(rtext)
                    processed_text.append(ele)
                # else:
                #     processed_text.append(text)
                new_texts.extend(processed_text)
            texts = new_texts
        return RTextList(*texts)


class _ClickEvent(NamedTuple):
    action: RAction
    value: str


class RText(RTextBase):

    def __init__(self, text: object) -> None:
        self.__text: str = str(text)
        self.__click_event: Optional[_ClickEvent] = None
        self.__hover_text_list: List[Any] = []

    def _copy_from(self, text: 'RText') -> None:
        self.__text = text.__text
        self.__click_event = text.__click_event
        self.__hover_text_list = text.__hover_text_list.copy()

    def set_click_event(self, action: RAction, value: str) -> 'RText':
        self.__click_event = _ClickEvent(action, value)
        return self

    def set_hover_text(self, *args: object) -> 'RText':
        self.__hover_text_list = list(args)
        return self

    def to_json_object(self) -> JSON:
        obj: Dict[str, Any] = {
            'text': self.__text,
        }
        if self.__click_event is not None:
            obj['clickEvent'] = {
                'action': self.__click_event.action.name,
                'value': self.__click_event.value
            }
        if len(self.__hover_text_list) > 0:
            obj['hoverEvent'] = {
                'action': 'show_text',
                'value': {
                    'text': '',
                    'extra':
                    RTextList(*self.__hover_text_list).to_json_object(),
                }
            }
        return obj

    def to_plain_text(self) -> str:
        return self.__text

    def copy(self) -> 'RText':
        copied = RText('')
        copied._copy_from(self)
        return copied


class RTextList(RTextBase):

    def __init__(self, *args: object) -> None:
        self.header = RText('')
        self.header_empty = True
        self.children: List[RTextBase] = []
        self.append(*args)

    def set_click_event(self, action: RAction, value: str) -> 'RTextList':
        self.header.set_click_event(action, value)
        self.header_empty = False
        return self

    def set_hover_text(self, *args: object) -> 'RTextList':
        self.header.set_hover_text(*args)
        self.header_empty = False
        return self

    def append(self, *args: object) -> 'RTextList':
        for obj in args:
            if isinstance(obj, RTextList):
                self.children.extend(obj.children)
            elif isinstance(obj, RTextBase):
                self.children.append(obj)
            else:
                self.children.append(RText(obj))
        return self

    def is_empty(self) -> bool:
        return len(self.children) == 0

    def to_json_object(self) -> JSON:
        ret = ['' if self.header_empty else self.header.to_json_object()]
        ret.extend(map(lambda rtext: rtext.to_json_object(), self.children))
        return ret

    def to_plain_text(self) -> str:
        return ''.join(map(lambda rtext: rtext.to_plain_text(), self.children))

    def to_colored_text(self) -> str:
        return ''.join(
            map(lambda rtext: rtext.to_colored_text(), self.children)
        )

    def copy(self) -> 'RTextList':
        copied = RTextList()
        copied.header = self.header.copy()
        copied.header_empty = self.header_empty
        copied.children = [child.copy() for child in self.children]
        return copied


def rtext_json_to_text(raw_text: str, replace_special_symbol: bool = True):
    try:
        data: JSON = json.loads(raw_text)
    except Exception:
        return raw_text
    text = ""
    if type(data) == list:
        for i in typing.cast(List[Any], data):
            if i != "":
                text += i["text"]
    elif type(data) == dict:
        text = typing.cast(Dict[str, Any], data)["text"]
    if replace_special_symbol:
        return re.sub(r"§.", "", text)
    else:
        return text
