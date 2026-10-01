"""Private original Impact Site arena for the sampled Bulblax display (#172, #389).

Batch 5 install+arena entry for the Empress/Emperor Bulblax and larva family,
modeled on ``pikmin2_aquatic_arena.py`` and ``pikmin2_kochappy_arena.py`` per
``docs/PIKMIN2_ENEMY_ARENA.md``. Original P1 Impact Site map/collision/routes
are preserved byte-identical; the arena adds a small starting Pikmin squad
(5 red + 5 blue, per the #234 expectations artifact) and stages the #235
sampled Bulblax display through ``pikmin2_bulblax_visual.install``.

The Bulblax lane is a noninteractive sampled display (``p2-bulblax-visual.txt``,
``P2_BULBLAX_VISUAL_1``), not a live boss Teki: there is no source FSM, combat,
damage receiver, drops or rewards here. Display placements 230001/230002/230003
are the engineered coordinates recorded in ``docs/PIKMIN2_BULBLAX_RUNTIME.md``;
source yaw is carried as unapplied metadata. This is engineered placement, not
production placement evidence.
"""
import argparse
import hashlib
import json
import struct
import uuid
from pathlib import Path

from scripts.preview_pikmin2_room import generator, overlay, records
from experimental.pikmin2_generator_pose import write_position
from experimental.pikmin2_bulblax_visual import install as install_display

# #235 engineered display placements (docs/PIKMIN2_BULBLAX_RUNTIME.md).
EXPECTED = ((230001, 'Queen', 'wait1', (-120., 30., 1800.)),
            (230002, 'Baby', 'move', (-100., 30., 1820.)),
            (230003, 'KingChappy', 'move1', (150., 30., 1500.)))
SQUAD = (('red', 5), ('blue', 5))
SQUAD_BASE = 230100
GATES = ('native_identity', 'spawn_exact_xyz', 'control_undisturbed', 'natural_AI',
         'combat', 'death_corpse', 'carrier_recovery', 'reload')
BLOCKED = {
    'native_identity': 'display-only sampled overlay; no Teki actor registered (#235)',
    'natural_AI': 'blocked: source boss FSM/AI is not in the sampled display',
    'combat': 'blocked: source attacks/damage receivers are not registered',
    'death_corpse': 'blocked: source death/corpse behavior is not registered',
    'carrier_recovery': 'blocked: no carry behavior in the sampled display path',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the 5 red + 5 blue starting squad to the original practice records."""
    source = assets / 'dataDir/stages/practice/default.gen'
    header = source.read_bytes()[:24]
    practice = records(source)
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    template = next(r for r in candidates if r[72:76] == b'ikip')
    used = {struct.unpack_from('<I', r, 8)[0] for r in practice}
    entries = list(practice)
    ids = []
    total = sum(count for _, count in SQUAD)
    red = dict(SQUAD)['red']
    for index in range(total):
        identity = SQUAD_BASE + index
        if identity in used:
            raise ValueError('Arena generator ID collision')
        used.add(identity)
        row = bytearray(template)
        struct.pack_into('<I', row, 8, identity)
        row[16:48] = b'Bulblax arena starting squad'.ljust(32, b'\0')
        write_position(row, (10.0 + (index % red) * 12, 30.0, 1890.0 + (index // red) * 12))
        struct.pack_into('>I', row, 92, 1 if index < red else 0)
        entries.append(bytes(row))
        ids.append(identity)
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), ids


def placements(profile):
    """Validate the prepared #235 profile against the recorded display placements."""
    profile = Path(profile)
    meta = json.loads((profile / 'bulblax-visual.json').read_bytes())
    if meta.get('schema') != 1 or meta.get('kind') != 'bulblax_sampled_display':
        raise ValueError('Unsupported Bulblax display profile')
    rows = meta.get('placements')
    expected_ids = [identity for identity, _, _, _ in EXPECTED]
    if not isinstance(rows, list) or sorted(row.get('placement_id') for row in rows) != expected_ids:
        raise ValueError('Bulblax arena expects the three #235 display placements')
    by_id = {row['placement_id']: row for row in rows}
    result = []
    for identity, species, clip, xyz in EXPECTED:
        row = by_id[identity]
        if row.get('species') != species or row.get('clip') != clip \
                or [float(v) for v in row.get('xyz', [])] != list(xyz):
            raise ValueError(f'Bulblax display placement {identity} changed')
        result.append(dict(placement_id=identity, species=species, clip=clip,
                           xyz=list(xyz), source_yaw=None, source_yaw_applied=False))
    return result


def prepare(assets, profile, output):
    """Build a private arena run with the normalized Bulblax display bank installed."""
    assets = assets.resolve()
    profile = profile.resolve()
    actors = placements(profile)
    data, ids = roster(assets)
    stage = assets / 'dataDir/stages/practice.ini'
    course = assets / 'dataDir/courses/practice'
    preserved = {str(path.relative_to(assets)).replace('\\', '/'): digest(path)
                 for path in course.rglob('*') if path.is_file()}
    if not preserved:
        raise ValueError('Original Impact Site course missing')
    run = output.resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': stage.read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/arena-private.txt': b'P1 original stage arena\n'}
    for path in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + path.name, empty)
    overlay(assets, run / 'assets', overrides)
    receipt = install_display(profile, run)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0',
                  actors=actors, enemy_count=0,
                  control='P1 captain with starting squad red=5 blue=5',
                  squad={'generators': ids, 'red': 5, 'blue': 5},
                  source_stage_sha256=digest(stage), preserved_course_sha256=preserved,
                  profile_sha256=receipt['profile_sha256'],
                  config_sha256=receipt['config_sha256'],
                  placements=receipt['placements'],
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  scatter='No enemy generators; sampled display overlay only, no generator scatter',
                  placement_choice='Engineered #235 display coordinates; terrain/physical '
                                   'spawn acceptance unmeasured',
                  gates={key: BLOCKED.get(key, 'untested') for key in GATES},
                  limitations=['Sampled noninteractive display only; no boss Teki, AI, hitbox, '
                               'health, combat, bomb interaction, drops or rewards',
                               'No source yaw applied to the display placements',
                               'Queen black/silver materials and KingChappy terrain intersection '
                               'remain open in #239'])
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'profile', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.profile, args.output))
