"""Stage the native OWN Antenna Beetle (P2 Fuefuki, source 41) campaign inputs (#245).

The native campaign module (``engine`` ``pc_port/pc_p2_fuefuki_teki.cpp``, policy
``pc_p2_fuefuki_teki_policy.h``) binds every seed-placed 41 to the engine-free
source FSM and reads, from the run root:

* ``p2-fuefuki-parms.txt``: the verbatim retail ``fuefuki/enemyparm.txt``
  (general fp00/fp06/fp08/fp28/fp09/fp10/fp11/fp16-fp19/fp22/fp23 and the
  proper fp01-fp31 block), parsed by ``p2fuefuki::parseEnemyParm``;
* ``p2-fuefuki-motion.txt``: the ``P2_RETAIL_EVENTS_1`` table of all ten
  FUEFUKIANIM clips (durations, loop markers, KEYEVENT_2/3) from
  ``experimental.pikmin2_fuefuki_motion``, fed to the verified retail player;
* ``p2-fuefuki-bank.txt``: ``P2_FUEFUKI_BANK_1 <n>`` then
  ``clip <name> <frames> <poses> <frame>...`` rows and ``END`` -- the sampled
  pose frame of every staged ``fuefuki_Fuefuki_<clip>_<ii>.mod``;

and the pose meshes in the private model room
``assets/dataDir/courses/pikmin2room/`` (the draw hook). Nothing here reads a
disc: the plan comes from a ``pikmin2_fuefuki_assets`` extractor tree
(``fuefuki.json`` + the ``Fuefuki`` import directory contents).
"""
import hashlib
import json
from pathlib import Path

from experimental import pikmin2_fuefuki_motion as motion

PARMS_TXT = 'p2-fuefuki-parms.txt'
MOTION_TXT = 'p2-fuefuki-motion.txt'
BANK_TXT = 'p2-fuefuki-bank.txt'
BANK_HEADER = 'P2_FUEFUKI_BANK_1'
ROOM = 'assets/dataDir/courses/pikmin2room'
MANIFEST = 'fuefuki.json'
CLIPS = ('dead', 'landing', 'landfail', 'move', 'pivot', 'wait', 'whisle', 'struggle', 'jump', 'carry')
MAX_POSES = 24          # native loadPoses bound
MESH_BYTES = 1024 * 1024
TOTAL_BYTES = 24 * 1024 * 1024


class FuefukiStageError(ValueError):
    pass


def pose_name(clip, number):
    return f'fuefuki_Fuefuki_{clip}_{number:02}.mod'


def _manifest(source):
    path = Path(source) / MANIFEST
    if not path.is_file():
        raise FuefukiStageError(f'missing {MANIFEST} in {source}')
    data = json.loads(path.read_text(encoding='utf-8'))
    try:
        return data['species']['Fuefuki']
    except (KeyError, TypeError) as error:
        raise FuefukiStageError('fuefuki.json has no Fuefuki species') from error


def bank_text(rows):
    """Serialise the native ``P2_FUEFUKI_BANK_1`` grammar (fail closed)."""
    if not 1 <= len(rows) <= len(CLIPS):
        raise FuefukiStageError('bank clip count out of range')
    lines = [f'{BANK_HEADER} {len(rows)}']
    seen = set()
    for name, frames, poses in rows:
        if name not in CLIPS or name in seen:
            raise FuefukiStageError(f'bad clip {name!r}')
        seen.add(name)
        if type(frames) is not int or not 1 <= frames <= 10000 or len(poses) > MAX_POSES:
            raise FuefukiStageError(f'bad clip bounds for {name}')
        for i, frame in enumerate(poses):
            if type(frame) is not int or not 0 <= frame < frames or (i and frame <= poses[i - 1]):
                raise FuefukiStageError(f'bad pose frame for {name}')
        lines.append(' '.join(['clip', name, str(frames), str(len(poses))] + [str(f) for f in poses]))
    lines.append('END')
    return ('\n'.join(lines) + '\n').encode('ascii')


def plan(source):
    """Build ``{files: {name: bytes}, room: [(name, bytes)], summary}`` from a tree."""
    source = Path(source)
    info = _manifest(source)
    parm = source / 'enemyparm.txt'
    if not parm.is_file():
        raise FuefukiStageError('missing retail enemyparm.txt')
    table = motion.encode(source)
    rows, room, total = [], [], 0
    by_name = {clip['name']: clip for clip in info['clips']}
    for name in CLIPS:
        clip = by_name.get(name)
        if clip is None or clip.get('status') != 'converted':
            raise FuefukiStageError(f'clip {name} not converted: {clip and clip.get("unsupported_reason")}')
        poses = [pose for pose in clip['poses'] if 'file' in pose]
        frames = []
        for number, pose in enumerate(poses):
            path = source / pose['file']
            data = path.read_bytes()
            if len(data) > MESH_BYTES or hashlib.sha256(data).hexdigest() != pose['sha256']:
                raise FuefukiStageError(f'pose mismatch {pose["file"]}')
            total += len(data)
            room.append((pose_name(name, number), data))
            frames.append(int(pose['frame']))
        rows.append((name, int(clip['source_frames']), frames))
    if total > TOTAL_BYTES:
        raise FuefukiStageError('pose bank over budget')
    files = {PARMS_TXT: parm.read_bytes(), MOTION_TXT: table, BANK_TXT: bank_text(rows)}
    return dict(files=files, room=room,
                summary=dict(clips=len(rows), poses=len(room), pose_bytes=total))


def stage(run, planned):
    run = Path(run)
    room = run / ROOM
    if not room.is_dir() or not room.resolve().is_relative_to(run.resolve()):
        raise FuefukiStageError('Fuefuki staging needs the private model room')
    for name, data in planned['files'].items():
        path = run / name
        if path.exists() and path.read_bytes() != data:
            raise FuefukiStageError(f'refusing to replace existing {name}')
        path.write_bytes(data)
    for name, data in planned['room']:
        path = room / name
        if path.exists() and path.read_bytes() != data:
            raise FuefukiStageError(f'refusing existing pose {name}')
        path.write_bytes(data)
    receipt = dict(planned['summary'])
    receipt.update({name: hashlib.sha256(data).hexdigest() for name, data in planned['files'].items()})
    return receipt


def stage_from(source, run):
    return stage(run, plan(source))
