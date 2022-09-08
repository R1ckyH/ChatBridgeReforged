from typing import List, TypedDict


class TypedServerConfig(TypedDict):
    host_name: str
    port: int
    aes_key: str


class TypedClientsConfig(TypedDict):
    name: str
    password: str


class TypedLogConfig(TypedDict):
    size_to_zip: int
    split_log: bool
    size_to_zip_chat: int


class TypedDebugConfig(TypedDict):
    all: bool
    CBR: bool
    plugin: bool


class TypedConfig(TypedDict):
    server_setting: TypedServerConfig
    clients: List[TypedClientsConfig]
    log: TypedLogConfig
    debug: TypedDebugConfig


class TypedConfigStruct(TypedDict):
    name: str
    sub_structure: List["TypedConfigStruct"]
