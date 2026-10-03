"""Versioned producer contract for the generated engineering cave.

This contract is separate from historical standalone descriptors. It does not
claim retail course geometry or enable an AP option without the native consumer.
"""
from .cave_floor import create, fingerprint
from experimental.pikmin2_cave_lane41_generator import _seed_uint64

SCHEMA = 'pikmin-generated-cave-seed/1'
CAPABILITY = 'generated-cave-checks-v1'
DISPLAY_NAME = 'Generated Forest Cave'
LOCATION_NAMES = (
    'Pikmin 2: Generated Forest Cave F1 Water Treasure',
    'Pikmin 2: Generated Forest Cave F1 Electric Treasure',
)


def location_ids(base):
    from .catalog import LOCATION_BASE
    additions = {name: LOCATION_BASE + 0x10000 + i
                 for i, name in enumerate(LOCATION_NAMES)}
    if set(additions) & set(base) or set(additions.values()) & set(base.values()):
        raise ValueError('generated cave location identity collision')
    return dict(base, **additions)


def can_reach(inventory, manifest):
    from .catalog import RED, BLUE, YELLOW, color_inventory
    owned = color_inventory(inventory, manifest)
    # Onion access supplies renewable actual bodies; runtime entry separately
    # witnesses the two living Red inputs. Capacity never substitutes for stock.
    return all(owned.get(onion, 0) for onion in (RED, BLUE, YELLOW))


def produce(seed, slot):
    descriptor = create(seed, slot)
    table = descriptor['table']
    return {
        'schema': SCHEMA,
        'identity': {'kind': 'engineered', 'id': 'generated-forest-v1',
                     'engine_cave': table['cave_id'], 'retail_source': None,
                     'display_name': DISPLAY_NAME},
        'descriptor': descriptor,
        'native_seed': _seed_uint64(table['seed']),
        'native_token': fingerprint(descriptor)[:32],
        'checks': [
            {'name': name, 'item': treasure['treasure_id'],
             'host': treasure['slot_id'],
             'slot': 'item:' + treasure['slot_id'] + ':0'}
            for name, treasure in zip(LOCATION_NAMES, table['treasures'])
        ],
        # Supply is actual input bodies, not field-capacity upgrades. Production
        # entry must witness these Red bodies before accepting the bud recipe.
        'entry_supply': {'species': 'red', 'minimum_live_bodies': 2,
                         'source': 'ordinary-campaign-red-onion-and-pellets'},
        'bud_recipe': {'blue_inputs': 2, 'yellow_inputs': 1,
                       'yellow_input_species': 'blue'},
    }


def validate_contract(contract, seed, slot):
    if type(contract) is not dict or contract != produce(seed, slot):
        raise ValueError('foreign or incompatible generated cave seed contract')
    return contract


def bootstrap_contract(contract, seed, slot, names):
    validate_contract(contract, seed, slot)
    names = tuple(names)
    if len(names) != len(set(names)):
        raise ValueError('ambiguous native check catalog')
    if names[-2:] != LOCATION_NAMES:
        raise ValueError('generated cave checks must follow the complete base catalog')
    words = ['CAVE_CHECKS', '1', contract['identity']['id'],
             contract['identity']['engine_cave'], '1',
             str(contract['native_seed']), contract['native_token'], '2']
    for check in contract['checks']:
        words.extend((str(names.index(check['name'])), check['item'],
                      check['host'], check['slot']))
    return ' '.join(words) + '\n'
