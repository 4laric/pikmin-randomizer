"""Stage the native Breadbug (PanModoki 38) OWN inputs (#898).

The native sidecar (``pc_port/pc_p2_breadbug_teki.cpp``) drives every
campaign-bound source 38 with the engine-free source FSM
(``pc_port/pc_p2_breadbug_fsm.cpp``) and reads, from the run root:

* ``p2-breadbug-parms.txt``: the verbatim retail ``panmodoki/enemyparm.txt``,
  parsed by ``p2breadbugfsm::parseEnemyParm`` (fp00 life, fp06 move speed,
  proper fp06 press damage, fp04 container damage, fp03 carry speed, ...);
* ``p2-breadbug-bank.txt``: the clip/key-event/pose bank parsed by
  ``p2breadbugfsm::parseBank`` (grammar reproduced by :func:`parse_bank`);

and the pose meshes ``breadbug_<clip>_<ii>.mod`` from the private model room
``assets/dataDir/courses/pikmin2room/`` (draw hook ``pc_p2_breadbug_teki_draw``).

Nothing here reads a disc: the plan is built from the extractor tree written
by :mod:`experimental.pikmin2_breadbug_own_assets`. These are exactly the
files the native sidecar opens; anything else in the extractor tree stays out
of the run.
"""
import hashlib
import json
import math
from pathlib import Path

from experimental.pikmin2_animation import resource_chunks

PARMS = 'p2-breadbug-parms.txt'
BANK_TXT = 'p2-breadbug-bank.txt'
BANK_HEADER = 'P2_BREADBUG_BANK_1'
ROOM = 'assets/dataDir/courses/pikmin2room'
MANIFEST = 'breadbug.json'

# PanModokiBase AnimID order (PanModokiBase.h:242-253) == retail row order.
CLIPS = ('dead', 'move1', 'move2', 'type1', 'type2', 'type3', 'type4', 'type5', 'wait1')

# Native parseBank / loadShape bounds (pc_p2_breadbug_fsm.cpp / _teki.cpp).
MAX_FRAMES = 10000
MAX_EVENTS = 64
MAX_POSES = 24
MESH_BYTES = 1024 * 1024
TOTAL_BYTES = 12 * 1024 * 1024


class BreadbugStageError(ValueError):
    pass


def pose_name(clip, number):
    """Native pose filename (pikmin2_breadbug_own_assets.pose_name)."""
    return f'breadbug_{clip}_{number:02}.mod'


# ------------------------------------------------------------------ parms
def parse_enemyparm(raw):
    """Mirror of native ``p2breadbugfsm::parseEnemyParm`` block detection.

    Returns ``(general, proper)`` tag -> float dicts. The general block holds
    fp00 and fp27; the proper block is the later block holding fp16 and ip01
    (it also carries its own fp00 nest scale and fp14 wait time, which is why
    the Groink fp00+fp14 rule cannot be reused). Raises on malformed text.
    """
    try:
        text = raw.decode('shift_jis') if isinstance(raw, bytes) else str(raw)
    except UnicodeDecodeError as error:
        raise BreadbugStageError('enemyparm.txt is not shift_jis text') from error
    words = ' '.join(line.split('#', 1)[0] for line in text.splitlines()).split()
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
                raise BreadbugStageError('truncated parameter row')
            value = words[index + 1]
            index += 2
            try:
                number = float(value)
            except ValueError as error:
                raise BreadbugStageError(f'bad parameter value {word}') from error
            if not math.isfinite(number):
                raise BreadbugStageError(f'bad parameter value {word}')
            tag = word[1:5]
            block = blocks[-1]
            if tag in block and block[tag] != number:
                raise BreadbugStageError(f'conflicting duplicate {tag}')
            block[tag] = number
    general = proper = None
    for block in blocks:
        if 'fp00' in block and 'fp27' in block:
            if general is not None:
                raise BreadbugStageError('duplicate general block')
            general = block
        elif 's003' in block:
            continue
        elif general is not None and proper is None and 'fp16' in block and 'ip01' in block:
            proper = block
    if general is None:
        raise BreadbugStageError('missing general block')
    if not general['fp00'] > 0:
        raise BreadbugStageError('nonphysical life')
    return general, proper or {}


# ------------------------------------------------------------------ bank
def bank_text(clips):
    """Serialise the native ``P2_BREADBUG_BANK_1`` grammar (validated)."""
    if not 1 <= len(clips) <= len(CLIPS):
        raise BreadbugStageError('bank clip count out of range')
    seen = set()
    rows = [f'{BANK_HEADER} {len(clips)}']
    for clip in clips:
        anim, name, frames = clip['anim_id'], clip['name'], clip['frames']
        events, poses = list(clip['events']), list(clip['poses'])
        if type(anim) is not int or not 0 <= anim < len(CLIPS) or anim in seen:
            raise BreadbugStageError(f'bad anim id {anim!r}')
        seen.add(anim)
        if not isinstance(name, str) or not name or any(c.isspace() for c in name):
            raise BreadbugStageError(f'bad clip name {name!r}')
        if type(frames) is not int or not 2 <= frames <= MAX_FRAMES:
            raise BreadbugStageError(f'bad frame count for {name}')
        if len(events) > MAX_EVENTS or len(poses) > MAX_POSES:
            raise BreadbugStageError(f'too many events/poses for {name}')
        previous = -1
        for frame, kind in events:
            if (type(frame) is not int or type(kind) is not int or not 0 <= frame < frames
                    or frame < previous or not 0 <= kind <= 2000):
                raise BreadbugStageError(f'bad key event for {name}')
            previous = frame
        for i, frame in enumerate(poses):
            if type(frame) is not int or not 0 <= frame < frames or (i and frame <= poses[i - 1]):
                raise BreadbugStageError(f'bad pose frame for {name}')
        parts = ['clip', str(anim), name, str(frames), str(len(events))]
        for frame, kind in events:
            parts += [str(frame), str(kind)]
        parts.append(str(len(poses)))
        parts += [str(frame) for frame in poses]
        rows.append(' '.join(parts))
    rows.append('END')
    return ('\n'.join(rows) + '\n').encode('ascii')


def parse_bank(data):
    """Reproduce native ``p2breadbugfsm::parseBank`` (fail closed identically)."""
    text = data.decode('ascii') if isinstance(data, bytes) else data
    tokens = text.split()
    pos = 0

    def take():
        nonlocal pos
        if pos >= len(tokens):
            raise BreadbugStageError('truncated bank')
        pos += 1
        return tokens[pos - 1]

    def take_int():
        word = take()
        try:
            return int(word)
        except ValueError as error:
            raise BreadbugStageError(f'bad integer {word!r}') from error

    if take() != BANK_HEADER:
        raise BreadbugStageError('bad bank header')
    count = take_int()
    if not 1 <= count <= len(CLIPS):
        raise BreadbugStageError('bad bank header')
    clips = {}
    for _ in range(count):
        if take() != 'clip':
            raise BreadbugStageError('bad clip row')
        anim, name, frames, events = take_int(), take(), take_int(), take_int()
        if not 0 <= anim < len(CLIPS) or anim in clips or not 2 <= frames <= MAX_FRAMES \
                or not 0 <= events <= MAX_EVENTS:
            raise BreadbugStageError('bad clip row')
        rows, previous = [], -1
        for _ in range(events):
            frame, kind = take_int(), take_int()
            if not 0 <= frame < frames or frame < previous or not 0 <= kind <= 2000:
                raise BreadbugStageError('bad key event')
            previous = frame
            rows.append((frame, kind))
        poses = take_int()
        if not 0 <= poses <= MAX_POSES:
            raise BreadbugStageError('bad pose count')
        frames_list = []
        for _ in range(poses):
            frame = take_int()
            if not 0 <= frame < frames or (frames_list and frame <= frames_list[-1]):
                raise BreadbugStageError('bad pose frame')
            frames_list.append(frame)
        clips[anim] = dict(name=name, frames=frames, events=rows, poses=frames_list)
    if take() != 'END' or pos != len(tokens):
        raise BreadbugStageError('missing END or trailing bank tokens')
    return dict(clips=clips)


# ------------------------------------------------------------------ plan
def plan(source):
    """Plan from a ``pikmin2_breadbug_own_assets`` tree (``breadbug.json``)."""
    source = Path(source)
    manifest_path = source / MANIFEST
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or manifest.get('enemy_id') != 38:
        raise BreadbugStageError('unexpected PanModoki manifest')
    clips = manifest.get('clips', [])
    names = [Path(c.get('file', '')).stem for c in clips]
    if names != list(CLIPS):
        raise BreadbugStageError(f'unexpected PanModoki clip order: {names!r}')
    rows, room = [], []
    total = 0
    reference = None
    for anim, clip in enumerate(clips):
        name = names[anim]
        poses = [p for p in clip.get('poses', []) if 'file' in p] if clip.get('status') == 'converted' else []
        frames = []
        for index, pose in enumerate(poses):
            data = (source / pose['file']).read_bytes()
            if not data or len(data) > MESH_BYTES:
                raise BreadbugStageError(f'pose mesh out of budget: {pose["file"]}')
            if pose.get('sha256') and hashlib.sha256(data).hexdigest() != pose['sha256']:
                raise BreadbugStageError(f'pose hash mismatch: {pose["file"]}')
            resources = resource_chunks(data)
            if reference is not None and resources != reference:
                raise BreadbugStageError(f'pose changes immutable render resources: {pose["file"]}')
            reference = resources
            total += len(data)
            if total > TOTAL_BYTES:
                raise BreadbugStageError('Breadbug pose budget exceeded')
            frames.append(int(pose['frame']))
            room.append((pose_name(name, index), data))
        events = [(int(e[0]), int(e[1])) for e in clip.get('events', [])]
        rows.append(dict(anim_id=anim, name=name, frames=int(clip['source_frames']), events=events, poses=frames))
    parm = source / 'enemyparm.txt'
    if not parm.is_file():
        raise BreadbugStageError('PanModoki enemyparm.txt missing from the extractor tree')
    raw = parm.read_bytes()
    parse_enemyparm(raw)  # fail closed before staging
    return dict(bank=bank_text(rows), room=room, parms=raw)


def _write_new_or_same(path, data):
    if path.exists() or path.is_symlink():
        if not path.is_file() or path.read_bytes() != data:
            raise BreadbugStageError(f'refusing to replace existing {path.name}')
        return False
    path.write_bytes(data)
    return True


def stage(run, plan_):
    """Write a plan into ``run``; idempotent for byte-identical inputs."""
    run = Path(run)
    room = run / ROOM
    private = room.is_dir() and room.resolve().is_relative_to(run.resolve())
    if not private:
        raise BreadbugStageError('Breadbug staging needs the private model room')
    _write_new_or_same(run / PARMS, plan_['parms'])
    for name, data in plan_['room']:
        _write_new_or_same(room / name, data)
    _write_new_or_same(run / BANK_TXT, plan_['bank'])
    return dict(parms=PARMS, bank=hashlib.sha256(plan_['bank']).hexdigest(), poses=len(plan_['room']),
                pose_bytes=sum(len(d) for _, d in plan_['room']))


def stage_from(source, run):
    """Plan from the extractor tree ``source`` then stage into ``run``."""
    plan_ = plan(source)
    if plan_ is None:
        raise BreadbugStageError(f'no {MANIFEST} under {source}')
    return stage(run, plan_)
