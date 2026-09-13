"""Breadbug lane (#220): install lane-extracted assets into a private runtime layout.

Consumes a `pikmin2_breadbug_lane` extraction (breadbug-lane.json) and installs
hash-verified MOD models for Breadbug, Giant Breadbug and the nest under a
private run's `assets/dataDir/courses/pikmin2room/`. Every install is verified
after copying; a second install into another fresh run must produce identical
bytes (reproducibility). The current native visual delegate reads only the
small-Breadbug `p2-breadbug-visual.txt` profile, so Giant/nest lane models are
staged for the requested native hook (issue #220) and are loadability-checked
here by structural MOD verification.
"""
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_breadbug_visual import read_verified, sha

MOD_REQUIRED_CHUNKS = {0, 16, 48, 80, 96, 0xFFFF}  # header, positions, materials, meshes, joints, EOF
MAX_MOD_BYTES = 16 * 1024 * 1024

# Per-species clip selection staged for the runtime: wait/move cycles.
LANE_CLIPS = {'PanModoki': ('wait1', 'move1'), 'OoPanModoki': ('wait1', 'move1')}
PREFIXES = {'PanModoki': 'lane_pan_', 'OoPanModoki': 'lane_ootake_', 'PanHouse': 'lane_nest_'}


def verify_mod(raw):
    """Structural MOD loadability check: chunk walk, required chunks, counts."""
    if not isinstance(raw, (bytes, bytearray)) or not 64 <= len(raw) <= MAX_MOD_BYTES:
        raise ValueError('Invalid MOD size')
    raw = bytes(raw)
    cursor = 0
    tags = []
    counts = {}
    while True:
        cursor += (-cursor) % 32
        if cursor + 8 > len(raw):
            raise ValueError('Truncated MOD chunk header')
        tag, size = struct.unpack_from('>II', raw, cursor)
        end = cursor + 8 + size
        if end > len(raw):
            raise ValueError('Truncated MOD chunk')
        if tag == 0xFFFF:
            tags.append(tag)
            if raw[end:].strip(b'\0'):
                raise ValueError('Trailing MOD data')
            break
        tags.append(tag)
        if size < 0:
            raise ValueError('Invalid MOD chunk size')
        if tag in (16, 17, 24, 32, 34, 48, 80, 96):
            if size < 4:
                raise ValueError('Missing MOD count')
            counts[tag] = struct.unpack_from('>I', raw, cursor + 8)[0]
        cursor = end
    if set(tags) & MOD_REQUIRED_CHUNKS != MOD_REQUIRED_CHUNKS or tags[0] != 0 or tags[-1] != 0xFFFF:
        raise ValueError('Missing required MOD chunks')
    if not counts.get(16) or not counts.get(80) or not counts.get(96):
        raise ValueError('Empty MOD geometry')
    return dict(bytes=len(raw), chunks=tags, vertices=counts[16], meshes=counts[80],
                textures=counts.get(32, 0))


def _select(lane, species):
    entry = lane['species'][species]
    picked = {}
    for stem in LANE_CLIPS.get(species, ()):
        clips = [c for c in entry['clips'] if Path(c['file']).stem == stem]
        if len(clips) != 1 or clips[0]['status'] != 'sampled_poses_converted' or not clips[0]['poses']:
            raise ValueError(f'Missing converted {species}/{stem} poses')
        picked[stem] = clips[0]
    return entry, picked


def prepare(lane_import, output):
    """Build an installable lane profile from a verified lane extraction."""
    raw = (lane_import / 'breadbug-lane.json').read_bytes()
    lane = json.loads(raw)
    if lane.get('schema') != 1 or lane.get('lane') != 213:
        raise ValueError('Unsupported lane import')
    if lane['classification']['39']['spawnable'] or lane['classification']['83']['spawnable']:
        raise ValueError('Helper/alias must remain non-spawnable')
    output.mkdir(parents=True, exist_ok=False)
    models = output / 'models'
    models.mkdir()
    files = {}
    rows = []
    for species in ('PanModoki', 'OoPanModoki'):
        entry, picked = _select(lane, species)
        for stem, clip in picked.items():
            for pose in clip['poses']:
                data = read_verified(lane_import / species / pose['file'], pose['sha256'])
                verify_mod(data)
                name = f"{PREFIXES[species]}{stem}_{pose['frame']:03}.mod"
                if name in files:
                    raise ValueError('Duplicate staged name')
                files[name] = data
                rows.append(dict(species=species, clip=stem, source_frame=pose['frame'],
                                 file=name, sha256=sha(data)))
    nest = lane['species']['PanHouse']['static_pose']
    if nest.get('file') != 'nest.mod':
        raise ValueError('Missing converted nest model')
    data = read_verified(lane_import / 'PanHouse/nest.mod', nest['sha256'])
    verify_mod(data)
    files[PREFIXES['PanHouse'] + 'nest.mod'] = data
    rows.append(dict(species='PanHouse', clip=None, source_frame=None,
                     file=PREFIXES['PanHouse'] + 'nest.mod', sha256=sha(data)))
    for name, data in files.items():
        (models / name).write_bytes(data)
    result = dict(schema=1, lane=220, purpose='runtime_install_staging',
                  source_import_sha256=sha(raw), native_hook='pending; issue #220',
                  spawnable={'PanModoki': True, 'OoPanModoki': True,
                             'PanModokiNest': False, 'PanHouse': False},
                  files={name: sha(data) for name, data in files.items()}, rows=rows)
    (output / 'breadbug-lane-profile.json').write_text(json.dumps(result, indent=2) + '\n',
                                                       encoding='utf-8')
    return result


def install(profile, run):
    """Copy a verified lane profile into a private run's course directory."""
    metadata = json.loads((profile / 'breadbug-lane-profile.json').read_text())
    if metadata.get('schema') != 1 or metadata.get('lane') != 220:
        raise ValueError('Unsupported lane profile')
    room = run / 'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.resolve() != room.absolute():
        raise ValueError('Expected private non-junction model directory')
    files = {}
    for name, digest in metadata['files'].items():
        if Path(name).name != name or not name.startswith('lane_') or not name.endswith('.mod'):
            raise ValueError('Unsafe lane model name')
        files[name] = read_verified(profile / 'models' / name, digest)
        verify_mod(files[name])
    if (run / 'breadbug-lane-install.json').exists() or any((room / name).exists() for name in files):
        raise ValueError('Refusing existing lane installation')
    for name, data in files.items():
        (room / name).write_bytes(data)
    installed = {}
    for name in files:  # post-copy verification of the installed bytes
        data = (room / name).read_bytes()
        if sha(data) != metadata['files'][name]:
            raise ValueError('Installed byte mismatch: ' + name)
        installed[name] = verify_mod(data) | dict(sha256=sha(data))
    result = dict(schema=1, profile_sha256=sha((profile / 'breadbug-lane-profile.json').read_bytes()),
                  installed=installed, native_hook='pending; issue #220')
    (run / 'breadbug-lane-install.json').write_text(json.dumps(result, indent=2) + '\n',
                                                    encoding='utf-8')
    return result


def verify_installation(run):
    """Re-verify an existing lane installation against its manifest."""
    result = json.loads((run / 'breadbug-lane-install.json').read_text())
    if result.get('schema') != 1:
        raise ValueError('Unsupported lane installation')
    room = run / 'assets/dataDir/courses/pikmin2room'
    for name, record in result['installed'].items():
        data = (room / name).read_bytes()
        if sha(data) != record['sha256']:
            raise ValueError('Installed file changed: ' + name)
        check = verify_mod(data)
        if check['vertices'] != record['vertices'] or check['meshes'] != record['meshes']:
            raise ValueError('Installed structure changed: ' + name)
    return result
