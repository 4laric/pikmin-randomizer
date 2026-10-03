"""Stage the TamagoMushi (Mitite, source 68) batch-2 ground files into a run.

The native TamagoMushi path opens ``p2-ground-actors.txt`` plus
``p2-ground-bank.txt`` (filtered to the ``TamagoMushi`` rows by
``engine/pc_port/pc_p2_tamago.cpp:378-421`` ``pc_p2_tamago_setup``) and the
sampled pose meshes ``assets/dataDir/courses/pikmin2room/ginv_TamagoMushi_<clip>_\
%02d.mod`` (opened by ``engine/pc_port/pc_p2_batch2.cpp:95-120`` ``loadPose``
with the ``ginv`` family prefix, which aborts the setup on a missing file
rather than skipping). The extractor
(:mod:`experimental.pikmin2_tamago_assets`) produces the source art under
``<content>/TamagoMushi/`` (``tamagomushi.json`` plus the ``ginv_*.mod`` pose meshes);
this module carries that art to where the native loader opens it, deriving the
actors/bank rows in the exact shape the native parsers accept. It never
extracts assets and never commits retail data.

Source layout (extracted ``<content>/TamagoMushi/`` tree):

* ``tamagomushi.json`` (schema 1, species ``TamagoMushi``, enemy_id 68): per-clip
  ``file`` (``<clip>.bca``), ``events`` (``[[frame, kind], ...]``),
  ``source_frames`` (BCA duration), ``sha256`` (raw BCA hash), ``status``
  (``converted``) and ``poses`` (``frame``, ``file``
  (``ginv_TamagoMushi_<clip>_%02d.mod``), ``bytes``, ``sha256``).
* The referenced ``ginv_TamagoMushi_<clip>_%02d.mod`` pose meshes.

Staged layout (run directory): the shared ``p2-ground-actors.txt`` /
``p2-ground-bank.txt`` pair (merged with other ground-identity species' rows
through :mod:`experimental.pikmin2_ground_species_content`, so one seed can
bind TamagoMushi, TamagoMushi and Sokkuri together) plus the room meshes.

Idempotent like the Sokkuri adapter: all payloads are computed and validated
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

from experimental import pikmin2_ground_species_content as ground
from experimental.pikmin2_animation import frames_trailer
from experimental.pikmin2_staging import StagingError

SOURCE_ID = 68
SPECIES = 'TamagoMushi'
MANIFEST = 'tamagomushi.json'
ROOM = Path('assets/dataDir/courses/pikmin2room')

_CLIP_RE = re.compile(r'[a-z0-9_]+\.bca')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')
# Native loadPose grammar: assets/dataDir/courses/pikmin2room/
# <prefix>_<Species>_<clip>_%02d.mod with prefix ginv (pc_p2_batch2.cpp:96).
_POSE_RE = re.compile(r'ginv_TamagoMushi_([a-z0-9_]+)_([0-9]{2})\.mod')

# Batch-2 ground anchors for TamagoMushi: the family contract refuses an import
# whose anchor clips are unavailable
# (experimental/pikmin2_batch2_families.py GROUND anchors), and the native
# setup enters TAMAGO_APPEAR on "set" (pc_p2_tamago.cpp:437) and loops on
# move/wait (pc_p2_tamago.cpp:399), so a staged bank without the locomotion
# anchors cannot serve the family arena.
REQUIRED_CLIPS = ('dead', 'move', 'wait')


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
    (``pc_p2_tamago.cpp:391-407``: comma/colon split, ``atoi`` both sides),
    plus the loop-pairing rule the Sokkuri adapter enforces for kinds 0/1.
    """
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise StagingError(f'TamagoMushi clip duration out of native range: {clip_name}')
    if not isinstance(events, list) or len(events) > 4096:
        raise StagingError(f'TamagoMushi clip event budget exceeded: {clip_name}')
    previous, loop_start = -1, None
    for entry in events:
        if (not isinstance(entry, list) or len(entry) != 2
                or type(entry[0]) is not int or type(entry[1]) is not int):
            raise StagingError(f'TamagoMushi clip event malformed: {clip_name}')
        frame, kind = entry
        if frame < previous or frame < 0 or frame >= duration or frame > 100000:
            raise StagingError(f'TamagoMushi clip event outside the native clip: {clip_name}')
        if not 0 <= kind < 1000:
            raise StagingError(f'TamagoMushi clip event kind outside the native range: {clip_name}')
        if kind == 0:
            loop_start = frame
        if kind == 1 and (loop_start is None or frame <= loop_start):
            raise StagingError(f'TamagoMushi clip event loop unmatched: {clip_name}')
        previous = frame


def _load_manifest(source):
    """Read and validate the extracted TamagoMushi manifest; fail closed on mismatch."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f'TamagoMushi manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'TamagoMushi manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'TamagoMushi manifest schema mismatch for identity content: {path}')
    if document.get('species') != SPECIES or document.get('enemy_id') != SOURCE_ID:
        raise StagingError(f'TamagoMushi manifest identity mismatch for identity content: {path}')
    clips = document.get('clips')
    if not isinstance(clips, list) or not clips:
        raise StagingError(f'TamagoMushi manifest carries no clips for identity content: {path}')
    return document, raw


def _clip_poses(document):
    """Return the validated converted clips in manifest order with their poses."""
    seen = set()
    converted = []
    for clip in document.get('clips', []):
        name = clip.get('file')
        if not isinstance(name, str) or not _CLIP_RE.fullmatch(name):
            raise StagingError(f'TamagoMushi clip name rejected by the native bank grammar: {name!r}')
        if name in seen:
            raise StagingError(f'TamagoMushi clip ambiguous for identity content: {name}')
        seen.add(name)
        if clip.get('status') != 'converted':
            continue
        poses = clip.get('poses')
        if not isinstance(poses, list) or not poses:
            raise StagingError(f'TamagoMushi clip carries no poses for identity content: {name}')
        if len(poses) > ground.MAX_BANK_POSES:
            raise StagingError(f'TamagoMushi clip exceeds the native bank budget: {name}')
        stem = name[:-4]
        previous = -1
        for index, pose in enumerate(poses):
            frame = pose.get('frame')
            if type(frame) is not int or frame <= previous or frame > 100000:
                raise StagingError(f'TamagoMushi pose frames are not strictly increasing in {name}')
            previous = frame
            filename = pose.get('file')
            match = _POSE_RE.fullmatch(filename) if isinstance(filename, str) else None
            if match is None or match.group(1) != stem or int(match.group(2)) != index:
                raise StagingError(
                    f'TamagoMushi pose filename breaks the native loadPose sequence: {filename!r}')
            digest = pose.get('sha256')
            if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
                raise StagingError(f'TamagoMushi pose SHA-256 missing for identity content: {filename}')
        _check_events(name, clip.get('source_frames'), clip.get('events', []))
        converted.append(clip)
    present = {Path(clip['file']).stem for clip in converted}
    for required in REQUIRED_CLIPS:
        if required not in present:
            raise StagingError(
                f'TamagoMushi ground anchor unavailable for identity content: {required}')
    return converted


def _mesh_bytes(source, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(source) / pose['file']
    if not path.is_file():
        raise StagingError(f'TamagoMushi pose mesh missing for identity content: {path}')
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f'TamagoMushi pose mesh unreadable for identity content: {path}') from error
    if _sha(data) != pose['sha256']:
        raise StagingError(f'TamagoMushi pose hash mismatch for identity content: {path}')
    if not data:
        raise StagingError(f'TamagoMushi pose mesh empty for identity content: {path}')
    return data


def validate_source(source):
    """Pre-flight check for the TamagoMushi content tree without writing anything.

    Mirrors the source-side requirements of ``stage_tamago_ground`` so a
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

def _trailer_row(row, poses, source_frames):
    """Append the P2_BANK_FRAMES_1 list when the poses carry valid frames (#895)."""
    trailer = frames_trailer(poses, source_frames)
    return row + (trailer.split()[1],) if trailer else row


def plan(source, actors, *, resource_only=False):
    """Validate everything and return exact payloads; never writes.

    Returns ``(actors_payload, bank_payload, mesh_files, manifest_digest)``
    where the actors/bank payloads are already merged with any staged rows
    other ground-identity species left behind (see
    :mod:`experimental.pikmin2_ground_species_content`), and ``mesh_files``
    maps room-relative mesh names to bytes.
    """
    source = Path(source)
    actors = list(actors)
    pairs = []
    for generator, species in actors:
        if species != SPECIES:
            raise StagingError(f'TamagoMushi adapter got non-TamagoMushi species: {species!r}')
        if type(generator) is not int or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f'TamagoMushi actor generator out of native range: {generator!r}')
        pairs.append(generator)
    if not pairs and not resource_only:
        raise StagingError('TamagoMushi install requires at least one generator')
    if len(set(pairs)) != len(pairs):
        raise StagingError('TamagoMushi actor generators are not unique')
    document, raw = _load_manifest(source)
    digest = _sha(raw)
    clips = _clip_poses(document)
    clip_rows = []
    for clip in clips:
        name = Path(clip['file']).stem
        token = _events_token(clip['file'], clip.get('events', []))
        clip_rows.append(_trailer_row((name, clip['source_frames'], token,
                                       len(clip['poses']), 'converted'),
                                      clip['poses'], clip['source_frames']))
    mesh_files = {}
    for clip in clips:
        for pose in clip['poses']:
            data = _mesh_bytes(source, pose)
            if pose['file'] in mesh_files and mesh_files[pose['file']] != data:
                raise StagingError(f'TamagoMushi pose mesh name collision: {pose["file"]}')
            mesh_files[pose['file']] = data
    return digest, pairs, clip_rows, mesh_files


def stage_tamago_ground(source, run, actors, _existing=None, *, resource_only=False):
    """Stage the batch-2 TamagoMushi ground files from an extracted TamagoMushi tree.

    ``source`` is the extracted ``<content>/TamagoMushi/`` directory
    (``tamagomushi.json`` plus the ``ginv_TamagoMushi_<clip>_%02d.mod`` pose meshes);
    ``run`` is the run directory whose text-bank slots and
    ``assets/dataDir/courses/pikmin2room/`` room receive the staged files;
    ``actors`` is the seed's ``[(generator_id, 'TamagoMushi'), ...]`` bindings.
    Rows merge with other ground-identity species' staged rows (see
    :mod:`experimental.pikmin2_ground_species_content`); idempotent across
    repeat calls, fail-closed on any conflict, all validated before any write.
    """
    source, run = Path(source), Path(run)
    actors = list(actors)
    if not run.is_dir():
        raise StagingError(f'TamagoMushi run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'TamagoMushi room directory missing for run staging: {room}')
    if resource_only and actors:
        raise StagingError('TamagoMushi resource-only staging cannot bind actors')
    digest, generators, clip_rows, mesh_files = plan(source, actors, resource_only=resource_only)
    actors_path, bank_path = run / ground.ACTORS_TXT, run / ground.BANK_TXT
    bank_payload = ground.merge_bank(
        bank_path.read_bytes() if bank_path.is_file() else None,
        SPECIES, SOURCE_ID, clip_rows)
    targets = {ground.BANK_TXT: bank_payload}
    if not resource_only:
        targets[ground.ACTORS_TXT] = ground.merge_actors(
            actors_path.read_bytes() if actors_path.is_file() else None,
            SPECIES, generators)
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    # Sidecar conflicts surface inside the merge above (a restaged own-species
    # block must equal what is already there); only a mesh file that exists
    # with different bytes is a conflict here. Merged sidecars legitimately
    # differ from the staged files when they gain new rows.
    mesh_conflicts = sorted(
        name for name, payload in mesh_files.items()
        if (run / str(ROOM / name)).is_file()
        and (run / str(ROOM / name)).read_bytes() != payload)
    if mesh_conflicts:
        raise StagingError(
            'Refusing conflicting TamagoMushi ground staging: ' + ', '.join(mesh_conflicts))
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


def stage_bigfoot_children(source, run):
    """Stage Mitite resources for BigFoot's death without creating a placement."""
    return stage_tamago_ground(source, run, [], resource_only=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--actor', action='append', required=True,
                        help='generator:species, e.g. 219068:TamagoMushi')
    args = parser.parse_args()
    actors = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(stage_tamago_ground(args.source, args.run, actors),
                     sort_keys=True, indent=2))
