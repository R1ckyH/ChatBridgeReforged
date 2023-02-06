import pytest

from cbr.lib.logger import CBRLogger

import ChatBridgeReforged_MC as CBR_MC
import ChatBridgeReforged_cqhttp as CBR_CQ

NAME = "TESTING"
logger = CBRLogger(NAME)
# logger.debug_config['all'] = True


@pytest.fixture(params=["", "rickyho555"])
def player(request):
    return request.param


@pytest.fixture(params=["{}", "{test: test}", "test"])
def message(request):
    return request.param


@pytest.fixture(params=["", "test"])
def text(request):
    return request.param


@pytest.fixture(params=["", "key"])
def key(request):
    return request.param
