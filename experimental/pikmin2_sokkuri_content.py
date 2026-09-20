"""Stage the Sokkuri (Skitter Leaf, source 79) batch-2 ground files into a run.

The native ground path opens three things: ``p2-ground-actors.txt`` plus
``p2-ground-bank.txt`` (parsed by ``engine/pc_port/pc_p2_batch2.cpp:119-167``
``parseActors``/``parseBank`` and consumed per species by
``engine/pc_port/pc_p2_sokkuri.cpp:334-392`` ``pc_p2_sokkuri_setup``) and the
sampled pose meshes
``assets/dataDir/courses/pikmin2room/ginv_Sokkuri_<clip>_%02d.mod`` (opened by
``pc_p2_batch2.cpp:92-117`` ``loadPose``, which aborts the setup on a missing
file rather than skipping). The extractor
(:mod:`experimental.pikmin2_sokkuri_assets`) produces the source art under
``<content>/Sokkuri/`` (``sokkuri.json`` plus the ``ginv_*.mod`` pose meshes);
this module carries that art to where the native loader opens it, deriving the
actors/bank rows in the exact shape the native parsers accept. It never
extracts assets and never commits retail data.

Source layout (extracted ``<content>/Sokkuri/`` tree):

* ``sokkuri.json`` (schema 1, species ``Sokkuri``, enemy_id 79): per-clip
  ``file`` (``<clip>.bca``), ``events`` (``[[frame, kind], ...]``),
  ``source_frames`` (BCA duration), ``sha256`` (raw BCA hash), ``status``
  (``converted``) and ``poses`` (``frame``, ``file``
  (``ginv_Sokkuri_<clip>_%02d.mod``), ``bytes``, ``sha256``).
* The referenced ``ginv_Sokkuri_<clip>_%02d.mod`` pose meshes.

Staged layout (run directory):

* ``p2-ground-actors.txt``: ``P2_GROUND_ACTORS_1`` header, generator count,
  one ``<generator> Sokkuri`` row per seed actor.
* ``p2-ground-bank.txt``: ``P2_GROUND_BANK_1`` header, one
  ``species Sokkuri 79`` row, one
  ``clip Sokkuri <name> <source_frames> <events|-> poses <n> converted`` row
  per converted clip, events encoded ``frame:kind,...`` exactly as
  ``experimental.pikmin2_batch2_core.bank_text`` writes them.
* ``assets/dataDir/courses/pikmin2room/ginv_Sokkuri_<clip>_%02d.mod``: byte
  copies of the sampled pose meshes, hash-bound to the manifest.

Idempotent like the Sarai adapter: all payloads are computed and validated
before any mutation; a second call over the same run is a no-op success when
every staged file is byte-identical, and any conflicting staged file is
refused with ``StagingError`` before anything is written. A missing or
mismatched source file raises ``StagingError`` -- never fabricates a pose or
an event.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_staging import StagingError

SOURCE_ID = 79
SPECIES = 'Sokkuri'
MANIFEST = 'sokkuri.json'
ACTORS_TXT = 'p2-ground-actors.txt'
BANK_TXT = 'p2-ground-bank.txt'
ACTORS_HEADER = 'P2_GROUND_ACTORS_1'
BANK_HEADER = 'P2_GROUND_BANK_1'
ROOM = Path('assets/dataDir/courses/pikmin2room')

_CLIP_RE = re.compile(r'[a-z0-9_]+\.bca')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')
# Native loadPose grammar: assets/dataDir/courses/pikmin2room/
# <prefix>_<Species>_<clip>_%02d.mod with prefix ginv (pc_p2_batch2.cpp:96).
_POSE_RE = re.compile(r'ginv_Sokkuri_([a-z0-9_]+)_([0-9]{2})\.mod')

# Native bank clip-row budget (pc_p2_batch2.cpp:152-155): poses in 0..64.
_MAX_BANK_POSES = 64

# Batch-2 ground anchors for Sokkuri: the installer refuses an import whose
# anchor clips are unavailable (pikmin2_batch2_core.plan), and the native draw
# path falls back across dead/move/wait clips (pc_p2_batch2.cpp:292-329), so a
# staged bank without these three cannot serve the family arena.
# (experimental/pikmin2_batch2_families.py GROUND anchors.)
REQUIRED_CLIPS = ('run1', 'wait1', 'dead1')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _events_token(clip_name, events):
    """Encode one clip's events exactly as bank_text does (``-`` when empty)."""
    if not events:
        return '-'
    return ','.join(f'{frame}:{kind}' for frame, kind in events)


def _check_events(clip_name, duration, events):
    """Mirror the native bank/event grammar so every staged row always parses.

    Covers ``parseEvents`` (``pc_p2_batch2_clock.h:102-136``: ``-`` or
    ``frame:key,...`` with frame in 0..100000) and the per-species consumer
    (``pc_p2_sokkuri.cpp:357-371``: comma/colon split, ``atoi`` both sides),
    plus the loop-pairing rule the Sarai adapter enforces for kinds 0/1.
    """
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise StagingError(f'Sokkuri clip duration out of native range: {clip_name}')
    if not isinstance(events, list) or len(events) > 4096:
        raise StagingError(f'Sokkuri clip event budget exceeded: {clip_name}')
    previous, loop_start = -1, None
    for entry in events:
        if (not isinstance(entry, list) or len(entry) != 2
                or type(entry[0]) is not int or type(entry[1]) is not int):
            raise StagingError(f'Sokkuri clip event malformed: {clip_name}')
        frame, kind = entry
        if frame < previous or frame < 0 or frame >= duration or frame > 100000:
            raise StagingError(f'Sokkuri clip event outside the native clip: {clip_name}')
        if not 0 <= kind < 1000:
            raise StagingError(f'Sokkuri clip event kind outside the native range: {clip_name}')
        if kind == 0:
            loop_start = frame
        if kind == 1 and (loop_start is None or frame <= loop_start):
            raise StagingError(f'Sokkuri clip event loop unmatched: {clip_name}')
        previous = frame


def _load_manifest(source):
    """Read and validate the extracted Sokkuri manifest; fail closed on mismatch."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f'Sokkuri manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'Sokkuri manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'Sokkuri manifest schema mismatch for identity content: {path}')
    if document.get('species') != SPECIES or document.get('enemy_id') != SOURCE_ID:
        raise StagingError(f'Sokkuri manifest identity mismatch for identity content: {path}')
    clips = document.get('clips')
    if not isinstance(clips, list) or not clips:
        raise StagingError(f'Sokkuri manifest carries no clips for identity content: {path}')
    return document, raw


def _clip_poses(document):
    """Return the validated converted clips in manifest order with their poses.

    Returns ``(converted, skipped)``: ``skipped`` names registry clips with no
    converted pose (recorded ``unsupported`` by the extractor, e.g. Sokkuri
    ``type5`` whose sampled frames all fail conversion). Skipping them is not
    fabrication: the bank rows claim exactly the staged meshes, and the native
    draw path falls back across dead/move/wait clips
    (``pc_p2_batch2.cpp:292-329``) rather than requiring every registry clip.
    The ground anchors are always required.
    """
    seen = set()
    converted, skipped = [], []
    for clip in document.get('clips', []):
        name = clip.get('file')
        if not isinstance(name, str) or not _CLIP_RE.fullmatch(name):
            raise StagingError(f'Sokkuri clip name rejected by the native bank grammar: {name!r}')
        if name in seen:
            raise StagingError(f'Sokkuri clip ambiguous for identity content: {name}')
        seen.add(name)
        if clip.get('status') != 'converted':
            skipped.append(name)
            continue
        poses = clip.get('poses')
        if not isinstance(poses, list) or not poses:
            raise StagingError(f'Sokkuri clip carries no poses for identity content: {name}')
        if len(poses) > _MAX_BANK_POSES:
            raise StagingError(f'Sokkuri clip exceeds the native bank budget: {name}')
        stem = name[:-4]
        previous = -1
        for index, pose in enumerate(poses):
            frame = pose.get('frame')
            if type(frame) is not int or frame <= previous or frame > 100000:
                raise StagingError(f'Sokkuri pose frames are not strictly increasing in {name}')
            previous = frame
            filename = pose.get('file')
            match = _POSE_RE.fullmatch(filename) if isinstance(filename, str) else None
            if match is None or match.group(1) != stem or int(match.group(2)) != index:
                raise StagingError(
                    f'Sokkuri pose filename breaks the native loadPose sequence: {filename!r}')
            digest = pose.get('sha256')
            if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
                raise StagingError(f'Sokkuri pose SHA-256 missing for identity content: {filename}')
        _check_events(name, clip.get('source_frames'), clip.get('events', []))
        converted.append(clip)
    present = {Path(clip['file']).stem for clip in converted}
    for required in REQUIRED_CLIPS:
        if required not in present:
            raise StagingError(
                f'Sokkuri ground anchor unavailable for identity content: {required}')
    return converted, skipped


def _actors_payload(actors):
    """Render P2_GROUND_ACTORS_1 from the seed's Sokkuri generator ids."""
    generators = []
    for generator, species in actors:
        if species != SPECIES:
            raise StagingError(f'Sokkuri adapter got non-Sokkuri species: {species!r}')
        if type(generator) is not int or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f'Sokkuri actor generator out of native range: {generator!r}')
        generators.append(generator)
    if not generators:
        raise StagingError('Sokkuri install requires at least one generator')
    if len(set(generators)) != len(generators):
        raise StagingError('Sokkuri actor generators are not unique')
    lines = [ACTORS_HEADER, str(len(generators))]
    lines.extend(f'{generator} {SPECIES}' for generator in generators)
    return ('\n'.join(lines) + '\n').encode('ascii')


def _bank_payload(document):
    """Render P2_GROUND_BANK_1 with the Sokkuri species row plus its clip rows."""
    clips, _skipped = _clip_poses(document)
    lines = [BANK_HEADER, f'species {SPECIES} {SOURCE_ID}']
    for clip in clips:
        name = Path(clip['file']).stem
        poses = clip['poses']
        token = _events_token(clip['file'], clip.get('events', []))
        lines.append(f'clip {SPECIES} {name} {clip["source_frames"]} '
                     f'{token} poses {len(poses)} converted')
    return ('\n'.join(lines) + '\n').encode('ascii')


def _mesh_bytes(source, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(source) / pose['file']
    if not path.is_file():
        raise StagingError(f'Sokkuri pose mesh missing for identity content: {path}')
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f'Sokkuri pose mesh unreadable for identity content: {path}') from error
    if _sha(data) != pose['sha256']:
        raise StagingError(f'Sokkuri pose hash mismatch for identity content: {path}')
    if not data:
        raise StagingError(f'Sokkuri pose mesh empty for identity content: {path}')
    return data


def validate_source(source):
    """Pre-flight check for the Sokkuri content tree without writing anything.

    Mirrors the source-side requirements of ``stage_sokkuri_ground`` so a
    wrong/missing source is rejected before any run destination is prepared;
    the stager re-checks the full contract and remains authoritative. ``actors``
    is not checked here; pass it to :func:`plan` for the full validation.
    """
    source = Path(source)
    document, _raw = _load_manifest(source)
    clips, _skipped = _clip_poses(document)
    for clip in clips:
        for pose in clip['poses']:
            _mesh_bytes(source, pose)
    return True


def plan(source, actors):
    """Validate everything and return exact payloads; never writes.

    Returns ``(actors_payload, bank_payload, mesh_files, manifest_digest,
    skipped_clips)`` where ``mesh_files`` maps room-relative mesh names to
    bytes and ``skipped_clips`` names registry clips with no converted pose.
    """
    source = Path(source)
    actors = list(actors)
    document, raw = _load_manifest(source)
    digest = _sha(raw)
    actors_payload = _actors_payload(actors)
    bank_payload = _bank_payload(document)
    clips, skipped = _clip_poses(document)
    mesh_files = {}
    for clip in clips:
        for pose in clip['poses']:
            data = _mesh_bytes(source, pose)
            if pose['file'] in mesh_files and mesh_files[pose['file']] != data:
                raise StagingError(f'Sokkuri pose mesh name collision: {pose["file"]}')
            mesh_files[pose['file']] = data
    return actors_payload, bank_payload, mesh_files, digest, skipped


def stage_sokkuri_ground(source, run, actors):
    """Stage the batch-2 Sokkuri ground files from an extracted Sokkuri tree.

    ``source`` is the extracted ``<content>/Sokkuri/`` directory
    (``sokkuri.json`` plus the ``ginv_Sokkuri_<clip>_%02d.mod`` pose meshes);
    ``run`` is the run directory whose text-bank slots and
    ``assets/dataDir/courses/pikmin2room/`` room receive the staged files;
    ``actors`` is the seed's ``[(generator_id, 'Sokkuri'), ...]`` bindings.
    Idempotent: a second call over the same run is a no-op success when every
    staged file is byte-identical; a conflicting staged file is refused with
    ``StagingError`` before any write.
    """
    source, run = Path(source), Path(run)
    actors = list(actors)
    if not run.is_dir():
        raise StagingError(f'Sokkuri run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'Sokkuri room directory missing for run staging: {room}')
    actors_payload, bank_payload, mesh_files, digest, skipped = plan(source, actors)
    targets = {ACTORS_TXT: actors_payload, BANK_TXT: bank_payload}
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    conflicts = sorted(name for name, payload in targets.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError('Refusing conflicting Sokkuri ground staging: ' + ', '.join(conflicts))
    if all((run / name).is_file() for name in targets):
        staged = 'existing_identical'
    else:
        for name, payload in targets.items():
            (run / name).write_bytes(payload)
        staged = 'written'
    receipt = dict(species=SPECIES, source_id=SOURCE_ID, staged=staged,
                   manifest_sha256=digest,
                   generators=[int(generator) for generator, _species in actors],
                   skipped_clips=list(skipped),
                   files={name: _sha(payload) for name, payload in targets.items()})
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--actor', action='append', required=True,
                        help='generator:species, e.g. 219079:Sokkuri')
    args = parser.parse_args()
    actors = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(stage_sokkuri_ground(args.source, args.run, actors),
                     sort_keys=True, indent=2))
