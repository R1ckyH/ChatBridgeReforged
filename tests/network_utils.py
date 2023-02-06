import pytest
from pytest_lazyfixture import lazy_fixture

from basic_fixture import *
from fake_class import *

import cbr.resources.formatter as CBRFormatter

from cbr.net.encrypt import AESCryptor
from cbr.net.network import Network
from cbr.net.process import ClientProcess
from cbr.net.tcpserver import CBRTCPServer
from cbr.lib.client import Client

from chatbridgereforged_mc.net.network import Network as CBR_MC_PYZ_Network
from chatbridgereforged_mc.net.tcpclient import CBRTCPClient as CBR_MC_PYZ_CBRTCPClient
from chatbridgereforged_mc.net.encrypt import AESCryptor as CBR_MC_PYZ_Cryptor


@pytest.fixture(params=[CBR_MC_PYZ_CBRTCPClient, CBR_MC.CBRTCPClient, CBR_CQ.CBRTCPClient])
def client(request):
    return request.param


@pytest.fixture
def fake_client(client, key):
    CBR_client = client(FakeClientConfig(key), logger)
    CBR_client.connected = True
    CBR_client.ping_guardian = Fake_guardian()
    return CBR_client


@pytest.fixture(params=[CBR_MC_PYZ_Network, CBR_MC.Network, CBR_CQ.Network])
def client_network(request):
    return request.param


def fake_server_config(key) -> TypedServerConfig:
    return {
        "host_name": "0.0.0.0",
        "port": 30001,
        "aes_key": key
    }


@pytest.fixture
def fake_server(key):
    tcpserver = CBRTCPServer(logger, fake_server_config(key), {"test": Client("test", "password")})
    process = ClientProcess(tcpserver, logger)
    process.current_client = "test"
    process.cancel_scope = None
    tcpserver.clients["test"].process = process
    return tcpserver


@pytest.fixture
def fake_connection():
    return FakeStreamSocket(NAME)


@pytest.fixture(params=[Network, lazy_fixture('client_network')])
def network(request, key, fake_client):
    if request.param == Network:
        return request.param(logger, key, {NAME: Client(NAME, "testing")})
    else:
        return request.param(key, fake_client)


@pytest.fixture(params=[AESCryptor, CBR_MC_PYZ_Cryptor, CBR_MC.AESCryptor, CBR_CQ.AESCryptor])
def cryptor(key, request):
    return request.param(key, logger)


@pytest.fixture
def cryptor2(cryptor):
    return cryptor
