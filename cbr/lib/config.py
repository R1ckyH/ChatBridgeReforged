"""
CBR config file stuffs
"""
import shutil

from os import path
from ruamel import yaml
#from ruamel.yaml.comments import CommentedMap
from cbr.lib.logger import CBRLogger

CHATBRIDGEREFORGED_VERSION = '0.0.1-Alpha007-fix2'
DEFAULT_CONFIG_PATH = "cbr/resources/defaultconfig.yml"
CONFIG_PATH = "config.yml"
CONFIG_STRUCTURE = [
    {'name' : 'server_setting',
        'sub_structure' : [
            {'name' : 'ip_address',},
            {'name' : 'port',},
            {'name' : 'aes_key',},
        ]
    },
    {'name' : 'debug',
        'sub_structure':[
            {'name' : 'all',},
            {'name' : 'CBR',},
            {'name' : 'plugin',},
        ]
    },
    {'name' : 'clients',}
]


class Config:
    def __init__(self):
        self.data = {}
    
    def getdata(self):
        if path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as cf:
                self.data = yaml.safe_load(cf)
            self.data.update({'version' : CHATBRIDGEREFORGED_VERSION})
            return True
        else:
            return False


class Config_check:
    def __init__(self, logger : CBRLogger, config : Config):
        self.logger = logger
        self.config = config
        self.check_all()
    
    def check_all(self):
        self.logger.info(f"CBR is now starting with version {CHATBRIDGEREFORGED_VERSION}")
        self.logger.debug("Checking config ......")
        if not path.exists(CONFIG_PATH):
            self.logger.error("Config is missing, defalut config generated")
            self._gen_config()
        self.config.getdata()
        self._check_config_info(self.config.data)
        
    def _gen_config(self):
        if not path.exists(DEFAULT_CONFIG_PATH):
            raise FileNotFoundError('Default config not found, re-installing ChatBridgeReforged may fix the problem')
            #self.logger.bug()
        else:
            shutil.copyfile(DEFAULT_CONFIG_PATH, CONFIG_PATH)
            self.logger.info("Defalut config is used now")
            self.logger.debug("Exit now")
            exit(0)#exit here

    def _check_config_info(self, data):
        self.logger.debug('Checking config.yml')
        if not self._check_node(data, CONFIG_STRUCTURE):
            try:
                raise ValueError('Some config is missing in config.yml')
            except:
                self.logger.bug(False)
            self.logger.warning('Please check config.yml carefully')
        else:
            self.logger.info('Checked config')
        data.keys()

    def _check_node(self, data, structure):
        check_node_result = True
        for i in range(len(structure)):
            self.logger.debug('Checking for ' + structure[i]['name'])
            struct = structure[i]
            if not struct['name'] in data.keys() or 'sub_structure' in struct.keys() and not self._check_node(data[struct['name']], struct['sub_structure']):
                check_node_result = False
                self.logger.error('Config ' + struct['name'] + ' not exist in config.yml')
            if not 'sub_structure' in struct.keys():
                if struct['name'] == 'client_servers':
                    msg = 'Client_servers are: '
                    for j in range(len(data[struct['name']])):
                        msg = msg + f" {data[struct['name']][j]['name']} "
                    self.logger.debug(msg)
                else:
                    self.logger.debug(f"Config {struct['name']} values {data[struct['name']]}")
        return check_node_result