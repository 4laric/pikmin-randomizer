"""Named retail enemy data; species-specific tails remain untranslated.

Layout: projectPiki/pikmin2 29bc5478edffa2c963c88fdd261d876d055aa2b0,
src/plugProjectYamashitaU/genEnemy.cpp, GenObjectEnemy::doRead.
This decoder does not instantiate enemies or reproduce their spawn RNG.
"""
from copy import deepcopy
import math


def _integer(value, minimum, maximum):
    if not isinstance(value, str):
        raise ValueError('Expected source integer token')
    try:
        result = int(value)
    except ValueError as error:
        raise ValueError('Invalid source integer') from error
    if not minimum <= result <= maximum:
        raise ValueError('Source integer outside native field range')
    return result


def _number(value):
    if not isinstance(value, str):
        raise ValueError('Expected source float token')
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError('Invalid source float') from error
    if not math.isfinite(result) or abs(result) > 3.4028234663852886e38:
        raise ValueError('Nonfinite or overflowing native source float')
    return result


def enemy_object(actor):
    """Decode common 0005 fields, retaining the complete special generator tail.

    Spawn type1 uses the original center; other types use radius/RNG in retail.
    Do not infer native support from a decoded enemy ID or opaque tail.
    """
    if actor.get('kind') != 'teki' or actor.get('object_version') != '0005':
        raise ValueError('Unsupported source enemy object version/kind')
    values = actor.get('source_payload')
    if (not isinstance(values, list) or len(values) < 15
            or values[-1] != [['_eof']] or not isinstance(values[13], list)
            or len(values[13]) != 1 or not isinstance(values[13][0], str)
            or len(values[13][0]) != 4):
        raise ValueError('Malformed source enemy generator tail/version')
    result = dict(source_id=_integer(values[0], 0, 65535),
                  birth_type=_integer(values[1], 0, 255),
                  count=_integer(values[2], 0, 32767),
                  direction_degrees=_number(values[3]),
                  spawn_type=_integer(values[4], 0, 255),
                  appear_radius=_number(values[5]), enemy_size=_number(values[6]),
                  treasure_code=_integer(values[7], -32768, 32767),
                  pellet_color=_integer(values[8], 0, 255),
                  pellet_size=_integer(values[9], 0, 255),
                  pellet_minimum=_integer(values[10], 0, 255),
                  pellet_maximum=_integer(values[11], 0, 255),
                  pellet_probability=_number(values[12]),
                  generator_version=values[13][0],
                  generator_tail=deepcopy(values[14:-1]))
    return result
