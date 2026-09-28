"""Stage the native Careening Dirigibug (58 BombSarai) OWN campaign inputs (#244).

The native OWN port (``engine`` ``pc_port/pc_p2_bombsarai_own_teki.cpp``) drives
every campaign-bound source-58 actor with the engine-free source machine
(``pc_port/pc_p2_bombsarai_own.cpp``) and reads, from the run root:

* ``p2-bombsarai-parms.txt``: the verbatim retail ``bombsarai/enemyparm.txt``
  (``p2bsown::parseEnemyParm``);
* ``p2-bombsarai-bomb-parms.txt``: the verbatim retail ``bomb/enemyparm.txt``
  (``p2bsown::parseBombParm``);
* ``p2-bombsarai-own-bank.txt``: retail clip frame counts (bca header), the
  ``bombsarai/enemyanimmgr.txt`` key events, the staged pose frames with the
  model-space ``kamu_jnt1`` translation at each pose (the joint the source
  captures the held Bomb at), plus the Bomb payload pose rows
  (``p2bsown::parseBank``; grammar reproduced by :func:`parse_bank`);
* ``p2-bombsarai-teki.txt``: ``P2_BOMBSARAI_TEKI_1 1 <generator> 11``. The
  campaign setup binds actors from the seed (source 58 -> TEKI_Napkid), so the
  generator is a placeholder there; the row keeps the room-preview grammar.

and the pose meshes ``bombsarai_BombSarai_<clip>_<ii>.mod`` (already staged by
``pikmin2_bombsarai_install``) and ``bombsarai_Bomb_<clip>_<ii>.mod`` (staged
here) from the private model room ``assets/dataDir/courses/pikmin2room/``.

Nothing here reads a disc: the plan is built from the
``experimental.pikmin2_bombsarai_assets`` extraction tree (``bombsarai.json``,
``BombSarai/`` and ``Bomb/``).
"""
import hashlib
import json
import math
import struct
from pathlib import Path

PARMS_TXT = 'p2-bombsarai-parms.txt'
BOMB_PARMS_TXT = 'p2-bombsarai-bomb-parms.txt'
BANK_TXT = 'p2-bombsarai-own-bank.txt'
BANK_HEADER = 'P2_BOMBSARAI_OWN_BANK_1'
TEKI_TXT = 'p2-bombsarai-teki.txt'
TEKI_HEADER = 'P2_BOMBSARAI_TEKI_1'
HOST_TYPE = 11  # TEKI_Napkid
ROOM = 'assets/dataDir/courses/pikmin2room'
KAMU_JOINT = 'kamu_jnt1'

# BombSarai.h:161-177 AnimID order == retail enemyanimmgr.txt rows.
CLIPS = ('dead1', 'fall1', 'flick1', 'bflick1', 'mogaki1', 'release1', 'run1',
         'run2', 'supli1', 'takeoff1', 'takeoff2', 'type5', 'wait1', 'wait2')
BOMB_CLIPS = ('hit_start', 'hit_loop')

# Native parseBank bounds (pc_p2_bombsarai_own.cpp).
MAX_FRAMES = 10000
MAX_EVENTS = 64
MAX_POSES = 24
MAX_FILE = 99
MAX_KAMU = 10000.0
MESH_BYTES = 1024 * 1024


class BombSaraiStageError(ValueError):
    pass


def pose_name(species, clip, number):
    """Native pose filename (pikmin2_bombsarai_assets naming)."""
    return f'bombsarai_{species}_{clip}_{number:02}.mod'


def bca_frames(raw):
    """Frame count from the J3D ANF1 section header (u16 at 0x2A)."""
    if len(raw) < 0x2C or raw[0x20:0x24] != b'ANF1':
        raise BombSaraiStageError('not a bca (ANF1) animation')
    return struct.unpack_from('>H', raw, 0x2A)[0]


# ------------------------------------------------------------------ bank
def _fmt(value):
    return format(float(value), '.6g')


def bank_text(clips, bombs):
    """Serialise ``P2_BOMBSARAI_OWN_BANK_1``; validates every native bound.

    ``clips``: ``[{anim_id, name, frames, events: [(f, t)], poses: [(frame,
    file, (kx, ky, kz))]}]``; ``bombs``: ``[{name, frames, poses: [(frame,
    file)]}]``.
    """
    if not 1 <= len(clips) <= len(CLIPS):
        raise BombSaraiStageError('bank clip count out of range')
    if len(bombs) > 2:
        raise BombSaraiStageError('too many bomb clips')
    rows = [f'{BANK_HEADER} {len(clips)}']
    seen = set()
    for clip in clips:
        anim, name, frames = clip['anim_id'], clip['name'], clip['frames']
        events, poses = list(clip['events']), list(clip['poses'])
        if type(anim) is not int or not 0 <= anim < len(CLIPS) or anim in seen:
            raise BombSaraiStageError(f'bad anim id {anim!r}')
        seen.add(anim)
        if not isinstance(name, str) or not name or any(c.isspace() for c in name):
            raise BombSaraiStageError(f'bad clip name {name!r}')
        if type(frames) is not int or not 1 <= frames <= MAX_FRAMES:
            raise BombSaraiStageError(f'bad frame count for {name}')
        if len(events) > MAX_EVENTS or len(poses) > MAX_POSES:
            raise BombSaraiStageError(f'too many events/poses for {name}')
        parts = ['clip', str(anim), name, str(frames), str(len(events))]
        previous = -1
        for frame, kind in events:
            if (type(frame) is not int or type(kind) is not int or not 0 <= frame < frames
                    or frame < previous or not 0 <= kind <= 2000):
                raise BombSaraiStageError(f'bad key event for {name}')
            previous = frame
            parts += [str(frame), str(kind)]
        parts.append(str(len(poses)))
        last = -1
        for frame, number, kamu in poses:
            if (type(frame) is not int or not 0 <= frame < frames or frame <= last
                    or type(number) is not int or not 0 <= number <= MAX_FILE
                    or len(kamu) != 3
                    or any(not math.isfinite(v) or abs(v) > MAX_KAMU for v in kamu)):
                raise BombSaraiStageError(f'bad pose row for {name}')
            last = frame
            parts += [str(frame), str(number)] + [_fmt(v) for v in kamu]
        rows.append(' '.join(parts))
    for bomb in bombs:
        name, frames, poses = bomb['name'], bomb['frames'], list(bomb['poses'])
        if name not in BOMB_CLIPS or type(frames) is not int or not 1 <= frames <= MAX_FRAMES \
                or len(poses) > MAX_POSES:
            raise BombSaraiStageError(f'bad bomb clip {name!r}')
        parts = ['bomb', name, str(frames), str(len(poses))]
        for frame, number in poses:
            if type(frame) is not int or not 0 <= frame < frames or type(number) is not int \
                    or not 0 <= number <= MAX_FILE:
                raise BombSaraiStageError(f'bad bomb pose for {name}')
            parts += [str(frame), str(number)]
        rows.append(' '.join(parts))
    rows.append('END')
    return ('\n'.join(rows) + '\n').encode('ascii')


def parse_bank(data):
    """Reproduce native ``p2bsown::parseBank`` (fails closed identically)."""
    tokens = (data.decode('ascii') if isinstance(data, bytes) else data).split()
    pos = 0

    def take():
        nonlocal pos
        if pos >= len(tokens):
            raise BombSaraiStageError('truncated bank')
        pos += 1
        return tokens[pos - 1]

    def take_int():
        word = take()
        try:
            return int(word)
        except ValueError as error:
            raise BombSaraiStageError(f'bad integer {word!r}') from error

    def take_float():
        word = take()
        try:
            value = float(word)
        except ValueError as error:
            raise BombSaraiStageError(f'bad number {word!r}') from error
        if not math.isfinite(value) or abs(value) > MAX_KAMU:
            raise BombSaraiStageError('bad kamu value')
        return value

    if take() != BANK_HEADER:
        raise BombSaraiStageError('bad bank header')
    count = take_int()
    if not 1 <= count <= len(CLIPS):
        raise BombSaraiStageError('bad bank header')
    clips, bombs = {}, []
    for _ in range(count):
        if take() != 'clip':
            raise BombSaraiStageError('bad clip row')
        anim, name, frames, events = take_int(), take(), take_int(), take_int()
        if not 0 <= anim < len(CLIPS) or anim in clips or not 1 <= frames <= MAX_FRAMES \
                or not 0 <= events <= MAX_EVENTS:
            raise BombSaraiStageError('bad clip row')
        rows, previous = [], -1
        for _ in range(events):
            frame, kind = take_int(), take_int()
            if not 0 <= frame < frames or frame < previous or not 0 <= kind <= 2000:
                raise BombSaraiStageError('bad key event')
            previous = frame
            rows.append((frame, kind))
        count_poses = take_int()
        if not 0 <= count_poses <= MAX_POSES:
            raise BombSaraiStageError('bad pose count')
        poses, last = [], -1
        for _ in range(count_poses):
            frame, number = take_int(), take_int()
            kamu = (take_float(), take_float(), take_float())
            if not 0 <= frame < frames or frame <= last or not 0 <= number <= MAX_FILE:
                raise BombSaraiStageError('bad pose row')
            last = frame
            poses.append((frame, number, kamu))
        clips[anim] = dict(name=name, frames=frames, events=rows, poses=poses)
    while True:
        word = take()
        if word == 'END':
            if pos != len(tokens):
                raise BombSaraiStageError('trailing bank tokens')
            return dict(clips=clips, bombs=bombs)
        if word == 'bomb':
            if len(bombs) >= 2:
                raise BombSaraiStageError('too many bomb clips')
            name, frames, count_poses = take(), take_int(), take_int()
            if not 1 <= frames <= MAX_FRAMES or not 0 <= count_poses <= MAX_POSES:
                raise BombSaraiStageError('bad bomb row')
            poses = []
            for _ in range(count_poses):
                frame, number = take_int(), take_int()
                if not 0 <= frame < frames or not 0 <= number <= MAX_FILE:
                    raise BombSaraiStageError('bad bomb pose')
                poses.append((frame, number))
            bombs.append(dict(name=name, frames=frames, poses=poses))
            continue
        raise BombSaraiStageError(f'unexpected token {word}')


# ------------------------------------------------------------------ plan
def _pose_number(filename, species, clip):
    prefix = f'bombsarai_{species}_{clip}_'
    if not filename.startswith(prefix) or not filename.endswith('.mod'):
        raise BombSaraiStageError(f'unexpected pose file {filename!r}')
    return int(filename[len(prefix):-4])


def _kamu_translations(species_dir, clip_name, frames):
    """Model-space kamu_jnt1 translation at each pose frame of one clip."""
    from experimental.pikmin2_convert import blocks
    from experimental.pikmin2_purple import bca_pose
    from experimental.pikmin2_rigid import joint_matrices
    from experimental.pikmin2_sheargrub_assets import joints
    model = (species_dir / 'enemy.bmd').read_bytes()
    names = joints(model)
    if names.count(KAMU_JOINT) != 1:
        raise BombSaraiStageError('expected exactly one kamu_jnt1 joint')
    index = names.index(KAMU_JOINT)
    model_blocks = blocks(model)
    raw = (species_dir / f'{clip_name}.bca').read_bytes()
    out = []
    for frame in frames:
        _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
        matrix = joint_matrices(model_blocks, pose)[index]
        out.append(tuple(float(matrix[r][3]) for r in range(3)))
    return out


def plan(source):
    """Plan from a ``pikmin2_bombsarai_assets`` extraction tree."""
    source = Path(source)
    manifest_path = source / 'bombsarai.json'
    if not manifest_path.is_file():
        raise BombSaraiStageError(f'missing {manifest_path}')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    info = manifest.get('species', {}).get('BombSarai')
    if manifest.get('schema') != 1 or not info or info.get('enemy_id') != 58:
        raise BombSaraiStageError('unexpected BombSarai manifest')
    species_dir = source / 'BombSarai'
    clips = info.get('clips', [])
    if [c.get('name') for c in clips] != list(CLIPS):
        raise BombSaraiStageError(f'unexpected clip order: {[c.get("name") for c in clips]!r}')
    rows = []
    for anim, clip in enumerate(clips):
        name = clip['name']
        raw = (species_dir / f'{name}.bca').read_bytes()
        frames = int(clip.get('source_frames') or 0) or bca_frames(raw)
        poses = [p for p in clip.get('poses', []) if 'file' in p]
        kamus = _kamu_translations(species_dir, name, [int(p['frame']) for p in poses]) if poses else []
        pose_rows = []
        for pose, kamu in zip(poses, kamus):
            data = (species_dir / pose['file']).read_bytes()
            if not data or len(data) > MESH_BYTES or hashlib.sha256(data).hexdigest() != pose['sha256']:
                raise BombSaraiStageError(f'pose mesh mismatch: {pose["file"]}')
            pose_rows.append((int(pose['frame']), _pose_number(pose['file'], 'BombSarai', name), kamu))
        rows.append(dict(anim_id=anim, name=name, frames=frames,
                         events=[(int(f), int(t)) for f, t in clip.get('events', [])], poses=pose_rows))
    bombs, room = [], []
    payload = manifest.get('payload_assets', {})
    bomb_dir = source / 'Bomb'
    for clip in payload.get('clips', []):
        name = clip['name']
        if name not in BOMB_CLIPS:
            continue
        raw = (bomb_dir / f'{name}.bca').read_bytes()
        frames = int(clip.get('source_frames') or 0) or bca_frames(raw)
        poses = []
        for pose in clip.get('poses', []):
            if 'file' not in pose:
                continue
            data = (bomb_dir / pose['file']).read_bytes()
            if not data or len(data) > MESH_BYTES or hashlib.sha256(data).hexdigest() != pose['sha256']:
                raise BombSaraiStageError(f'bomb pose mismatch: {pose["file"]}')
            poses.append((int(pose['frame']), _pose_number(pose['file'], 'Bomb', name)))
            room.append((pose['file'], data))
        bombs.append(dict(name=name, frames=frames, poses=poses))
    parms = {}
    for rel, target in (('BombSarai/enemyparm.txt', PARMS_TXT), ('Bomb/enemyparm.txt', BOMB_PARMS_TXT)):
        path = source / rel
        if not path.is_file():
            raise BombSaraiStageError(f'missing retail parameter file {rel}')
        parms[target] = path.read_bytes()
    return dict(bank=bank_text(rows, bombs), room=room, parms=parms,
                poses=sum(len(r['poses']) for r in rows),
                bomb_poses=sum(len(b['poses']) for b in bombs))


def teki_text(generator):
    if type(generator) is not int or not 0 < generator <= 0xffffffff:
        raise BombSaraiStageError('bad placeholder generator')
    return f'{TEKI_HEADER} 1 {generator} {HOST_TYPE}\n'.encode('ascii')


def _write_new_or_same(path, data):
    if path.exists() or path.is_symlink():
        if not path.is_file() or path.read_bytes() != data:
            raise BombSaraiStageError(f'refusing to replace existing {path.name}')
        return False
    path.write_bytes(data)
    return True


def stage(source, run, generators):
    """Stage the OWN inputs into ``run``; returns a receipt dict."""
    run = Path(run)
    staged = plan(source)
    room = run / ROOM
    if not room.is_dir() or not room.resolve().is_relative_to(run.resolve()):
        raise BombSaraiStageError('BombSarai OWN staging requires the private model room')
    for name, data in sorted(staged['parms'].items()):
        _write_new_or_same(run / name, data)
    _write_new_or_same(run / BANK_TXT, staged['bank'])
    for name, data in staged['room']:
        _write_new_or_same(room / name, data)
    placeholder = sorted(set(int(g) for g in generators))[0]
    teki = teki_text(placeholder)
    _write_new_or_same(run / TEKI_TXT, teki)
    return dict(bank=hashlib.sha256(staged['bank']).hexdigest(), poses=staged['poses'],
                bomb_poses=staged['bomb_poses'], parms=sorted(staged['parms']),
                teki_config_sha256=hashlib.sha256(teki).hexdigest(), placeholder_generator=True,
                host_type=HOST_TYPE)
