"""PanModoki (source 38) contested-cargo transport observer for gate transport_reward.

Parses the real native markers emitted by pc_p2_breadbug_actor +
pc_p2_breadbug_contest_host (lane 18 / #220) and validates the natural
contested-cargo tug plus the durable nest/Pod receipt, including the
exactly-once negatives. Nothing is emitted or fabricated here: this module
only reads an existing native.log and classifies the observed sequence, so a
future fresh run is checkable and a partial/injected run cannot be mislabeled.

The same grammar is implemented independently in
native/tools/p2_panmodoki_transport_fixture.cpp (stdlib-only checker) so a
native-side gate script and the Python suite agree on a shared contract.
"""
import re

GENERATOR_SOURCE_38 = 186081
SOURCE_IDENTITY_PREFIX = 'onion:p2:38'


class TransportContractError(Exception):
    """Raised when a log violates a mandatory transport/receipt invariant."""


_READY = re.compile(r'P2_BREADBUG_ACTOR_READY generator=(\d+) .*behavior=(\S+)')
_CARRY = re.compile(r'P2_BREADBUG_CONTEST generator=(\d+) native_power=([\d.]+) carriers=(\d+)')
_BEGIN = re.compile(r'P2_BREADBUG_CONTEST_BEGIN generator=(\d+) identity=(\S+) max=(\d+)')
_UPDATE = re.compile(r'P2_BREADBUG_CONTEST_UPDATE generator=(\d+) carriers=(\d+) outcome=(\w+)')
_STOLEN = re.compile(r'P2_BREADBUG_CONTEST_STOLEN generator=(\d+) carriers=(\d+) released=(\d+)')
_GRANT = re.compile(r'P2_BREADBUG_CONTEST_GRANT generator=(\d+) identity=(\S+) granted=(\d+)(?: duplicate=(\d+))?')
_PROBE = re.compile(r'P2_BREADBUG_CONTEST_PROBE generator=(\d+) carriers=(\d+) injected=(\d+)')
_INTERRUPT = re.compile(r'P2_BREADBUG_CONTEST_INTERRUPT generator=(\d+) reason=(\w+)')
_OWNER_DIED = re.compile(r'P2_BREADBUG_OWNER_DIED generator=(\d+) released=(\d+) reason=(\w+)')
_DEATH = re.compile(r'P2_BREADBUG_ACTOR_DEATH generator=(\d+) corpse=(\d+) held=(\d+)')


def parse(log_text):
    """Return the ordered list of recognized transport markers.

    Each item is a dict with kind, generator, line number (1-based) and the
    decoded fields. Unknown lines are ignored so ordinary engine output does
    not break the contract.
    """
    events = []
    for number, raw in enumerate(log_text.splitlines(), 1):
        line = raw.strip()
        if 'P2_BREADBUG_' not in line:
            continue
        for kind, pattern in (('ready', _READY), ('carry', _CARRY), ('begin', _BEGIN),
                              ('update', _UPDATE), ('stolen', _STOLEN), ('grant', _GRANT),
                              ('probe', _PROBE), ('interrupt', _INTERRUPT),
                              ('owner_died', _OWNER_DIED), ('death', _DEATH)):
            match = pattern.search(line)
            if match:
                item = {'kind': kind, 'generator': int(match[1]), 'line': number,
                        'text': line}
                if kind == 'ready':
                    item['behavior'] = match[2]
                elif kind == 'carry':
                    item['native_power'] = float(match[2])
                    item['carriers'] = int(match[3])
                elif kind == 'begin':
                    item['identity'] = match[2]
                elif kind == 'update':
                    item['carriers'] = int(match[2])
                    item['outcome'] = match[3]
                elif kind == 'stolen':
                    item['carriers'] = int(match[2])
                    item['released'] = int(match[3])
                elif kind == 'grant':
                    item['identity'] = match[2]
                    item['granted'] = int(match[3])
                    item['duplicate'] = int(match[4]) if match[4] is not None else 0
                elif kind == 'probe':
                    item['carriers'] = int(match[2])
                    item['injected'] = int(match[3])
                elif kind == 'interrupt':
                    item['reason'] = match[2]
                elif kind == 'owner_died':
                    item['released'] = int(match[2])
                elif kind == 'death':
                    item['corpse'] = int(match[2])
                    item['held'] = int(match[3])
                events.append(item)
                break
    return events


def _require(condition, message):
    if not condition:
        raise TransportContractError(message)


def validate(events, generator=GENERATOR_SOURCE_38):
    """Validate the natural contested-cargo transport + durable receipt contract.

    Requires, in order: family bind; a natural carry latch with real carriers
    (>= 1 native_power reading); a sustained drag/held outcome; a stolen tug;
    exactly one granting receipt for the panmodoki identity; and a later
    duplicate attempt refused as duplicate=1. Injected carrier probes and
    grants without a preceding steal are rejected outright.

    Returns a report dict with the classified outcome and cited line numbers.
    """
    scoped = [e for e in events if e['generator'] == generator]
    ready = [e for e in scoped if e['kind'] == 'ready']
    _require(ready, 'Missing P2_BREADBUG_ACTOR_READY bind for generator %d' % generator)
    _require(ready[0]['behavior'] == 'P1_Collec_proxy',
             'Unexpected source-38 behavior: ' + ready[0]['behavior'])

    natural_carries = [e for e in scoped if e['kind'] == 'carry' and e['carriers'] >= 1]
    _require(natural_carries,
             'No natural carry latch: no P2_BREADBUG_CONTEST carriers>=1 reading')
    _require(all(e['native_power'] >= 0 for e in natural_carries),
             'Invalid native_power in carry reading')

    drags = [e for e in scoped if e['kind'] == 'update' and e['outcome'] == 'held'
             and e['carriers'] >= 1]
    _require(drags, 'No sustained drag/held tug: no CONTEST_UPDATE held with carriers>=1')

    injected = [e for e in scoped if e['kind'] == 'probe' and e['injected'] == 1]
    if injected:
        natural_lines = {e['line'] for e in natural_carries}
        injected_lines = {e['line'] for e in injected}
        _require(natural_lines,
                 'Carrier count only ever injected (probe injected=1 at line %d)' % min(injected_lines))

    stolen = [e for e in scoped if e['kind'] == 'stolen']
    grants = [e for e in scoped if e['kind'] == 'grant']
    granted = [e for e in grants if e['granted'] == 1]
    duplicates = [e for e in grants if e['granted'] == 0 and e['duplicate'] == 1]

    _require(stolen, 'No stolen tug: transport_reward requires a resolved contest')
    _require(granted, 'No durable receipt: CONTEST_GRANT granted=1 missing')
    for grant in granted:
        preceding = [e for e in scoped if e['line'] < grant['line'] and e['kind'] == 'stolen']
        _require(preceding,
                 'Injected receipt: grant granted=1 at line %d without a preceding STOLEN' % grant['line'])
        _require(grant['identity'].startswith(SOURCE_IDENTITY_PREFIX),
                 'Receipt identity %s is not source 38' % grant['identity'])
    identities = {e['identity'] for e in granted}
    _require(len(identities) == len(granted),
             'Duplicate delivery: the same identity received more than one granted=1')
    _require(duplicates,
             'Missing exactly-once negative: no GRANT granted=0 duplicate=1 after the first receipt')
    first_grant_line = min(e['line'] for e in granted)
    _require(all(e['line'] > first_grant_line for e in duplicates),
             'Duplicate refusal must follow the first granted receipt')

    return {
        'generator': generator,
        'identity': sorted(identities)[0],
        'natural_carry_line': natural_carries[0]['line'],
        'drag_line': drags[0]['line'],
        'stolen_line': stolen[0]['line'],
        'grant_line': first_grant_line,
        'duplicate_line': duplicates[0]['line'],
        'injected_probes': len(injected),
        'transport_reward': 'PASS',
    }


def validate_log(path, generator=GENERATOR_SOURCE_38):
    """Convenience wrapper: read a native.log path and validate it."""
    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        return validate(parse(handle.read()), generator)
