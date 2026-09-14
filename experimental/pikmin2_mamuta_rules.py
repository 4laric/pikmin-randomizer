"""Batch 4 (#221): opt-in P2 Miulin bury rules + starting Pikmin squad staging.

Layers the native opt-in P2 receiver semantics (pc_p2_mamuta_rules, marker
p2-mamuta-rules.txt = P2_MAMUTA_RULES_1 at the run root) onto the batch-2
arena, and adds a small starting red Pikmin squad near the Mamuta so the
arena attack naturally exercises bury -> flower-stage planted sprout, the
P2 99-planted cap, and captain damage-only behavior.

Squad generator ID 221003 is reserved for this lane (recorded on #186).
Native reference semantics (interactPiki.cpp:377-442, interactNavi.cpp:218-226,
miulinState.cpp:264-330): flower-stage same-kind planted sprout, 99-planted
cap (US), non-bald safe ground, +-20 vertical band, captain 5.0 damage only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from scripts.preview_pikmin2_room import generator
from experimental.pikmin2_generator_pose import write_position, validate_position
from experimental import pikmin2_mamuta_arena as arena

RULES_NAME = 'p2-mamuta-rules.txt'
RULES_TOKEN = 'P2_MAMUTA_RULES_1'
SQUAD_GENERATOR = 221003  # reserved on #186 for the Mamuta lane squad
SQUAD_NAME = 'P2 Mamuta squad reds'
SQUAD_COUNT = 10
SQUAD_COLOR = 1  # native Red
SQUAD_FORMATION = 2  # free formation, not a buried sprout
SQUAD_POSITION = (-150., 30., 1900.)  # 50 units south of the Mamuta at (-150, 30, 1850)

P2_REFERENCE = dict(piki_damage=0.0, navi_damage=5.0, planted_cap_us=99,
                    vertical_band=20.0, kill_flag='CKILL_DontCountAsDeath')


def rules_profile():
    return RULES_TOKEN + '\n'


def stage_rules(run):
    """Write the opt-in rules marker at the run root (native reads it from CWD)."""
    target = run / RULES_NAME
    if target.exists():
        raise ValueError('Refusing existing rules profile')
    target.write_text(rules_profile())
    return {'file': RULES_NAME, 'token': RULES_TOKEN, 'reference': dict(P2_REFERENCE)}


def validate_rules_profile(run):
    target = run / RULES_NAME
    if target.read_text() != rules_profile():
        raise ValueError('Rules profile mismatch')
    return True


def squad_record(assets):
    """Build the starting-squad generator record from the validated piki template."""
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    piki = bytearray(next(r for r in candidates if r[72:76] == b'ikip'))
    if piki[80:84] != b'p00\x04' or piki[88:92] != b'p01\x04':
        raise ValueError('Unexpected Piki fields')
    struct.pack_into('<I', piki, 8, SQUAD_GENERATOR)  # arena roster endianness (native-verified)
    piki[16:48] = SQUAD_NAME.encode('ascii').ljust(32, b'\0')
    struct.pack_into('>I', piki, 84, SQUAD_FORMATION)
    struct.pack_into('>I', piki, 92, SQUAD_COLOR)
    type_start = piki.index(b'nota0.0v', 96)
    count_start = piki.index(b'p00\x04', type_start) + 4
    struct.pack_into('>I', piki, count_start, SQUAD_COUNT)
    write_position(piki, SQUAD_POSITION)
    return bytes(piki)


def validate_squad(record):
    """Re-parse a staged squad record and prove the intended fields survived."""
    if struct.unpack_from('<I', record, 8)[0] != SQUAD_GENERATOR:
        raise ValueError('Squad generator ID mismatch')
    if record[16:48].rstrip(b'\0').decode('ascii') != SQUAD_NAME:
        raise ValueError('Squad name mismatch')
    if struct.unpack_from('>I', record, 84)[0] != SQUAD_FORMATION:
        raise ValueError('Squad formation mismatch')
    if struct.unpack_from('>I', record, 92)[0] != SQUAD_COLOR:
        raise ValueError('Squad color mismatch')
    type_start = record.index(b'nota0.0v', 96)
    count_start = record.index(b'p00\x04', type_start) + 4
    if struct.unpack_from('>I', record, count_start)[0] != SQUAD_COUNT:
        raise ValueError('Squad count mismatch')
    return dict(generator=SQUAD_GENERATOR, species=SQUAD_NAME, native_family='Piki',
                count=SQUAD_COUNT, color='red', formation=SQUAD_FORMATION,
                position=list(validate_position(bytearray(record), SQUAD_POSITION)))


def parse_plant_events(log_text):
    """Parse native rules markers from a session log for fixture verification.

    Native emitters (pc_p2_mamuta_rules.cpp): P2_MAMUTA_RULES enabled ...,
    P2_MAMUTA_PLANT kind=<int> happa=<int> planted=<int>,
    P2_MAMUTA_PLANT_REJECT reason=<word>, P2_MAMUTA_NAVI damage=<f> health=<f>.
    """
    events = {'enabled': 0, 'plants': [], 'rejects': [], 'navi': []}
    for line in log_text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'P2_MAMUTA_RULES' and len(parts) > 1 and parts[1] == 'enabled':
            events['enabled'] += 1
        elif parts[0] == 'P2_MAMUTA_PLANT':
            kv = dict(p.split('=', 1) for p in parts[1:])
            events['plants'].append({'kind': int(kv['kind']), 'happa': int(kv['happa']),
                                     'planted': int(kv['planted'])})
        elif parts[0] == 'P2_MAMUTA_PLANT_REJECT':
            kv = dict(p.split('=', 1) for p in parts[1:])
            events['rejects'].append(kv['reason'])
        elif parts[0] == 'P2_MAMUTA_NAVI':
            kv = dict(p.split('=', 1) for p in parts[1:])
            events['navi'].append({'damage': float(kv['damage']),
                                   'health': float(kv['health'])})
    return events


def validate_plant_events(events, min_plants=1):
    """P2 acceptance over parsed events: flower-stage (happa 2) same-kind plants."""
    if events['enabled'] != 1:
        raise ValueError('Rules profile must be enabled exactly once')
    if len(events['plants']) < min_plants:
        raise ValueError('Expected at least one planted sprout')
    for plant in events['plants']:
        if plant['happa'] != 2:
            raise ValueError('P2 planted sprout must be flower-stage')
    for hit in events['navi']:
        if hit['damage'] != P2_REFERENCE['navi_damage']:
            raise ValueError('Captain bury damage must be the P2 value 5.0')
    for reason in events['rejects']:
        if reason != 'cap99':
            raise ValueError('Unknown plant rejection reason: ' + reason)
    return True


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cargo_profile(treasure, money, weight, capacity, corpse_value):
    """Exact ``p2-pod.txt`` text the native preview parses (P2_POD_1 header).

    The native reader expects the version token, a treasure row
    ``<id> <money> <weight> <capacity>``, and a ``Kochappy <value>`` corpse row;
    the same ranges are enforced there.
    """
    if not (isinstance(treasure, str) and treasure and treasure.isascii()
            and not any(c.isspace() for c in treasure) and len(treasure) < 64):
        raise ValueError('Invalid pod treasure id')
    if not (0 <= money <= 1000000 and 1 <= weight <= 1000 and 1 <= capacity <= 128
            and 0 <= corpse_value <= 1000000):
        raise ValueError('Invalid pod economy')
    return f'P2_POD_1\n{treasure} {money} {weight} {capacity}\nKochappy {corpse_value}\n'


def enable_cargo(run, *, treasure, money, weight, capacity, corpse_value,
                 treasure_model_sha256):
    """Switch a cargo-free staged arena to a Pod without changing its actors.

    ``arena.prepare`` stages ``p2-cargo-free.txt``; the native preview refuses
    cargo while that file exists, which is why the Mamuta carcass could never be
    delivered (see docs/PIKMIN2_MAMUTA_POD.md). This removes it and writes the
    Pod config, but requires the caller to have already staged
    ``assets/dataDir/courses/pikmin2room/treasure.mod`` (hashed here) and a
    ``pr05`` treasure actor in the stage; otherwise the native preview aborts
    with 'treasure generator missing' or 'converted treasure missing'.
    """
    cargo_free = run / 'p2-cargo-free.txt'
    if not cargo_free.exists():
        raise ValueError('Arena is not cargo-free; refusing to change cargo mode')
    pod = run / 'p2-pod.txt'
    if pod.exists():
        raise ValueError('Refusing existing pod config')
    model = run / 'assets/dataDir/courses/pikmin2room/treasure.mod'
    if not model.exists() or _sha(model) != treasure_model_sha256:
        raise ValueError('Staged treasure model missing or mismatched')
    pod.write_text(cargo_profile(treasure, money, weight, capacity, corpse_value))
    cargo_free.unlink()
    return dict(file=pod.name, treasure=treasure, money=money, weight=weight,
                capacity=capacity, corpse_value=corpse_value,
                treasure_model_sha256=treasure_model_sha256)


def prepare(assets, imported, output, cargo=None):
    """Batch-2 arena plus rules marker plus the explicit 10-red starting squad.

    The squad record is staged through ``arena.prepare``'s overlay override so
    the mandatory ``ensure_pikmin_squad()`` helper sees the existing 'ikip'
    record and preserves this lane's squad instead of adding the default
    20-red squad.

    Passing ``cargo`` (keyword args for :func:`enable_cargo`) switches the run
    from the default cargo-free arena to a Pod so the Mamuta carcass can be
    credited.
    """
    assets = Path(assets).resolve()
    record = squad_record(assets)
    placement = validate_squad(record)
    run = arena.prepare(assets, imported, output, extra_record=record, extra_actor=placement)
    info = json.loads((run / 'arena.json').read_text())
    info['squad'] = placement
    info['rules'] = stage_rules(run)
    if cargo is not None:
        info['cargo'] = enable_cargo(run, **cargo)
    info['gates']['starting_squad'] = 'staged (explicit 10-red lane squad; overlay preserved)'
    (run / 'arena.json').write_text(json.dumps(info, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    print(prepare(a.assets, a.imported, a.output))
