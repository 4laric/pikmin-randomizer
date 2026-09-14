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
import re
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

# Pod-cargo staging: a cargo-enabled Mamuta arena needs a single ``pr05``
# treasure actor (native policy refuses a non-cargo-free preview without one)
# plus the converted ``treasure.mod``/``pod.mod`` pair the native preview loads.
# Generator 221004 is reserved for this lane alongside 221001..221003.
POD_TREASURE_GENERATOR = 221004
POD_TREASURE_NAME = 'P2 Mamuta pod cargo'
POD_TREASURE_POSITION = (-150., 30., 1750.)  # 100 units north of the Mamuta
POD_PACKAGE_FILES = ('p2-pod.txt', 'pod.mod', 'treasure.mod')

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


def parse_cargo_profile(text):
    """Parse/canonicalise a staged ``p2-pod.txt`` profile, rejecting anything odd."""
    parts = text.split()
    if len(parts) != 7 or parts[0] != 'P2_POD_1' or parts[5] != 'Kochappy':
        raise ValueError('Invalid pod profile')
    try:
        money, weight, capacity, corpse_value = (int(parts[2]), int(parts[3]),
                                                 int(parts[4]), int(parts[6]))
    except ValueError as error:
        raise ValueError('Invalid pod economy') from error
    canonical = cargo_profile(parts[1], money, weight, capacity, corpse_value)
    return dict(treasure=parts[1], money=money, weight=weight, capacity=capacity,
                corpse_value=corpse_value, profile=canonical)


def load_pod_package(package):
    """Load a reusable converted Pod package (pod.mod/treasure.mod/p2-pod.txt).

    The package is the disc-derived asset trio produced once by
    ``experimental.pikmin2_pod.extract`` (or ``pikmin2_beasts_content``) and
    cached under ``output/``; it is deliberately not committed. Fails closed on
    any missing/empty member so the native preview never aborts mid-run.
    """
    path = Path(package)
    missing = [name for name in POD_PACKAGE_FILES if not (path / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f'Pod asset package incomplete at {path}: missing {", ".join(missing)}')
    profile = parse_cargo_profile((path / 'p2-pod.txt').read_text())
    treasure_model = (path / 'treasure.mod').read_bytes()
    pod_model = (path / 'pod.mod').read_bytes()
    if not treasure_model or not pod_model:
        raise ValueError('Pod asset package contains empty models')
    return dict(path=str(path), treasure_model=treasure_model, pod_model=pod_model,
                treasure_model_sha256=hashlib.sha256(treasure_model).hexdigest(),
                pod_model_sha256=hashlib.sha256(pod_model).hexdigest(), **profile)


def find_pod_package(candidates):
    """Return the first loadable Pod package among ``candidates`` or fail closed."""
    tried = []
    for candidate in candidates:
        path = Path(candidate)
        if all((path / name).is_file() for name in POD_PACKAGE_FILES):
            return load_pod_package(path)
        tried.append(str(path))
    raise FileNotFoundError('No reusable Pod asset package found among: ' + ', '.join(tried))


def _treasure_record_from_source(source, position):
    record = bytearray(source)
    struct.pack_into('<I', record, 8, POD_TREASURE_GENERATOR)
    record[16:48] = POD_TREASURE_NAME.encode('ascii').ljust(32, b'\0')
    write_position(record, position)
    return bytes(record)


def treasure_record(assets, position=POD_TREASURE_POSITION):
    """Build the single ``pr05`` treasure generator record for the Pod arena."""
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    source = next((r for r in candidates
                   if r[16:48].rstrip(b'\0') == b'preview treasure bolt'), None)
    if source is None or source[80:84] != b'50rp':
        raise ValueError('Source pr05 treasure template unavailable')
    return _treasure_record_from_source(source, position)


def validate_treasure_record(record, position=POD_TREASURE_POSITION):
    """Re-parse a staged Pod treasure record and prove the intended fields survived."""
    if len(record) < 96 or record[80:84] != b'50rp':
        raise ValueError('Pod treasure record is not pr05')
    if struct.unpack_from('<I', record, 8)[0] != POD_TREASURE_GENERATOR:
        raise ValueError('Pod treasure generator ID mismatch')
    if record[16:48].rstrip(b'\0').decode('ascii') != POD_TREASURE_NAME:
        raise ValueError('Pod treasure name mismatch')
    return dict(generator=POD_TREASURE_GENERATOR, species=POD_TREASURE_NAME,
                native_family='Pellet', model_id='pr05',
                position=list(validate_position(bytearray(record), position)))


def append_treasure_record(run, record):
    """Append a built treasure record to a staged arena gen; refuse a second pr05."""
    gen = run / 'assets/dataDir/stages/chal0/default.gen'
    data = gen.read_bytes()
    if data[:4] != b'1.0v' or len(data) < 24:
        raise ValueError('Unsupported stage generator')
    starts = [m.start() for m in re.finditer(b'    0.0v', data)]
    count = struct.unpack_from('>I', data, 20)[0]
    if not starts or starts[0] != 24 or len(starts) != count:
        raise ValueError('Stage generator record framing mismatch')
    entries = [data[s:(starts[i + 1] if i + 1 < len(starts) else len(data))]
               for i, s in enumerate(starts)]
    if any(struct.unpack_from('<I', e, 8)[0] == POD_TREASURE_GENERATOR for e in entries):
        raise ValueError('Pod treasure generator already staged')
    if any(e[80:84] == b'50rp' for e in entries):
        raise ValueError('A pr05 treasure actor is already staged')
    gen.write_bytes(data[:20] + struct.pack('>I', count + 1) + b''.join(entries) + record)
    return validate_treasure_record(record)


def enable_cargo(run, *, treasure, money, weight, capacity, corpse_value,
                 treasure_model_sha256, pod_model_sha256):
    """Switch a cargo-free staged arena to a Pod without changing its actors.

    ``arena.prepare`` stages ``p2-cargo-free.txt``; the native preview refuses
    cargo while that file exists, which is why the Mamuta carcass could never be
    delivered (see docs/PIKMIN2_MAMUTA_POD.md). This removes it and writes the
    Pod config, but requires the caller to have already staged
    ``assets/dataDir/courses/pikmin2room/treasure.mod`` and ``pod.mod`` (both
    hashed here) and a ``pr05`` treasure actor; otherwise the native preview
    aborts with 'treasure generator missing', 'converted treasure missing' or
    'P2 pod shape missing'. :func:`stage_cargo` performs that staging.
    """
    cargo_free = run / 'p2-cargo-free.txt'
    if not cargo_free.exists():
        raise ValueError('Arena is not cargo-free; refusing to change cargo mode')
    config = run / 'p2-pod.txt'
    if config.exists():
        raise ValueError('Refusing existing pod config')
    model = run / 'assets/dataDir/courses/pikmin2room/treasure.mod'
    if not model.exists() or _sha(model) != treasure_model_sha256:
        raise ValueError('Staged treasure model missing or mismatched')
    pod_model = run / 'assets/dataDir/courses/pikmin2room/pod.mod'
    if not pod_model.exists() or _sha(pod_model) != pod_model_sha256:
        raise ValueError('Staged pod model missing or mismatched')
    config.write_text(cargo_profile(treasure, money, weight, capacity, corpse_value))
    cargo_free.unlink()
    return dict(file=config.name, treasure=treasure, money=money, weight=weight,
                capacity=capacity, corpse_value=corpse_value,
                treasure_model_sha256=treasure_model_sha256,
                pod_model_sha256=pod_model_sha256)


def stage_cargo(run, assets, package, position=POD_TREASURE_POSITION, record=None):
    """Stage the Pod cargo end-to-end on a cargo-free arena, then enable it.

    Writes the converted ``treasure.mod``/``pod.mod`` pair, appends the ``pr05``
    treasure actor to the stage generator, and calls :func:`enable_cargo`. The
    package may be a :func:`load_pod_package` dict or a path to a package dir.
    Callers may pass a prebuilt ``record`` so an unavailable template fails
    before the arena is mutated.
    """
    resolved = package if isinstance(package, dict) else load_pod_package(package)
    room = run / 'assets/dataDir/courses/pikmin2room'
    room.mkdir(parents=True, exist_ok=True)
    (room / 'treasure.mod').write_bytes(resolved['treasure_model'])
    (room / 'pod.mod').write_bytes(resolved['pod_model'])
    actor = append_treasure_record(run, record if record is not None else treasure_record(assets, position))
    info = enable_cargo(run, treasure=resolved['treasure'], money=resolved['money'],
                        weight=resolved['weight'], capacity=resolved['capacity'],
                        corpse_value=resolved['corpse_value'],
                        treasure_model_sha256=resolved['treasure_model_sha256'],
                        pod_model_sha256=resolved['pod_model_sha256'])
    info['actor'] = actor
    info['package'] = resolved['path']
    return info


def prepare(assets, imported, output, cargo=None):
    """Batch-2 arena plus rules marker plus the explicit 10-red starting squad.

    The squad record is staged through ``arena.prepare``'s overlay override so
    the mandatory ``ensure_pikmin_squad()`` helper sees the existing 'ikip'
    record and preserves this lane's squad instead of adding the default
    20-red squad.

    Passing ``cargo`` as ``dict(pod_package=<dir>, position=<xyz>)`` switches the
    run from the default cargo-free arena to a Pod: :func:`stage_cargo` writes
    the converted models, appends the ``pr05`` treasure actor and enables the
    Pod config so the Mamuta carcass can be credited. Omitting/pointing at an
    unavailable package fails closed before any file is written.
    """
    assets = Path(assets).resolve()
    cargo_package = cargo_record = None
    if cargo is not None:
        cargo = dict(cargo)
        package = cargo.pop('pod_package', None)
        position = cargo.pop('position', POD_TREASURE_POSITION)
        if package is None:
            raise ValueError('Cargo staging requires pod_package')
        if cargo:
            raise ValueError('Unknown cargo options: ' + ', '.join(sorted(cargo)))
        # Resolve/hash the package and the source template before any mutation so
        # an unavailable asset fails closed without writing a partial arena.
        cargo_package = load_pod_package(package)
        cargo_record = treasure_record(assets, position)
    record = squad_record(assets)
    placement = validate_squad(record)
    run = arena.prepare(assets, imported, output, extra_record=record, extra_actor=placement)
    info = json.loads((run / 'arena.json').read_text())
    info['squad'] = placement
    info['rules'] = stage_rules(run)
    if cargo_package is not None:
        info['cargo'] = stage_cargo(run, assets, cargo_package, record=cargo_record)
        info['gates']['pod_cargo'] = ('staged (pr05 treasure actor + converted '
                                      'treasure.mod/pod.mod; Pod receipt path)')
    info['gates']['starting_squad'] = 'staged (explicit 10-red lane squad; overlay preserved)'
    (run / 'arena.json').write_text(json.dumps(info, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    print(prepare(a.assets, a.imported, a.output))
