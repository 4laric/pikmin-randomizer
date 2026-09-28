"""Stage the native Gatling Groink (78 MiniHoudai / 97 FminiHoudai) OWN inputs (#888 WP5).

The native Groink sidecar (``engine`` ``pc_port/pc_p2_groink_teki.cpp``) drives a
campaign-bound 78/97 with the engine-free source FSM
(``pc_port/pc_p2_groink_fsm.cpp``) and reads, from the run root:

* ``p2-groink-parms.txt``: the verbatim retail ``minihoudai/enemyparm.txt``
  (78 NormMiniHoudai), parsed by ``p2groinkfsm::parseEnemyParm``;
* ``p2-groink-fixed-parms.txt``: the verbatim retail
  ``fminihoudai/enemyparm.txt`` (97 FixMiniHoudai);
* ``p2-groink-bank.txt``: the clip/key-event/pose/muzzle bank parsed by
  ``p2groinkfsm::parseBank`` (grammar reproduced by :func:`parse_bank`);

and the pose meshes ``minihoudai_<clip>_<ii>.mod`` from the private model room
``assets/dataDir/courses/pikmin2room/`` (the draw hook
``pc_p2_groink_teki_draw``). 78 and 97 share the MiniHoudai model, animations
and bank, so the first stager in a session writes the bank and poses and a
later one keeps them (after checking them) and stages only its parameter file.

Nothing here reads a disc: plans are built from extractor output trees
(``experimental.pikmin2_minihoudai_assets`` for 78,
``experimental.pikmin2_cannon_projectile_assets`` for 97).
"""
import hashlib
import json
import math
from pathlib import Path

from experimental.pikmin2_animation import resource_chunks

PARMS_78 = 'p2-groink-parms.txt'
PARMS_97 = 'p2-groink-fixed-parms.txt'
BANK_TXT = 'p2-groink-bank.txt'
BANK_HEADER = 'P2_GROINK_BANK_1'
ROOM = 'assets/dataDir/courses/pikmin2room'

# MiniHoudai AnimID order (MiniHoudai.h:181-191) == the retail
# minihoudai/enemyanimmgr.txt row order (pikmin2_cannon_projectile_assets.CLIPS).
CLIPS = ('walk', 'search1', 'turn1', 'attack1', 'flick1', 'dead1', 'type5', 'rebirth')

# Poses sampled per clip by the MiniHoudai extractor (native bound: <= 24 per
# clip, <= 1 MiB per mesh, <= 24 MiB total). The looping/visible clips get the
# most; type5 is the carcass hold and needs only its two end poses.
POSE_LIMITS = {'walk': 8, 'search1': 4, 'turn1': 4, 'attack1': 10,
               'flick1': 6, 'dead1': 8, 'type5': 2, 'rebirth': 6}

# Native parseBank bounds (pc_p2_groink_fsm.cpp).
MAX_FRAMES = 10000
MAX_EVENTS = 64
MAX_POSES = 24
MAX_MUZZLE = 10000.0
# Native loadShape bounds (pc_p2_groink_teki.cpp) plus a package budget.
MESH_BYTES = 1024 * 1024
TOTAL_BYTES = 12 * 1024 * 1024

# Source defaults (EnemyParmsBase.h fp00; MiniHoudai.h:157-160 fp11/fp12).
DEFAULT_GAUGE = (30.0, 10.0, 100.0)


class GroinkStageError(ValueError):
    pass


def pose_name(clip, number):
    """Native pose filename (pikmin2_minihoudai_assets.pose_name)."""
    return f'minihoudai_{clip}_{number:02}.mod'


# ------------------------------------------------------------------ parms
def parse_enemyparm(raw):
    """Mirror of native ``parseEnemyParm`` block detection.

    Returns ``(general, proper)`` dicts of tag -> float. Blocks end at
    ``{_eof}``; ``#`` comments are dropped; rows are ``{tag} <kind> <value>``.
    The general block holds fp00 and fp14; the proper block is the first
    later block holding fp11/fp12 without fp00. Raises on malformed text.
    """
    try:
        text = raw.decode('shift_jis') if isinstance(raw, bytes) else str(raw)
    except UnicodeDecodeError as error:
        raise GroinkStageError('enemyparm.txt is not shift_jis text') from error
    lines = [line.split('#', 1)[0] for line in text.splitlines()]
    words = ' '.join(lines).split()
    blocks = [{}]
    index = 0
    while index < len(words):
        word = words[index]
        index += 1
        if word == '{_eof}':
            blocks.append({})
            continue
        if len(word) == 6 and word[0] == '{' and word[-1] == '}':
            if index + 1 >= len(words):
                raise GroinkStageError('truncated parameter row')
            value = words[index + 1]
            index += 2
            try:
                number = float(value)
            except ValueError as error:
                raise GroinkStageError(f'bad parameter value {word}') from error
            if not math.isfinite(number):
                raise GroinkStageError(f'bad parameter value {word}')
            tag = word[1:5]
            block = blocks[-1]
            if tag in block and block[tag] != number:
                raise GroinkStageError(f'conflicting duplicate {tag}')
            block[tag] = number
    general = proper = None
    for block in blocks:
        if 'fp00' in block and 'fp14' in block:
            if general is not None:
                raise GroinkStageError('duplicate general block')
            general = block
        elif 's003' in block:
            continue
        elif general is not None and proper is None and 'fp11' in block and 'fp12' in block:
            proper = block
    if general is None:
        raise GroinkStageError('missing general block')
    if not general['fp00'] > 0:
        raise GroinkStageError('nonphysical life')
    return general, proper or {}


def gauge_profile(raw):
    """``(gaugeDelay, recoverySeconds, maxHealth)`` for p2-groink-teki.txt.

    Source-derived: proper fp11 (death -> gauge), proper fp12 (gauge ->
    revival) and general fp00 (life); source defaults fill any missing row.
    Replaces the 2.0/3.0/1200 fixture profile on the campaign path.
    """
    if raw is None:
        return DEFAULT_GAUGE
    general, proper = parse_enemyparm(raw)
    gauge = proper.get('fp11', DEFAULT_GAUGE[0])
    recovery = proper.get('fp12', DEFAULT_GAUGE[1])
    if gauge < 0 or not recovery > 0:
        raise GroinkStageError('nonphysical carcass timeline')
    return (gauge, recovery, general['fp00'])


# ------------------------------------------------------------------ bank
def _fmt(value):
    text = format(float(value), '.9g')
    return text


def bank_text(clips, muzzle=None):
    """Serialise the native ``P2_GROINK_BANK_1`` grammar.

    ``clips`` is a list of dicts ``{anim_id, name, frames, events, poses}``
    (``events`` = ``[(frame, type)]`` in registry order, ``poses`` = the
    staged pose frames). ``muzzle`` is four model-space ``kuti`` columns
    ``[c0, c1, c2, c3]`` or ``None``. Validates every native bound so a
    written bank always parses.
    """
    if not 1 <= len(clips) <= len(CLIPS):
        raise GroinkStageError('bank clip count out of range')
    seen = set()
    rows = [f'{BANK_HEADER} {len(clips)}']
    for clip in clips:
        anim, name, frames = clip['anim_id'], clip['name'], clip['frames']
        events, poses = list(clip['events']), list(clip['poses'])
        if type(anim) is not int or not 0 <= anim < len(CLIPS) or anim in seen:
            raise GroinkStageError(f'bad anim id {anim!r}')
        seen.add(anim)
        if not isinstance(name, str) or not name or any(c.isspace() for c in name):
            raise GroinkStageError(f'bad clip name {name!r}')
        if type(frames) is not int or not 2 <= frames <= MAX_FRAMES:
            raise GroinkStageError(f'bad frame count for {name}')
        if len(events) > MAX_EVENTS or len(poses) > MAX_POSES:
            raise GroinkStageError(f'too many events/poses for {name}')
        previous = -1
        for frame, kind in events:
            if (type(frame) is not int or type(kind) is not int or not 0 <= frame < frames
                    or frame < previous or not 0 <= kind <= 2000):
                raise GroinkStageError(f'bad key event for {name}')
            previous = frame
        for i, frame in enumerate(poses):
            if type(frame) is not int or not 0 <= frame < frames or (i and frame <= poses[i - 1]):
                raise GroinkStageError(f'bad pose frame for {name}')
        parts = ['clip', str(anim), name, str(frames), str(len(events))]
        for frame, kind in events:
            parts += [str(frame), str(kind)]
        parts.append(str(len(poses)))
        parts += [str(frame) for frame in poses]
        rows.append(' '.join(parts))
    if muzzle is not None:
        values = [float(v) for column in muzzle for v in column]
        if len(muzzle) != 4 or any(len(c) != 3 for c in muzzle) \
                or any(not math.isfinite(v) or abs(v) > MAX_MUZZLE for v in values):
            raise GroinkStageError('bad muzzle basis')
        rows.append('muzzle ' + ' '.join(_fmt(v) for v in values))
    rows.append('END')
    return ('\n'.join(rows) + '\n').encode('ascii')


def parse_bank(data):
    """Reproduce native ``p2groinkfsm::parseBank`` (fail closed identically).

    Returns ``{'clips': {anim_id: {name, frames, events, poses}}, 'muzzle': ...}``.
    """
    text = data.decode('ascii') if isinstance(data, bytes) else data
    tokens = text.split()
    pos = 0

    def take():
        nonlocal pos
        if pos >= len(tokens):
            raise GroinkStageError('truncated bank')
        pos += 1
        return tokens[pos - 1]

    def take_int():
        word = take()
        try:
            return int(word)
        except ValueError as error:
            raise GroinkStageError(f'bad integer {word!r}') from error

    if take() != BANK_HEADER:
        raise GroinkStageError('bad bank header')
    count = take_int()
    if not 1 <= count <= len(CLIPS):
        raise GroinkStageError('bad bank header')
    clips = {}
    for _ in range(count):
        if take() != 'clip':
            raise GroinkStageError('bad clip row')
        anim = take_int()
        name = take()
        frames = take_int()
        events = take_int()
        if not 0 <= anim < len(CLIPS) or anim in clips or not 2 <= frames <= MAX_FRAMES \
                or not 0 <= events <= MAX_EVENTS:
            raise GroinkStageError('bad clip row')
        rows = []
        previous = -1
        for _ in range(events):
            frame, kind = take_int(), take_int()
            if not 0 <= frame < frames or frame < previous or not 0 <= kind <= 2000:
                raise GroinkStageError('bad key event')
            previous = frame
            rows.append((frame, kind))
        poses = take_int()
        if not 0 <= poses <= MAX_POSES:
            raise GroinkStageError('bad pose count')
        frames_list = []
        for _ in range(poses):
            frame = take_int()
            if not 0 <= frame < frames or (frames_list and frame <= frames_list[-1]):
                raise GroinkStageError('bad pose frame')
            frames_list.append(frame)
        clips[anim] = dict(name=name, frames=frames, events=rows, poses=frames_list)
    muzzle = None
    while True:
        word = take()
        if word == 'END':
            if pos != len(tokens):
                # Native stops reading at END; trailing bytes are harmless there
                # but the stager never writes any.
                raise GroinkStageError('trailing bank tokens')
            return dict(clips=clips, muzzle=muzzle)
        if word == 'muzzle':
            values = []
            for _ in range(12):
                try:
                    value = float(take())
                except ValueError as error:
                    raise GroinkStageError('bad muzzle') from error
                if not math.isfinite(value) or abs(value) > MAX_MUZZLE:
                    raise GroinkStageError('bad muzzle')
                values.append(value)
            muzzle = [values[0:3], values[3:6], values[6:9], values[9:12]]
            continue
        raise GroinkStageError(f'unexpected token {word}')


def muzzle_columns(joint_matrix):
    """Model-space ``kuti`` 3x4 joint matrix -> native columns c0..c3."""
    if len(joint_matrix) != 3 or any(len(row) != 4 for row in joint_matrix):
        raise GroinkStageError('bad kuti joint matrix')
    return [[float(joint_matrix[r][c]) for r in range(3)] for c in range(4)]


# ------------------------------------------------------------------ plans
def _events(raw_events, name):
    rows = []
    for event in raw_events:
        if len(event) != 2:
            raise GroinkStageError(f'bad event row for {name}')
        rows.append((int(event[0]), int(event[1])))
    return rows


def _check_clip_order(names):
    if list(names) != list(CLIPS):
        raise GroinkStageError(f'unexpected MiniHoudai clip order: {list(names)!r}')


def _pose_payload(source_dir, clip_name, poses, total):
    """Read and verify converted pose meshes; returns (frames, [(dst, bytes)])."""
    frames, files = [], []
    reference = None
    for index, pose in enumerate(poses):
        data = (source_dir / pose['file']).read_bytes()
        if not data or len(data) > MESH_BYTES:
            raise GroinkStageError(f'pose mesh out of budget: {pose["file"]}')
        if pose.get('sha256') and hashlib.sha256(data).hexdigest() != pose['sha256']:
            raise GroinkStageError(f'pose hash mismatch: {pose["file"]}')
        resources = resource_chunks(data)
        if reference is not None and resources != reference:
            raise GroinkStageError(f'pose changes immutable render resources: {pose["file"]}')
        reference = resources
        total[0] += len(data)
        if total[0] > TOTAL_BYTES:
            raise GroinkStageError('Groink pose budget exceeded')
        frames.append(int(pose['frame']))
        files.append((pose_name(clip_name, index), data))
    return frames, files, reference


def plan_minihoudai(source):
    """Plan from a MiniHoudai extractor tree (``minihoudai.json``)."""
    source = Path(source)
    manifest_path = source / 'minihoudai.json'
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or manifest.get('enemy_id') != 78:
        raise GroinkStageError('unexpected MiniHoudai manifest')
    clips = manifest.get('clips', [])
    _check_clip_order(Path(c.get('file', '')).stem for c in clips)
    rows, room = [], []
    total = [0]
    reference = None
    for anim, clip in enumerate(clips):
        name = Path(clip['file']).stem
        poses = [p for p in clip.get('poses', []) if 'file' in p] if clip.get('status') == 'converted' else []
        frames, files, resources = _pose_payload(source, name, poses, total)
        if resources is not None:
            if reference is not None and resources != reference:
                raise GroinkStageError('MiniHoudai clips disagree on render resources')
            reference = resources
        rows.append(dict(anim_id=anim, name=name, frames=int(clip['source_frames']),
                         events=_events(clip.get('events', []), name), poses=frames))
        room += files
    muzzle = manifest.get('muzzle')
    columns = muzzle_columns(muzzle['joint_matrix']) if muzzle else None
    parms = {}
    for filename, target in (('enemyparm.txt', PARMS_78), ('fixed-enemyparm.txt', PARMS_97)):
        path = source / filename
        if path.is_file():
            raw = path.read_bytes()
            parse_enemyparm(raw)  # fail closed before staging
            parms[target] = raw
    return dict(bank=bank_text(rows, columns), room=room, parms=parms,
                variant='MiniHoudai', muzzle=columns is not None)


def plan_fminihoudai(source):
    """Plan from the cannon extractor tree (``cannon_projectile.json``, species FminiHoudai)."""
    source = Path(source)
    manifest_path = source / 'cannon_projectile.json'
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    info = manifest.get('species', {}).get('FminiHoudai')
    if manifest.get('schema') != 1 or not info:
        raise GroinkStageError('cannon manifest has no FminiHoudai bank')
    clips = info.get('clips', [])
    _check_clip_order(c.get('name') for c in clips)
    species_dir = source / 'FminiHoudai'
    rows, room = [], []
    total = [0]
    for anim, clip in enumerate(clips):
        name = clip['name']
        poses = [p for p in clip.get('poses', []) if 'file' in p] if clip.get('status') == 'converted' else []
        frames, files, _ = _pose_payload(species_dir, name, poses, total)
        rows.append(dict(anim_id=anim, name=name, frames=int(clip['source_frames']),
                         events=_events(clip.get('events', []), name), poses=frames))
        room += files
    muzzle = info.get('muzzle')
    columns = muzzle_columns(muzzle['joint_matrix']) if muzzle else None
    parms = {}
    path = species_dir / 'enemyparm.txt'
    if path.is_file():
        raw = path.read_bytes()
        parse_enemyparm(raw)
        parms[PARMS_97] = raw
    return dict(bank=bank_text(rows, columns), room=room, parms=parms,
                variant='FminiHoudai', muzzle=columns is not None)


# ------------------------------------------------------------------ stage
def _write_new_or_same(path, data):
    if path.exists() or path.is_symlink():
        if not path.is_file() or path.read_bytes() != data:
            raise GroinkStageError(f'refusing to replace existing {path.name}')
        return False
    path.write_bytes(data)
    return True


def _existing_bank_ok(run, room):
    try:
        parsed = parse_bank((run / BANK_TXT).read_bytes())
    except (OSError, UnicodeDecodeError, GroinkStageError):
        return False
    for clip in parsed['clips'].values():
        for index in range(len(clip['poses'])):
            if room is None or not (room / pose_name(clip['name'], index)).is_file():
                return False
    return True


def stage(run, plan):
    """Write a plan into ``run``. Returns a receipt dict.

    Parameter files are written or must already be byte-identical. The shared
    bank + poses are written by the first stager; a later stager keeps an
    existing valid bank whose poses are present (78/97 share one model). The
    pose meshes need the private model room; without it the bank is written
    with zero poses so the native draw falls back to the host model.
    """
    run = Path(run)
    room = run / ROOM
    private = room.is_dir() and room.resolve().is_relative_to(run.resolve())
    receipt = dict(variant=plan['variant'], parms=sorted(plan['parms']), bank='kept',
                   poses=0, pose_bytes=0, muzzle=plan['muzzle'])
    for name, data in sorted(plan['parms'].items()):
        _write_new_or_same(run / name, data)
    bank_path = run / BANK_TXT
    if bank_path.exists():
        if not _existing_bank_ok(run, room if private else None):
            raise GroinkStageError(f'existing {BANK_TXT} is malformed or missing poses')
        return receipt
    bank = plan['bank']
    if private and plan['room']:
        for name, data in plan['room']:
            if (room / name).exists():
                raise GroinkStageError(f'refusing existing Groink pose {name}')
        for name, data in plan['room']:
            (room / name).write_bytes(data)
        receipt['poses'] = len(plan['room'])
        receipt['pose_bytes'] = sum(len(d) for _, d in plan['room'])
    else:
        parsed = parse_bank(bank)
        rows = [dict(anim_id=a, name=c['name'], frames=c['frames'], events=c['events'], poses=[])
                for a, c in sorted(parsed['clips'].items())]
        bank = bank_text(rows, parsed['muzzle'])
        receipt['poses_skipped'] = 'no private model room'
    bank_path.write_bytes(bank)
    receipt['bank'] = hashlib.sha256(bank).hexdigest()
    return receipt


def stage_from(source, run):
    """Plan from whichever extractor tree ``source`` holds, then stage."""
    plan = plan_minihoudai(source) or plan_fminihoudai(source)
    if plan is None:
        return None
    return stage(run, plan)
