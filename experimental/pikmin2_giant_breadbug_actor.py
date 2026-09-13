"""Giant Breadbug actor profile (#220 batch 4): bind P1 Collec/Hollec pairs.

Consumes the breadbug-lane extraction (breadbug-lane-03) and stages an
installable actor profile: OoPanModoki wait1/move1 sampled poses plus the
PanHouse nest model. `install` writes `p2-giant-breadbug-actor.txt` and the
hash-verified lane models into a private run, binding each Giant generator
(P1 TEKI_Collec, type byte 8) to its owner nest generator (P1 TEKI_Hollec,
type byte 12). Scope ids 38/39/40/83 stay classified by the lane: 39 (alias)
and 83 (helper) are never made spawnable here — the nest remains an
owner-linked P1 Hollec, never an autonomous spawn.
"""
import json
import struct
from pathlib import Path

from experimental.pikmin2_breadbug_visual import read_verified, sha
from experimental.pikmin2_breadbug_lane_install import verify_mod
from scripts.preview_pikmin2_room import records

CLIPS = ('wait1', 'move1')
NAMES = {'wait1': 'wait', 'move1': 'move'}


def _clip(entry, stem):
    clips = [c for c in entry['clips'] if Path(c['file']).stem == stem]
    if len(clips) != 1 or clips[0]['status'] != 'sampled_poses_converted' or not clips[0]['poses']:
        raise ValueError(f'Missing converted OoPanModoki/{stem} poses')
    clip = clips[0]
    duration = clip['source_frames']
    frames = [p['frame'] for p in clip['poses']]
    if type(duration) is not int or not 2 <= duration <= 10000 or frames != sorted(set(frames)) \
            or frames[0] != 0 or frames[-1] != duration - 1 or not 2 <= len(frames) <= 12:
        raise ValueError(f'Invalid OoPanModoki/{stem} samples')
    return clip, duration, frames


def prepare(lane_import, output):
    """Build an installable Giant actor profile from a verified lane extraction."""
    raw = (lane_import / 'breadbug-lane.json').read_bytes()
    lane = json.loads(raw)
    if lane.get('schema') != 1 or lane.get('lane') != 213:
        raise ValueError('Unsupported lane import')
    if lane['classification']['39']['spawnable'] or lane['classification']['83']['spawnable']:
        raise ValueError('Helper/alias must remain non-spawnable')
    if not lane['classification']['40']['boss'] or lane['classification']['40']['name'] != 'OoPanModoki':
        raise ValueError('Expected boss-classified OoPanModoki source')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'models').mkdir()
    files = {}
    meta_clips = []
    giant = lane['species']['OoPanModoki']
    for stem in CLIPS:
        clip, duration, frames = _clip(giant, stem)
        for pose in clip['poses']:
            data = read_verified(lane_import / 'OoPanModoki' / pose['file'], pose['sha256'])
            verify_mod(data)
            name = f"lane_ootake_{stem}_{pose['frame']:03}.mod"
            if name in files:
                raise ValueError('Duplicate staged name')
            files[name] = data
        meta_clips.append(dict(name=NAMES[stem], duration=duration, frames=frames))
    nest = lane['species']['PanHouse']['static_pose']
    if nest.get('file') != 'nest.mod':
        raise ValueError('Missing converted nest model')
    data = read_verified(lane_import / 'PanHouse/nest.mod', nest['sha256'])
    verify_mod(data)
    files['lane_nest_nest.mod'] = data
    for name, blob in files.items():
        (output / 'models' / name).write_bytes(blob)
    result = dict(schema=1, lane=220, family='OoPanModoki',
                  behavior='P1_Collec_bound_giant_actor_P2_params',
                  params=dict(health=2000, carry_speed=45, press_damage=100,
                              press='purple_only', boss=True, bdt='empty_no_music',
                              threshold='at_or_above1'),
                  source_import_sha256=sha(raw), clips=meta_clips,
                  files={name: sha(blob) for name, blob in files.items()})
    (output / 'breadbug-giant-actor-profile.json').write_text(json.dumps(result, indent=2) + '\n',
                                                              encoding='utf-8')
    return result


def _generator_type(generator_rows, identity, marker, type_byte, label):
    matches = [r for r in generator_rows if len(r) >= 81 and struct.unpack_from('<I', r, 8)[0] == identity]
    if len(matches) != 1 or matches[0][72:76] != marker or matches[0][80] != type_byte:
        raise ValueError(f'Expected exactly one existing {label} generator')
    return matches[0]


def plan(profile, generator_rows, pairs):
    """Build the native config bytes and model map for giant/nest id pairs."""
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= 8:
        raise ValueError('Invalid giant/nest pairs')
    seen_g, seen_n = set(), set()
    rows = []
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError('Invalid giant/nest pair')
        giant, nest = pair
        if type(giant) is not int or type(nest) is not int or not 0 <= giant <= 0xffffffff \
                or not 0 <= nest <= 0xffffffff or giant == nest:
            raise ValueError('Invalid giant/nest IDs')
        _generator_type(generator_rows, giant, b'iket', 8, 'TEKI_Collec8')
        _generator_type(generator_rows, nest, b'iket', 12, 'TEKI_Hollec12')
        if giant in seen_g or nest in seen_n or nest in seen_g or giant in seen_n:
            raise ValueError('Duplicate giant/nest IDs')
        seen_g.add(giant)
        seen_n.add(nest)
        rows.append(f'{giant} {nest}')
    metadata = json.loads((profile / 'breadbug-giant-actor-profile.json').read_text())
    if metadata.get('schema') != 1 or metadata.get('family') != 'OoPanModoki' \
            or metadata.get('behavior') != 'P1_Collec_bound_giant_actor_P2_params':
        raise ValueError('Unsupported source profile')
    lines = ['P2_GIANT_BREADBUG_ACTOR_1']
    clips = metadata.get('clips', [])
    if [c.get('name') for c in clips] != ['wait', 'move']:
        raise ValueError('Missing source motion clips')
    files = {}
    for clip in clips:
        frames = clip['frames']
        duration = clip['duration']
        if type(duration) is not int or not 2 <= duration <= 10000 or frames != sorted(set(frames)) \
                or frames[0] != 0 or frames[-1] != duration - 1 or not 2 <= len(frames) <= 12:
            raise ValueError('Invalid source samples')
        lines.append(f"{clip['name']} {duration} {len(frames)} " + ' '.join(map(str, frames)))
    for name, digest in metadata['files'].items():
        if Path(name).name != name or not name.startswith(('lane_ootake_', 'lane_nest_')) \
                or not name.endswith('.mod'):
            raise ValueError('Unsafe lane model name')
        files[name] = read_verified(profile / 'models' / name, digest)
        verify_mod(files[name])
    lines.extend([str(len(rows)), *rows])
    return ('\n'.join(lines) + '\n').encode(), files, metadata


def install(profile, run, pairs):
    """Install a verified Giant actor profile into a private run directory."""
    room = run / 'assets/dataDir/courses/pikmin2room'
    generator = run / 'assets/dataDir/stages/chal0/default.gen'
    if not room.is_dir() or room.resolve() != room.absolute() or generator.resolve() != generator.absolute():
        raise ValueError('Expected private non-junction stage/model files')
    config, files, metadata = plan(profile, records(generator), pairs)
    if (run / 'p2-giant-breadbug-actor.txt').exists() or (run / 'breadbug-giant-actor.json').exists() \
            or any((room / name).exists() for name in files):
        raise ValueError('Refusing existing giant actor profile/models')
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / 'p2-giant-breadbug-actor.txt').write_bytes(config)
    result = dict(schema=1, family='OoPanModoki',
                  behavior='P1_Collec_bound_giant_actor_P2_params',
                  native_validated=False, pairs=[list(p) for p in pairs],
                  params=metadata['params'],
                  generator_sha256=sha(generator.read_bytes()), config_sha256=sha(config),
                  files={k: sha(v) for k, v in files.items()},
                  unchanged=['P1 FSM locomotion/cargo', 'P1 collision scale',
                             'nest treasure day-save persistence (engine owner)',
                             'manager lifetimes (engine owner)'])
    (run / 'breadbug-giant-actor.json').write_text(json.dumps(result, indent=2) + '\n',
                                                   encoding='utf-8')
    return result
