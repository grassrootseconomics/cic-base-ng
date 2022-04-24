# standard imports
import logging

# external imports
import cic_eth.cli
from chainlib.chain import ChainSpec
from chainlib.eth.address import is_checksum_address
from cic_eth.registry import (
        connect as connect_registry,
        connect_declarator,
        connect_token_registry,
        )
from cic_eth_registry import CICRegistry
from cic_eth_registry.error import UnknownContractError

# legacy imports
from cic_base.legacy.db import SessionBase

logg = logging.getLogger(__name__)


class CICSettings:

    def __init__(self):
        self.o = {}
        self.get = self.o.get
        self.registry = None


    def process_common(self, config):
        self.o['CHAIN_SPEC'] = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
        
        rpc = cic_eth.cli.RPC.from_config(config)
        self.o['RPC'] = rpc.get_default()


    def process_celery(self, config):
        cic_eth.cli.CeleryApp.from_config(config)
        self.o['CELERY_QUEUE'] = config.get('CELERY_QUEUE')


    def process_database(self, config):
        scheme = config.get('DATABASE_ENGINE')
        if config.get('DATABASE_DRIVER') != None:
            scheme += '+{}'.format(config.get('DATABASE_DRIVER'))

        dsn = ''
        dsn_out = ''
        if config.get('DATABASE_ENGINE') == 'sqlite':
            dsn = '{}:///{}'.format(
                    scheme,
                    config.get('DATABASE_NAME'),    
                )
            dsn_out = dsn

        else:
            dsn = '{}://{}:{}@{}:{}/{}'.format(
                    scheme,
                    config.get('DATABASE_USER'),
                    config.get('DATABASE_PASSWORD'),
                    config.get('DATABASE_HOST'),
                    config.get('DATABASE_PORT'),
                    config.get('DATABASE_NAME'),    
                )
            dsn_out = '{}://{}:{}@{}:{}/{}'.format(
                    scheme,
                    config.get('DATABASE_USER'),
                    '***',
                    config.get('DATABASE_HOST'),
                    config.get('DATABASE_PORT'),
                    config.get('DATABASE_NAME'),    
                )

        logg.debug('parsed dsn from config: {}'.format(dsn_out))
        pool_size = int(config.get('DATABASE_POOL_SIZE'))
        SessionBase.connect(dsn, pool_size=pool_size, debug=config.true('DATABASE_DEBUG'))


    def process_trusted_addresses(self, config):
        trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
        if trusted_addresses_src == None:
            raise InitializationError('At least one trusted address must be declared in CIC_TRUST_ADDRESS')

        trusted_addresses = trusted_addresses_src.split(',')
        for i, address in enumerate(trusted_addresses):
            if not config.get('_UNSAFE'):
                if not is_checksum_address(address):
                    raise ValueError('address {} at position {} is not a valid checksum address'.format(address, i))
            else:
                trusted_addresses[i] = to_checksum_address(address)
            logg.info('using trusted address {}'.format(address))


        self.o['TRUSTED_ADDRESSES'] = trusted_addresses


    def process_registry(self, config):
        registry = None
        try:
            registry = connect_registry(self.o['RPC'], self.o['CHAIN_SPEC'], config.get('CIC_REGISTRY_ADDRESS'))
        except UnknownContractError as e:
            pass
        if registry == None:
            raise InitializationError('Registry contract connection failed for {}: {}'.format(config.get('CIC_REGISTRY_ADDRESS'), e))
        connect_declarator(self.o['RPC'], self.o['CHAIN_SPEC'], self.o['TRUSTED_ADDRESSES'])
        connect_token_registry(self.o['RPC'], self.o['CHAIN_SPEC'])

        self.o['CIC_REGISTRY'] = CICRegistry(self.o['CHAIN_SPEC'], self.o['RPC'])


    def process(self, config):
        self.process_common(config)
        self.process_database(config)
        self.process_trusted_addresses(config)
        self.process_registry(config)
        self.process_celery(config)
