"""Source-backed, bounded local aquatic-enemy import; no native actor install.

Covers enemy IDs 26 Catfish (Water Dumple), 27 Tadpole (Wogpole), 63 Jigumo
(Hermit Crawmad) with 64 JigumoNest (PanHouse helper alias, no table row) and
100 UmiMushiBase / 101 UmiMushiBlind (shared UmiMushi::Mgr, base has no spawn
flag). Disc revision US GPVE01 rev 0. Source audit:
docs/PIKMIN2_AQUATIC_REMAINDER_ASSETS.md (issue #347, parent #167). Extraction
follows the Bulblax/Frog lanes: hashed disc reads, preserved metadata text,
bounded rigid pose sampling (UmiMushi weighted), byte-preserved extra textures.
No btk playback, no behavior execution.
"""
import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import time
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_sheargrub_assets import joints
from experimental.pikmin2_breadbug_assets import parameter_blocks, collision_nodes
from experimental.pikmin2_convert import blocks, decode, u16, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

# Concrete generator IDs. UmiMushi, UmiMushiBase and UmiMushiBlind share the
# generic data/resources below; opaque import name is the shared UmiMushi key.
SPECIES = {'Catfish': 26, 'Tadpole': 27, 'Jigumo': 63, 'UmiMushi': 71}
PARM_SOURCE = 'enemy/parm/enemyParms.szs'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
# Jigumo ships a shared Kochappy-family S3TC texture copy; UmiMushi ships its
# material palette animation. Both are hashed and byte-preserved only.
EXTRA_DISC_FILES = {'Jigumo': 'enemy/data/Jigumo/kochappy_body_s3tc.1.bti',
                    'UmiMushi': 'enemy/data/UmiMushi/umimusi_model1.btk'}
MAX_POSES = 12

# enemyanimmgr.txt registration order (with duplicate names where the disc has
# them): (file stem, events). Catfish repeats wait1.bca three times; only the
# first registration (the one a name-index lookup resolves) drives
# EXPECTED_EVENTS, the later footstep variant is still enforced here by order.
MGR_ROWS = {
    'Catfish': (('attack', [[17, 2], [75, 3]]), ('dead', []), ('flick', [[25, 2], [47, 3]]),
                ('move1', [[0, 0], [24, 1]]), ('wait1', []), ('type5', [[10, 0], [29, 1]]),
                ('wait1', [[0, 0], [29, 1]]), ('wait1', [[0, 0], [29, 1]]), ('waitact2', [])),
    'Tadpole': (('dead', [[3, 2], [17, 2]]), ('wait1', [[5, 0], [24, 1]]),
                ('move1', [[5, 0], [14, 1]]), ('waitact1', [[3, 2], [12, 3]]),
                ('piti1', [[14, 2], [15, 0], [29, 3], [30, 4], [44, 1]]), ('type5', [[10, 0], [29, 1]])),
    'Jigumo': (('appear1', [[10, 2]]), ('attack1', [[26, 2]]), ('backrun1', [[10, 0], [19, 1]]),
               ('backwait1', [[0, 0], [9, 1]]), ('dead1', [[24, 2]]),
               ('dive1', [[23, 2], [28, 3], [33, 4], [38, 5], [43, 6], [59, 7], [80, 8]]),
               ('flick1', [[9, 2], [16, 3]]), ('hide1', []), ('rdive1', []),
               ('rflick1', [[14, 2], [21, 3]]), ('runaway1', [[0, 0], [19, 1]]),
               ('sattack1', [[15, 2], [26, 3], [56, 4], [61, 5], [66, 6], [71, 7], [76, 8], [91, 9], [115, 10]]),
               ('smiss1', []), ('turn1', [[0, 0], [14, 1]]), ('type5', [[10, 0], [29, 1]]),
               ('wait1', [[0, 0], [29, 1]]), ('to_runaway1', [])),
    'UmiMushi': (('attack1', [[25, 2], [39, 3], [40, 4], [50, 5], [66, 6]]),
                 ('dead1', [[83, 2], [110, 3], [113, 4]]), ('eat1', []), ('flick1', [[9, 2]]),
                 ('run1', [[0, 0], [59, 1]]), ('search1', [[48, 2]]),
                 ('srun1', [[0, 0], [39, 1]]), ('sturn1', [[0, 0], [39, 1]]),
                 ('type5', [[10, 0], [29, 1]]), ('outview1', []), ('fsearch1', [])),
}

# First registration per stem (the name-index-resolved row the runtime uses).
EXPECTED_EVENTS = {}
for _species, _rows in MGR_ROWS.items():
    _first = {}
    for _stem, _events in _rows:
        _first.setdefault(_stem, _events)
    EXPECTED_EVENTS[_species] = _first

# Shipped .bca file order on disc (anim.szs). CLIPS equals the shipped set.
REGISTRY = {species: tuple(stem for stem, _ in rows) for species, rows in MGR_ROWS.items()}
CLIPS = {'Catfish': ('attack', 'dead', 'flick', 'move1', 'type5', 'wait1', 'waitact2'),
         'Tadpole': ('dead', 'move1', 'piti1', 'type5', 'wait1', 'waitact1'),
         'Jigumo': ('appear1', 'attack1', 'backrun1', 'backwait1', 'dead1', 'dive1', 'flick1',
                    'hide1', 'rdive1', 'rflick1', 'runaway1', 'sattack1', 'smiss1',
                    'to_runaway1', 'turn1', 'type5', 'wait1'),
         'UmiMushi': ('attack1', 'dead1', 'eat1', 'fsearch1', 'flick1', 'outview1', 'run1',
                      'search1', 'srun1', 'sturn1', 'type5', 'wait1')}

# Shipped .bca with no enemyanimmgr.txt entry on this disc revision; catalog and
# pose-sampled but unregistered (UmiMushi wait1 ships in anim.szs but is not
# listed, so it has no AnimID: UmiMushi.h:299-312 has no Wait entry either).
UNREGISTERED = {'UmiMushi': ('wait1',)}

# AnimID enum semantics from the header decls; authoritative for the report even
# though Jigumo's enemyanimmgr.txt row order differs from AnimID order (the
# animmgr registers in designer file order, e.g. dive1 is AnimID Eat=5).
# KochappyBase.h:129-139 (Catfish), Tadpole.h:108-115, Jigumo.h:319-339,
# UmiMushi.h:299-312.
ANIM_IDS = {
    'Catfish': {'attack': 0, 'dead': 1, 'flick': 2, 'move1': 3, 'type5': 5, 'wait1': 6, 'waitact2': 8},
    'Tadpole': {'dead': 0, 'wait1': 1, 'move1': 2, 'waitact1': 3, 'piti1': 4, 'type5': 5},
    'Jigumo': {'appear1': 0, 'attack1': 1, 'backrun1': 2, 'backwait1': 3, 'dead1': 4, 'dive1': 5,
               'flick1': 6, 'hide1': 7, 'rdive1': 8, 'rflick1': 9, 'runaway1': 10, 'sattack1': 11,
               'smiss1': 12, 'turn1': 13, 'type5': 14, 'wait1': 15, 'to_runaway1': 16},
    'UmiMushi': {'attack1': 0, 'dead1': 1, 'eat1': 2, 'flick1': 3, 'run1': 4, 'search1': 5,
                 'srun1': 6, 'sturn1': 7, 'type5': 8, 'outview1': 9, 'fsearch1': 10},
}

# State IDs: KochappyBase.h:155-163 (Catfish), Tadpole.h:19-27, Jigumo.h:36-51,
# UmiMushi.h:57-69.
STATE_IDS = {'Catfish': {'wait': 0, 'dead': 1, 'turn': 2, 'walk': 3, 'attack': 4,
                         'flick': 5, 'turntohome': 6, 'gohome': 7, 'press': 8},
             'Tadpole': {'dead': 0, 'wait': 1, 'move': 2, 'amaze': 3, 'escape': 4, 'leap': 5},
             'Jigumo': {'wait': 0, 'appear': 1, 'hide': 2, 'dead': 3, 'attack': 4, 'miss': 5,
                        'return': 6, 'carry': 7, 'flick': 8, 'eat': 9, 'search': 10,
                        'sattack': 11, 'smiss': 12},
             'UmiMushi': {'wait': 0, 'walk': 1, 'find': 2, 'search': 3, 'turn': 4, 'flick': 5,
                          'attack': 6, 'eat': 7, 'dead': 8, 'lost': 9}}

# ProperParms header defaults: KochappyBase.h:105-107, Tadpole.h:87-88,
# Jigumo.h:98-103, UmiMushi.h:76-89.
PROPER_PARM_DEFAULTS = {'Catfish': {'fp01': 2.0, 'fp02': 300.0, 'fp03': 90.0},
                        'Tadpole': {'fp01': 20.0},
                        'Jigumo': {'fp01': 100.0, 'fp02': 100.0, 'fp03': 1.0,
                                   'fp04': 1.2, 'fp05': 300.0, 'ip01': 30},
                        'UmiMushi': {'fp01': 1.0, 'fp02': 60.0, 'fp03': 10.0, 'fp04': 10.0,
                                     'fp06': 0.1, 'fp07': 5.0, 'fp09': 0.0, 'fp10': 200.0,
                                     'fp11': 300.0, 'fp12': 1000.0, 'fp13': 200.0,
                                     'fp14': 200.0, 'ip01': 100}}

# Retail (disc) values verified against enemyParms.szs on US GPVE01 rev 0.
# Keys are (block, parm): 'general' is the first EnemyParmsBase block, 'proper'
# the species block. Audit semantics: Catfish fp22 attack hit 50 and 200 HP /
# 280 territory; Tadpole 200 HP / 180 speed and zero attack; Jigumo 500 HP /
# 400 territory / carry speed fp01 75 / return fp02 30; UmiMushi 1500 HP /
# 700 sight / attack hit fp22 170, damage rate fp01 0.03, Blind health fp12 800.
DISC_PARMS = {'Catfish': {'general': {'fp00': 200.0, 'fp06': 60.0, 'fp09': 280.0, 'fp10': 80.0,
                                      'fp12': 200.0, 'fp20': 50.0, 'fp22': 50.0, 'fp24': 10.0},
                          'proper': {'fp01': 2.0, 'fp02': 300.0, 'fp03': 90.0}},
              'Tadpole': {'general': {'fp00': 200.0, 'fp06': 180.0, 'fp09': 200.0, 'fp10': 50.0,
                                      'fp12': 200.0, 'fp24': 0.0},
                          'proper': {'fp01': 20.0}},
              'Jigumo': {'general': {'fp00': 500.0, 'fp06': 300.0, 'fp09': 400.0, 'fp10': 25.0,
                                     'fp12': 400.0, 'fp20': 200.0, 'fp24': 10.0},
                         'proper': {'fp01': 75.0, 'fp02': 30.0, 'fp03': 1.0, 'fp04': 2.0,
                                    'fp05': 500.0, 'ip01': 30}},
              'UmiMushi': {'general': {'fp00': 1500.0, 'fp06': 15.0, 'fp09': 300.0, 'fp10': 30.0,
                                       'fp12': 700.0, 'fp20': 30.0, 'fp22': 170.0, 'fp24': 10.0},
                           'proper': {'fp01': 0.03, 'fp02': 30.0, 'fp03': 10.0, 'fp04': 85.0,
                                      'fp06': 0.05, 'fp07': 2.5, 'fp09': 0.05, 'fp10': 300.0,
                                      'fp11': 200.0, 'fp12': 800.0, 'fp13': 200.0,
                                      'fp14': 200.0, 'ip01': 0}}}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

LIMITATIONS = ['Sampled rigid poses (UmiMushi weighted) with approximate materials; no skeletal playback or event execution.',
               'Animation key events, loop markers and parameter text are preserved as data only; no damage, drop, birth or flick behavior executes.',
               'Jigumo kochappy_body_s3tc.1.bti is hashed and byte-preserved only; no S3TC texture repackaging or referential rewrite.',
               'UmiMushi umimusi_model1.btk is hashed and byte-preserved only; no btk (texture animation) playback.',
               'UmiMushi wait1.bca ships in anim.szs but has no enemyanimmgr.txt entry on this disc revision; it is cataloged and pose-sampled as unregistered (UmiMushi.h AnimID has no Wait clip).',
               'Catfish wait1.bca is registered three times in enemyanimmgr.txt; EXPECTED_EVENTS uses the first (name-index-resolved) registration, the footstep variant is enforced by MGR_ROWS order.',
               'No native runtime, AI/FSM, install or arena placement is provided by this slice.']

# Opt-in converter tolerances per species (#186); strict defaults everywhere else.
TOLERANCES = {}

TEXT = ('P2_AQUATIC_1\n'
        'species Catfish Tadpole Jigumo UmiMushi\n'
        'catfish_health 200\ncatfish_speed 60\ncatfish_territory 280\ncatfish_attack_range 50\n'
        'tadpole_health 200\ntadpole_speed 180\ntadpole_territory 200\n'
        'jigumo_health 500\njigumo_speed 300\njigumo_territory 400\njigumo_carry_speed 75\njigumo_return_speed 30\n'
        'umimushi_health 1500\numimushi_speed 15\numimushi_sight 700\numimushi_attack_range 170\n'
        'umimushi_damage_rate 0.03\numimushi_blind_health 800\n'
        'native_ready false\ngameplay_events_executed false\nbtk_playback false\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def anim_mgr_rows(text):
    """Parse enemyanimmgr.txt without the shared helper's unique-name check.

    Catfish registers wait1.bca three times; this lane must preserve every
    registration (row order + events) so it parses here with the same token
    rules as animation_rows but keeps duplicates.
    """
    clean = re.sub(r'#[^\r\n]*', '', text)
    count = int(clean.split()[0])
    rows = []
    for block in re.findall(r'\{([^{}]*)\}', clean):
        fields = block.split()
        if len(fields) < 3 or not re.fullmatch(r'[a-z0-9_]+\.bca', fields[1]) or fields[-1] != '-1':
            raise ValueError('Invalid animation registration')
        events = fields[2:-1]
        if len(events) % 2:
            raise ValueError('Invalid animation event pairs')
        rows.append({'file': fields[1],
                     'events': [[int(events[i]), int(events[i + 1])] for i in range(0, len(events), 2)]})
    if len(rows) != count:
        raise ValueError('Animation registry count mismatch')
    return rows


def profile(species, blocks_list, rows):
    """Validate parsed metadata for one species against the source contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt): creature, general,
    proper in order. ``rows`` is animation_rows(enemyanimmgr.txt) in
    registration order (duplicates preserved). Header defaults and disc
    values are reported separately, never flattened.
    """
    if species not in SPECIES:
        raise ValueError('Unknown aquatic species')
    if len(blocks_list) != 3:
        raise ValueError(f'Expected 3 parameter blocks for {species}')
    general, proper = blocks_list[1], blocks_list[2]
    if set(proper) != set(PROPER_PARM_DEFAULTS[species]):
        raise ValueError(f'Unexpected {species} proper parameter keys: {sorted(proper)}')
    for group in ('general', 'proper'):
        source = general if group == 'general' else proper
        for key, value in DISC_PARMS[species][group].items():
            if key not in source or not math.isclose(source[key], float(value), rel_tol=0, abs_tol=1e-6):
                raise ValueError(f'{species} disc {group} parameter {key} mismatch')
    registration = tuple((Path(r['file']).stem, [list(e) for e in r['events']]) for r in rows)
    if registration != MGR_ROWS[species]:
        raise ValueError(f'Unexpected {species} animmgr registration: {registration}')
    expected = {}
    for stem, events in registration:
        expected.setdefault(stem, events)
    if expected != EXPECTED_EVENTS[species]:
        raise ValueError(f'{species} first-registration event drift: {expected}')
    for stem in CLIPS[species]:
        if stem in EXPECTED_EVENTS[species] or stem in UNREGISTERED.get(species, ()):
            continue
        raise ValueError(f'{species} shipped clip {stem} is neither registered nor unregistered')
    return {'enemy_id': SPECIES[species], 'state_ids': dict(STATE_IDS[species]),
            'anim_id_by_clip': dict(ANIM_IDS[species]),
            'parameter_blocks': blocks_list,
            'proper_header_defaults': dict(PROPER_PARM_DEFAULTS[species]),
            'proper_retail': {k: proper[k] for k in PROPER_PARM_DEFAULTS[species]}}


def extract(iso, source, output, pose_limit=6):
    if type(pose_limit) is not int or not 2 <= pose_limit <= MAX_POSES:
        raise ValueError(f'Pose limit must be 2..{MAX_POSES}')
    if output.exists():
        raise ValueError('Output already exists')
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('Invalid source revision')
    index = disc_files(iso)
    source_hashes = {}
    started = time.perf_counter()
    with iso.open('rb') as disc:
        header = disc.read(8)
        if header[:6] != b'GPVE01':
            raise ValueError('Expected supplied US GPVE01 disc')

        def read(name):
            at, size = index[name]
            disc.seek(at)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated ISO resource')
            source_hashes[name] = sha(raw)
            return raw

        params = archive_files(read(PARM_SOURCE))
        output.mkdir(parents=True)
        report = dict(schema=1, policy='P2_AQUATIC_IMPORT_1', disc_id=header[:6].decode(),
                      disc_revision=header[7], source_revision=head, source_sha256=source_hashes,
                      native_ready=False, gameplay_events_executed=False, btk_playback=False,
                      species={}, total_pose_bytes=0, total_poses=0)
        for species, identity in SPECIES.items():
            root = output / species
            root.mkdir()
            model = archive_files(read(f'enemy/data/{species}/model.szs'))['enemy.bmd']
            model_blocks = blocks(model)
            motions = archive_files(read(f'enemy/data/{species}/anim.szs'))
            names = joints(model)
            (root / 'enemy.bmd').write_bytes(model)
            metadata = {}
            for filename in METADATA_FILES:
                raw = params[species.lower() + '/' + filename]
                metadata[filename] = sha(raw)
                (root / filename).write_bytes(raw)
            extra = {}
            if species in EXTRA_DISC_FILES:
                raw = read(EXTRA_DISC_FILES[species])
                name = Path(EXTRA_DISC_FILES[species]).name
                (root / name).write_bytes(raw)
                extra[name] = {'sha256': sha(raw), 'bytes': len(raw), 'playback': 'none; byte-preserved only'}
            envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
            draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
            blocks_list = parameter_blocks(params[species.lower() + '/enemyparm.txt'])
            rows = anim_mgr_rows(params[species.lower() + '/enemyanimmgr.txt'].decode('shift_jis'))
            info = profile(species, blocks_list, rows)
            roles = {'Catfish': 'concrete spawnable; KochappyBase::Obj subclass',
                     'Tadpole': 'concrete spawnable',
                     'Jigumo': 'concrete spawnable; owns PanHouse child (JigumoNest alias, no table row)',
                     'UmiMushi': 'concrete spawnable (EnemyID_UmiMushi); shares UmiMushi::Mgr with base 100 and Blind 101 on UmiMushi resources'}
            info.update(role=roles[species], model_sha256=sha(model), joints=names,
                        metadata_sha256=metadata,
                        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                                      weighted_baking=envelopes > 0,
                                      self_contained_resources=draws > 0),
                        collision=collision_nodes(params[species.lower() + '/enemycoll.txt'], len(names)),
                        extra_files=extra, clips=[])
            registered = set(EXPECTED_EVENTS[species])
            reference = None
            for stem in CLIPS[species]:
                raw = motions[stem + '.bca']
                (root / (stem + '.bca')).write_bytes(raw)
                events = EXPECTED_EVENTS[species].get(stem, [])
                if raw[40] not in LOOPS:
                    raise ValueError('Unsupported source loop attribute')
                clip = dict(name=stem, source_sha256=sha(raw), events=events, registered=stem in registered,
                            loop_attribute=raw[40], loop_semantics=LOOPS[raw[40]],
                            event_loop_boundaries=[r for r in events if r[1] in (0, 1)],
                            poses=[], status='unsupported')
                try:
                    duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
                    clip['source_frames'] = duration
                    frames = sample_frames(duration, pose_limit)
                    for number, frame in enumerate(frames):
                        try:
                            _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                            matrices = draw_matrices(model_blocks, pose)
                            tolerances = TOLERANCES.get(species, {})
                            decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices, **tolerances)
                            name = f'aquatic_{species}_{stem}_{number:02}.mod'
                            conversion = write_model(decoded, root / name, 'enemy.bmd')
                            conversion.update(source='enemy.bmd', output=name,
                                              weighted_pose_baked=envelopes > 0)
                            data = (root / name).read_bytes()
                            resources = resource_chunks(data)
                            if reference is not None and resources != reference:
                                raise ValueError('Aquatic pose changes immutable render resources')
                            reference = resources
                            report['total_pose_bytes'] += len(data)
                            report['total_poses'] += 1
                            clip['poses'].append(dict(file=name, frame=frame, bytes=len(data), sha256=sha(data)))
                            (root / Path(name).with_suffix('.json')).write_bytes(
                                (json.dumps(conversion, sort_keys=True, indent=2) + '\n').encode())
                        except (ValueError, KeyError, ArithmeticError) as error:
                            # Converter limitation; recorded, never fabricated.
                            clip['poses'].append(dict(frame=frame, unsupported_reason=f'{type(error).__name__}: {error}'))
                except (ValueError, KeyError, ArithmeticError) as error:
                    # Clip-level decode failure (bca_pose/sample_frames).
                    clip['unsupported_reason'] = f'{type(error).__name__}: {error}'
                converted = [p for p in clip['poses'] if 'file' in p]
                if converted:
                    clip['status'] = 'converted'
                else:
                    clip['unsupported_reason'] = clip.get('unsupported_reason') or (
                        clip['poses'][0]['unsupported_reason'] if clip['poses'] else 'no sampled frames')
                info['clips'].append(clip)
            report['species'][species] = info
        report['limitations'] = list(LIMITATIONS)
        manifest = {k: v for k, v in report.items()
                    if k != 'extract_seconds'}
        (output / 'aquatic.json').write_bytes((json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
        report['extract_seconds'] = round(time.perf_counter() - started, 3)
        (output / 'p2-aquatic.txt').write_text(TEXT)
        return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'source', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--pose-limit', type=int, default=6)
    a = p.parse_args()
    r = extract(a.iso, a.source, a.output, a.pose_limit)
    print(json.dumps({'bytes': r['total_pose_bytes'], 'poses': r['total_poses'],
                      'seconds': r['extract_seconds'],
                      'species': {s: {'clips': len(v['clips']),
                                      'converted': sum(c['status'] == 'converted' for c in v['clips']),
                                      'poses': sum(1 for c in v['clips'] for p in c['poses'] if 'file' in p),
                                      'unsupported_poses': sum(1 for c in v['clips'] for p in c['poses'] if 'file' not in p),
                                      'skinning': v['skinning']}
                                  for s, v in r['species'].items()}}, indent=2))