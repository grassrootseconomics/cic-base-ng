# standard imports
import logging

# external imports
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
import cic_base.cli
from cic_base.legacy.db import SessionBase
from cic_base.error import InitializationError

logg = logging.getLogger(__name__)


def __init__(settings):
    settings.o = {}
    settings.get = settings.o.get
    settings.registry = None


def process_common(settings, config):
    chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
    settings.o['CHAIN_SPEC'] = chain_spec
    
    rpc = cic_base.cli.RPC.from_config(config)
    conn = rpc.get_default()
    settings.set('RPC', conn)

    return settings


def process_celery(settings, config):
    cic_base.cli.CeleryApp.from_config(config)
    settings.set('CELERY_QUEUE', config.get('CELERY_QUEUE'))

    return settings


def process_database(settings, config):
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

    return settings


def process_trusted_addresses(settings, config):
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


    settings.set('TRUSTED_ADDRESSES', trusted_addresses)

    return settings


def process_registry(settings, config):
    registry = None
    chain_spec = settings.get('CHAIN_SPEC')
    rpc = settings.get('RPC')
    registry_address = config.get('CIC_REGISTRY_ADDRESS')

    try:
        registry = connect_registry(rpc, chain_spec, registry_address)
    except UnknownContractError as e:
        pass
    if registry == None:
        raise InitializationError('Registry contract connection failed for {}: {}'.format(config.get('CIC_REGISTRY_ADDRESS'), e))
    connect_declarator(rpc, chain_spec, settings.get('TRUSTED_ADDRESSES'))
    connect_token_registry(rpc, chain_spec)

    registry = CICRegistry(chain_spec, rpc)
    settings.set('CIC_REGISTRY', registry)

    return settings
