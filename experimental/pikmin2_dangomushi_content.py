"""Stage the DangoMushi (Segmented Crawbster, source 94) snagret files into a run.

The native DangoMushi path opens ``p2-snagret-actors.txt`` plus
``p2-snagret-bank.txt`` (filtered to the ``DangoMushi`` rows by
``engine/pc_port/pc_p2_dangomushi.cpp:737-806`` ``pc_p2_dangomushi_setup``)
and the sampled pose meshes
``assets/dataDir/courses/pikmin2room/snake_DangoMushi_<clip>_%02d.mod``
(opened by ``engine/pc_port/pc_p2_batch3.cpp`` ``loadPose`` with the
``snake`` family prefix -- ``{"snagret", "snake", ...}`` -- which aborts the
setup on a missing file rather than skipping). The extractor
(:mod:`experimental.pikmin2_dangomushi_assets`) produces the source art under
``<content>/DangoMushi/`` (``dangomushi.json`` plus the ``snake_*.mod`` pose
meshes); this module carries that art to where the native loader opens it,
deriving the actors/bank rows in the exact shape the native parsers accept.
It never extracts assets and never commits retail data.

Source layout (extracted ``<content>/DangoMushi/`` tree):

* ``dangomushi.json`` (schema 1, species ``DangoMushi``, enemy_id 94):
  per-clip ``file`` (``<clip>.bca``), ``events`` (``[[frame, kind], ...]``),
  ``source_frames`` (BCA duration), ``sha256`` (raw BCA hash), ``status``
  (``converted``) and ``poses`` (``frame``, ``file``
  (``snake_DangoMushi_<clip>_%02d.mod``), ``bytes``, ``sha256``).
* The referenced ``snake_DangoMushi_<clip>_%02d.mod`` pose meshes.

Staged layout (run directory):

* ``p2-snagret-actors.txt``: ``P2_SNAGRET_ACTORS_1`` header, generator count,
  one ``<generator> DangoMushi`` row per seed actor (merged with other
  snagret-family rows when present, in canonical
  SnakeCrow/SnakeWhole/DangoMushi order).
* ``p2-snagret-bank.txt``: ``P2_SNAGRET_BANK_1`` header, the
  ``species DangoMushi 94`` row, one
  ``clip DangoMushi <name> <source_frames> <events|-> poses <n> status
  converted`` row per converted clip (the canonical
  ``experimental.pikmin2_dangomushi_behavior.bank_text`` shape, which the
  batch-3 ``parseBank`` accepts with or without the literal ``status``
  keyword), merged with other snagret-family blocks when present.
* ``assets/dataDir/courses/pikmin2room/snake_DangoMushi_<clip>_%02d.mod``:
  byte copies of the sampled pose meshes, hash-bound to the manifest.

Idempotent like the ground-identity adapters: all payloads are computed and
validated before any mutation; a second call over the same run is a no-op
success when every staged file is byte-identical. A restaged own-species
block must equal what is already there, and a mesh file that exists with
different bytes is refused with ``StagingError`` before anything is written.
A missing or mismatched source file raises ``StagingError`` -- never
fabricates a pose or an event.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_animation import frames_trailer
from experimental.pikmin2_staging import StagingError

SOURCE_ID = 94
SPECIES = 'DangoMushi'
MANIFEST = 'dangomushi.json'
ACTORS_TXT = 'p2-snagret-actors.txt'
BANK_TXT = 'p2-snagret-bank.txt'
ACTORS_HEADER = 'P2_SNAGRET_ACTORS_1'
BANK_HEADER = 'P2_SNAGRET_BANK_1'
ROOM = Path('assets/dataDir/courses/pikmin2room')

# Canonical snagret family order (experimental.pikmin2_snagret_assets.SPECIES);
# merged bank blocks follow it so the bytes are independent of staging order.
SNAGRET_SPECIES_ORDER = ('SnakeCrow', 'SnakeWhole', 'DangoMushi')
SNAGRET_SPECIES_IDS = {'SnakeCrow': 34, 'SnakeWhole': 70, 'DangoMushi': 94}

_CLIP_RE = re.compile(r'[a-z0-9_]+\.bca')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')
# Native loadPose grammar: assets/dataDir/courses/pikmin2room/
# <prefix>_<Species>_<clip>_%02d.mod with prefix snake (pc_p2_batch3.cpp).
_POSE_RE = re.compile(r'snake_DangoMushi_([a-z0-9_]+)_([0-9]{2})\.mod')

# Native bank clip-row budget (pc_p2_batch3.cpp parseBank): poses in 0..64.
_MAX_BANK_POSES = 64
# Native actor-row budget (parseActors): 1..100 rows.
_MAX_ACTORS = 100

# Anchors for DangoMushi: the native setup enters DANGO_STAY on "fly"
# (pc_p2_dangomushi.cpp:816), loops on fly/wait/move (:766-769), and the draw
# path falls back across the locomotion clips, so a staged bank without these
# four cannot serve the family arena.
REQUIRED_CLIPS = ('fly', 'wait', 'move', 'dead')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _events_token(clip_name, events):
    """Encode one clip's events exactly as bank_text does (``-`` when empty)."""
    if not events:
        return '-'
    return ','.join(f'{frame}:{kind}' for frame, kind in events)


def _check_events_token(token):
    """Mirror ``parseEvents`` (pc_p2_batch2_clock.h:102-136) for one token."""
    if token == '-':
        return
    for item in token.split(','):
        head, sep, _tail = item.partition(':')
        if not sep or not head or not head.isascii() or not head.isdigit():
            raise StagingError(
                f'DangoMushi bank event token rejected by the native grammar: {token!r}')
        if int(head) > 100000:
            raise StagingError(
                f'DangoMushi bank event frame outside the native range: {token!r}')


def _check_events(clip_name, duration, events):
    """Mirror the native bank/event grammar so every staged row always parses.

    Covers ``parseEvents`` (``pc_p2_batch2_clock.h:102-136``) and the
    per-species consumer (``pc_p2_dangomushi.cpp:770-788``: comma/colon split,
    ``atoi`` both sides, with the roll gate on ``attack`` event 4 and the
    flick gate on ``attack_2`` event 2), plus the loop-pairing rule the
    ground-identity adapters enforce for kinds 0/1.
    """
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise StagingError(f'DangoMushi clip duration out of native range: {clip_name}')
    if not isinstance(events, list) or len(events) > 4096:
        raise StagingError(f'DangoMushi clip event budget exceeded: {clip_name}')
    previous, loop_start = -1, None
    for entry in events:
        if (not isinstance(entry, list) or len(entry) != 2
                or type(entry[0]) is not int or type(entry[1]) is not int):
            raise StagingError(f'DangoMushi clip event malformed: {clip_name}')
        frame, kind = entry
        if frame < previous or frame < 0 or frame >= duration or frame > 100000:
            raise StagingError(f'DangoMushi clip event outside the native clip: {clip_name}')
        if not 0 <= kind < 1000:
            raise StagingError(f'DangoMushi clip event kind outside the native range: {clip_name}')
        if kind == 0:
            loop_start = frame
        if kind == 1 and (loop_start is None or frame <= loop_start):
            raise StagingError(f'DangoMushi clip event loop unmatched: {clip_name}')
        previous = frame


def _parse_actors(data):
    """Parse staged actors bytes; strict mirror of batch-3 ``parseActors``."""
    try:
        text = data.decode('ascii')
    except (UnicodeDecodeError, AttributeError) as error:
        raise StagingError('snagret actors sidecar is not ASCII') from error
    tokens = text.split()
    if len(tokens) < 2 or tokens[0] != ACTORS_HEADER:
        raise StagingError('snagret actors sidecar header mismatch')
    try:
        count = int(tokens[1])
    except ValueError as error:
        raise StagingError('snagret actors sidecar count is not an int') from error
    if count < 1 or count > _MAX_ACTORS or len(tokens) != 2 + 2 * count:
        raise StagingError('snagret actors sidecar row count mismatch')
    rows, seen = [], set()
    for index in range(2, len(tokens), 2):
        try:
            generator = int(tokens[index])
        except ValueError as error:
            raise StagingError('snagret actors sidecar generator is not an int') from error
        species = tokens[index + 1]
        if not 0 < generator <= 0xFFFFFFFF or generator in seen:
            raise StagingError('snagret actors sidecar generator out of native range')
        if species not in SNAGRET_SPECIES_IDS:
            raise StagingError(f'snagret actors sidecar names no snagret species: {species!r}')
        seen.add(generator)
        rows.append((generator, species))
    return rows


def _render_actors(rows):
    lines = [ACTORS_HEADER, str(len(rows))]
    lines.extend(f'{generator} {species}' for generator, species in rows)
    return ('\n'.join(lines) + '\n').encode('ascii')


def _merge_actors(existing, species, generators):
    """Order-preserving generator union; a rebound generator refuses."""
    for generator in generators:
        if type(generator) is not int or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f'snagret actor generator out of native range: {generator!r}')
    if len(set(generators)) != len(generators):
        raise StagingError('snagret actor generators are not unique')
    rows = _parse_actors(existing) if existing is not None else []
    bound = dict(rows)
    for generator in generators:
        if generator in bound and bound[generator] != species:
            raise StagingError(
                f'snagret actor generator {generator} already bound to {bound[generator]!r}')
        if generator not in bound:
            rows.append((generator, species))
    if not rows or len(rows) > _MAX_ACTORS:
        raise StagingError('snagret actors outside the native budget')
    return _render_actors(rows)


def _parse_bank(data):
    """Parse staged bank bytes; strict mirror of batch-3 ``parseBank``.

    Accepts the species rows the native reader accepts (numeric enemy id, or
    the flying install's ``clips <count>`` row) and the clip rows with or
    without the literal ``status`` keyword.
    """
    try:
        text = data.decode('ascii')
    except (UnicodeDecodeError, AttributeError) as error:
        raise StagingError('snagret bank sidecar is not ASCII') from error
    tokens = text.split()
    if not tokens or tokens[0] != BANK_HEADER:
        raise StagingError('snagret bank sidecar header mismatch')
    blocks, current, pos = [], None, 1
    while pos < len(tokens):
        word = tokens[pos]
        if word == 'species':
            if pos + 2 >= len(tokens):
                raise StagingError('snagret bank species row truncated')
            species, identity = tokens[pos + 1], tokens[pos + 2]
            if species not in SNAGRET_SPECIES_IDS:
                raise StagingError(f'snagret bank species row mismatch: {species}')
            extra = 0
            if identity == 'clips':
                if pos + 3 >= len(tokens):
                    raise StagingError('snagret bank species row truncated')
                try:
                    extra = int(tokens[pos + 3])
                except ValueError as error:
                    raise StagingError('snagret bank species row clips not an int') from error
                if extra < 0:
                    raise StagingError('snagret bank species row clips negative')
                pos += 1
            elif identity != str(SNAGRET_SPECIES_IDS[species]):
                raise StagingError(f'snagret bank species row mismatch: {species} {identity}')
            if any(species == name for name, _, _ in blocks):
                raise StagingError(f'snagret bank species block duplicated: {species}')
            blocks.append((species, identity, []))
            current = blocks[-1][2]
            pos += 3
        elif word == 'clip':
            if current is None or pos + 6 >= len(tokens):
                raise StagingError('snagret bank clip row misplaced or truncated')
            _species, name = tokens[pos + 1], tokens[pos + 2]
            try:
                frames, poses = int(tokens[pos + 3]), int(tokens[pos + 6])
            except ValueError as error:
                raise StagingError('snagret bank clip row frames/poses not ints') from error
            events, marker = tokens[pos + 4], tokens[pos + 5]
            if marker != 'poses' or poses < 0 or poses > _MAX_BANK_POSES or frames < 0:
                raise StagingError(f'snagret bank clip row outside the native range: {name!r}')
            _check_events_token(events)
            value = tokens[pos + 7]
            if value == 'status':
                if pos + 8 >= len(tokens):
                    raise StagingError('snagret bank clip row status truncated')
                status, width = tokens[pos + 8], 9
            else:
                status, width = value, 8
            if not name or not status:
                raise StagingError('snagret bank clip row names no clip')
            current.append((name, frames, events, poses, status))
            pos += width
            if pos < len(tokens) and tokens[pos] == 'frames':
                # P2_BANK_FRAMES_1 trailer (#895): carried through verbatim.
                if pos + 1 >= len(tokens) or not _frames_token_ok(tokens[pos + 1]):
                    raise StagingError(f'snagret bank clip row frames trailer malformed: {name!r}')
                current[-1] = current[-1] + (tokens[pos + 1],)
                pos += 2
        else:
            raise StagingError(f'snagret bank token rejected by the native grammar: {word!r}')
    return blocks


def _frames_token_ok(token):
    """``f0,f1,...`` digits/commas only, at most 64 entries (native grammar)."""
    parts = token.split(',')
    return 1 <= len(parts) <= 64 and all(part.isdigit() and len(part) <= 6 for part in parts)


def _render_bank(blocks):
    """Render bank blocks in the canonical ``bank_text`` shape."""
    lines = [BANK_HEADER]
    for species, _identity, clips in blocks:
        lines.append(f'species {species} {SNAGRET_SPECIES_IDS[species]}')
        for row in clips:
            name, frames, events, poses, status = row[:5]
            trailer = f' frames {row[5]}' if len(row) > 5 else ''
            lines.append(f'clip {species} {name} {frames} {events} poses {poses} status {status}{trailer}')
    return ('\n'.join(lines) + '\n').encode('ascii')


def _merge_bank(existing, species, source_id, clip_rows):
    """Merge one species' bank block; a differing restaged block refuses."""
    if species not in SNAGRET_SPECIES_IDS or source_id != SNAGRET_SPECIES_IDS[species]:
        raise StagingError(f'snagret bank species identity mismatch: {species} {source_id}')
    for row in clip_rows:
        _name, frames, events, poses, status = row[:5]
        if len(row) > 6 or (len(row) == 6 and not _frames_token_ok(row[5])):
            raise StagingError(f'snagret bank clip frames trailer malformed: {_name!r}')
        if type(frames) is not int or frames < 0:
            raise StagingError(f'snagret bank clip frames outside the native range: {_name!r}')
        if type(poses) is not int or poses < 0 or poses > _MAX_BANK_POSES:
            raise StagingError(f'snagret bank clip poses outside the native range: {_name!r}')
        if not status:
            raise StagingError(f'snagret bank clip row names no status: {_name!r}')
        _check_events_token(events)
    blocks = _parse_bank(existing) if existing is not None else []
    own = (species, str(source_id), list(clip_rows))
    for index, (name, _id, _clips) in enumerate(blocks):
        if name == species:
            # The clip rows must match; the species-row identity token may be
            # the numeric id or the flying install's `clips <count>` variant
            # (both parse, both mean this species). Normalize to the numeric
            # id on write.
            if _clips != list(clip_rows):
                raise StagingError(
                    f'Refusing conflicting snagret bank block for {species}')
            blocks[index] = own
            break
    else:
        blocks.append(own)
    blocks.sort(key=lambda block: SNAGRET_SPECIES_ORDER.index(block[0]))
    return _render_bank(blocks)


def _load_manifest(source):
    """Read and validate the extracted DangoMushi manifest; fail closed on mismatch."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f'DangoMushi manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'DangoMushi manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'DangoMushi manifest schema mismatch for identity content: {path}')
    if document.get('species') != SPECIES or document.get('enemy_id') != SOURCE_ID:
        raise StagingError(f'DangoMushi manifest identity mismatch for identity content: {path}')
    clips = document.get('clips')
    if not isinstance(clips, list) or not clips:
        raise StagingError(f'DangoMushi manifest carries no clips for identity content: {path}')
    return document, raw


def _clip_poses(document):
    """Return the validated converted clips in manifest order with their poses."""
    seen = set()
    converted = []
    for clip in document.get('clips', []):
        name = clip.get('file')
        if not isinstance(name, str) or not _CLIP_RE.fullmatch(name):
            raise StagingError(
                f'DangoMushi clip name rejected by the native bank grammar: {name!r}')
        if name in seen:
            raise StagingError(f'DangoMushi clip ambiguous for identity content: {name}')
        seen.add(name)
        if clip.get('status') != 'converted':
            continue
        poses = clip.get('poses')
        if not isinstance(poses, list) or not poses:
            raise StagingError(f'DangoMushi clip carries no poses for identity content: {name}')
        if len(poses) > _MAX_BANK_POSES:
            raise StagingError(f'DangoMushi clip exceeds the native bank budget: {name}')
        stem = name[:-4]
        previous = -1
        for index, pose in enumerate(poses):
            frame = pose.get('frame')
            if type(frame) is not int or frame <= previous or frame > 100000:
                raise StagingError(f'DangoMushi pose frames are not strictly increasing in {name}')
            previous = frame
            filename = pose.get('file')
            match = _POSE_RE.fullmatch(filename) if isinstance(filename, str) else None
            if match is None or match.group(1) != stem or int(match.group(2)) != index:
                raise StagingError(
                    f'DangoMushi pose filename breaks the native loadPose sequence: {filename!r}')
            digest = pose.get('sha256')
            if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
                raise StagingError(
                    f'DangoMushi pose SHA-256 missing for identity content: {filename}')
        _check_events(name, clip.get('source_frames'), clip.get('events', []))
        converted.append(clip)
    present = {Path(clip['file']).stem for clip in converted}
    for required in REQUIRED_CLIPS:
        if required not in present:
            raise StagingError(
                f'DangoMushi anchor unavailable for identity content: {required}')
    return converted


def _mesh_bytes(source, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(source) / pose['file']
    if not path.is_file():
        raise StagingError(f'DangoMushi pose mesh missing for identity content: {path}')
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f'DangoMushi pose mesh unreadable for identity content: {path}') from error
    if _sha(data) != pose['sha256']:
        raise StagingError(f'DangoMushi pose hash mismatch for identity content: {path}')
    if not data:
        raise StagingError(f'DangoMushi pose mesh empty for identity content: {path}')
    return data


def validate_source(source):
    """Pre-flight check for the DangoMushi content tree without writing anything.

    Mirrors the source-side requirements of ``stage_dangomushi`` so a
    wrong/missing source is rejected before any run destination is prepared;
    the stager re-checks the full contract and remains authoritative. ``actors``
    is not checked here; pass it to :func:`plan` for the full validation.
    """
    source = Path(source)
    document, _raw = _load_manifest(source)
    clips = _clip_poses(document)
    for clip in clips:
        for pose in clip['poses']:
            _mesh_bytes(source, pose)
    return True


def plan(source, actors):
    """Validate everything and return exact payloads; never writes.

    Returns ``(manifest_digest, generators, clip_rows, mesh_files)`` where
    ``clip_rows`` is this species' ``[(name, frames, events, poses, status)]``
    in manifest order and ``mesh_files`` maps room-relative mesh names to
    bytes. Merging with staged snagret-family rows happens in
    :func:`stage_dangomushi`.
    """
    source = Path(source)
    actors = list(actors)
    generators = []
    for generator, species in actors:
        if species != SPECIES:
            raise StagingError(f'DangoMushi adapter got non-DangoMushi species: {species!r}')
        if type(generator) is not int or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f'DangoMushi actor generator out of native range: {generator!r}')
        generators.append(generator)
    if not generators:
        raise StagingError('DangoMushi install requires at least one generator')
    if len(set(generators)) != len(generators):
        raise StagingError('DangoMushi actor generators are not unique')
    document, raw = _load_manifest(source)
    digest = _sha(raw)
    clips = _clip_poses(document)
    clip_rows = []
    for clip in clips:
        name = Path(clip['file']).stem
        token = _events_token(clip['file'], clip.get('events', []))
        row = (name, clip['source_frames'], token, len(clip['poses']), 'converted')
        # P2_BANK_FRAMES_1 trailer (#895) from each pose's true source frame.
        trailer = frames_trailer(clip['poses'], clip['source_frames'])
        clip_rows.append(row + (trailer.split()[1],) if trailer else row)
    mesh_files = {}
    for clip in clips:
        for pose in clip['poses']:
            data = _mesh_bytes(source, pose)
            if pose['file'] in mesh_files and mesh_files[pose['file']] != data:
                raise StagingError(f'DangoMushi pose mesh name collision: {pose["file"]}')
            mesh_files[pose['file']] = data
    return digest, generators, clip_rows, mesh_files


def stage_dangomushi(source, run, actors):
    """Stage the DangoMushi snagret files from an extracted DangoMushi tree.

    ``source`` is the extracted ``<content>/DangoMushi/`` directory
    (``dangomushi.json`` plus the ``snake_DangoMushi_<clip>_%02d.mod`` pose
    meshes); ``run`` is the run directory whose text-bank slots and
    ``assets/dataDir/courses/pikmin2room/`` room receive the staged files;
    ``actors`` is the seed's ``[(generator_id, 'DangoMushi'), ...]`` bindings.
    Rows merge with other snagret-family staged rows; idempotent across repeat
    calls, fail-closed on any conflict, all validated before any write.
    """
    source, run = Path(source), Path(run)
    actors = list(actors)
    if not run.is_dir():
        raise StagingError(f'DangoMushi run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'DangoMushi room directory missing for run staging: {room}')
    digest, generators, clip_rows, mesh_files = plan(source, actors)
    actors_path, bank_path = run / ACTORS_TXT, run / BANK_TXT
    actors_payload = _merge_actors(
        actors_path.read_bytes() if actors_path.is_file() else None,
        SPECIES, generators)
    bank_payload = _merge_bank(
        bank_path.read_bytes() if bank_path.is_file() else None,
        SPECIES, SOURCE_ID, clip_rows)
    targets = {ACTORS_TXT: actors_payload, BANK_TXT: bank_payload}
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    # Sidecar conflicts surface inside the merge above; only a mesh file that
    # exists with different bytes is a conflict here.
    mesh_conflicts = sorted(
        name for name, payload in mesh_files.items()
        if (run / str(ROOM / name)).is_file()
        and (run / str(ROOM / name)).read_bytes() != payload)
    if mesh_conflicts:
        raise StagingError(
            'Refusing conflicting DangoMushi staging: ' + ', '.join(mesh_conflicts))
    if all((run / name).is_file() and (run / name).read_bytes() == payload
           for name, payload in targets.items()):
        staged = 'existing_identical'
    else:
        for name, payload in targets.items():
            if not (run / name).is_file() or (run / name).read_bytes() != payload:
                (run / name).write_bytes(payload)
        staged = 'written'
    receipt = dict(species=SPECIES, source_id=SOURCE_ID, staged=staged,
                   manifest_sha256=digest,
                   generators=[int(generator) for generator, _species in actors],
                   files={name: _sha(payload) for name, payload in targets.items()})
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--actor', action='append', required=True,
                        help='generator:species, e.g. 219094:DangoMushi')
    args = parser.parse_args()
    actors = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(stage_dangomushi(args.source, args.run, actors),
                     sort_keys=True, indent=2))
