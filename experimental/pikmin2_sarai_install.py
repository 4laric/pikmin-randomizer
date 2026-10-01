"""Stage the Sarai (Swooping Snitchbug, source 23) native host files into a run.

The native Sarai host (`buildHost` in `engine/pc_port/pc_p2_sarai_manager.cpp`)
fails closed with `bound=0 reason=host` unless the run directory carries the
eight files it opens: the rest mesh, five sampled-pose banks, the attack mouth
bank and the retail event table. The extractor (`scripts/p2_prepare_content.py`
`extract_sarai`, backed by `experimental/pikmin2_sarai_assets.py`) stages the
source art under `<content>/Sarai/` (`sarai.json` plus `<clip>_<frame>.mod`
sampled pose meshes such as `attack1_0000.mod`); this module carries that art
to where the native loader opens it, deriving each bank in the exact shape the
native parser accepts. It never converts or extracts assets and never commits
retail data.

Source layout (extracted `<content>/Sarai/` tree):

* `sarai.json` (schema 1, species `Sarai`, enemy_id 23): per-clip `file`
  (`<clip>.bca`), `events` (`[[frame, type], ...]`), `source_frames`
  (BCA duration), `sha256` (raw BCA hash), `status` (`converted`) and `poses`
  (`frame`, `file` (`<clip>_<frame:04>.mod`), `sha256`, `mouths` for
  `rkamujnt` / `lkamujnt` with radius 15 and a 3x4 model-space matrix).
* The referenced `<clip>_<frame>.mod` pose meshes (80 files).

Staged layout (run directory):

* `assets/dataDir/courses/pikmin2room/sarai0.mod`: byte copy of the attack1
  frame-0 pose mesh (the host replaces it with `applyPoseFrame(0)` during
  setup; lane-30 precedent stages the identical copy).
* `sarai-wait-poses.txt`, `sarai-move-poses.txt`, `sarai-attack-poses.txt`,
  `sarai-waitact1-poses.txt`, `sarai-waitact2-poses.txt`: `P2_DEMON_POSES_2`
  banks (one row per sampled pose of that clip: frame, mesh basename, 24
  mouth floats), per `engine/pc_port/pc_p2_demon_pose_bank.h:13-41` and
  `engine/pc_port/pc_p2_sarai_host.cpp:182-204`.
* `sarai-attack-mouths.txt`: `P2_DEMON_MOUTHS_1` bank (one row per attack1
  pose: frame, 24 mouth floats), read by
  `engine/pc_port/pc_p2_sarai_manager.cpp:52-65`.
* `sarai-retail-events.txt`: `P2_RETAIL_EVENTS_1` table (every clip from
  `sarai.json`: name, duration, attribute, BCA hash, events), read by
  `engine/pc_port/pc_p2_sarai_manager.cpp:80-96` via
  `engine/pc_port/pc_p2_motion_events.h:25-52`.

The derivations that must round-trip are implemented exactly, never guessed: the bank digest is sha256 of the source
`sarai.json` bytes, floats are formatted `%.17g` (both verified byte-exact
against the lane-30 staged reference); the events rows reuse the manifest
duration/sha/events verbatim. Two documented constants carry no pose or event
content: the BCA attribute (2 for every Sarai clip on GPVE01 rev 0, verified
against the retail disc) and the table registry tag (a content-derived
sha256, since the raw `enemyanimmgr.txt` hash is not staged by
`p2_prepare_content.py`; see `evidence.md` for the extractor change that
would restore raw-registry parity).

Idempotent like the existing adapters: all payloads are computed and
validated before any mutation; a second call over the same run is a no-op
success when every staged file is byte-identical, and any conflicting staged
file is refused with `StagingError` before anything is written. A missing or
mismatched source file raises `StagingError` -- never fabricates a pose or
an event.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from experimental.pikmin2_staging import StagingError

SOURCE_ID = 23
SPECIES = 'Sarai'
MANIFEST = 'sarai.json'
MOUTH_JOINTS = ('rkamujnt', 'lkamujnt')
MOUTH_RADIUS = 15

# Clip registry name -> staged pose-bank filename (subset of sarai.json clips).
POSE_BANKS = (
    ('wait1.bca', 'sarai-wait-poses.txt'),
    ('move1.bca', 'sarai-move-poses.txt'),
    ('attack1.bca', 'sarai-attack-poses.txt'),
    ('waitact1.bca', 'sarai-waitact1-poses.txt'),
    ('waitact2.bca', 'sarai-waitact2-poses.txt'),
)
MOUTH_CLIP = 'attack1.bca'
MOUTH_TXT = 'sarai-attack-mouths.txt'
EVENTS_TXT = 'sarai-retail-events.txt'
REST_MOD = 'sarai0.mod'
ROOM = Path('assets/dataDir/courses/pikmin2room')

POSES_MAGIC = 'P2_DEMON_POSES_2'
MOUTHS_MAGIC = 'P2_DEMON_MOUTHS_1'
EVENTS_MAGIC = 'P2_RETAIL_EVENTS_1'
# BCA header attribute byte (offset 40) read by experimental/pikmin2_motion_events
# `encode`; uniform across all twelve Sarai clips on GPVE01 rev 0 (verified
# against the retail disc, not recorded in sarai.json).
RETAIL_ATTRIBUTE = 2

_CLIP_RE = re.compile(r'[a-z0-9_]+\.bca')
_MODEL_RE = re.compile(r'[A-Za-z0-9_]+\.mod')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _fmt(value):
    """Format one mouth matrix component exactly as the staged banks encode it."""
    if type(value) not in (int, float):
        raise StagingError(f'Sarai mouth value is not numeric: {value!r}')
    number = float(value)
    if not math.isfinite(number) or abs(number) > 1.0e6:
        raise StagingError(f'Sarai mouth value out of native range: {value!r}')
    return format(number, '.17g')


def _mouth_values(pose, clip_name):
    """Flatten one pose's two mouth matrices to 24 native-ordered floats."""
    mouths = pose.get('mouths')
    if not isinstance(mouths, list) or len(mouths) != 2:
        raise StagingError(f'Sarai pose of {clip_name} lacks two mouths: {pose.get("file")}')
    values = []
    for mouth, joint in zip(mouths, MOUTH_JOINTS):
        if mouth.get('joint') != joint:
            raise StagingError(f'Sarai mouth joint mismatch in {clip_name}: {mouth.get("joint")!r}')
        if mouth.get('radius') != MOUTH_RADIUS:
            raise StagingError(f'Sarai mouth radius mismatch in {clip_name}: {mouth.get("radius")!r}')
        matrix = mouth.get('matrix')
        if not isinstance(matrix, list) or len(matrix) != 3 or any(
                not isinstance(row, list) or len(row) != 4 for row in matrix):
            raise StagingError(f'Sarai mouth matrix is not 3x4 in {clip_name}: {pose.get("file")}')
        for row in matrix:
            values.extend(_fmt(value) for value in row)
    if len(values) != 24:
        raise StagingError(f'Sarai mouth values are not 24 in {clip_name}: {pose.get("file")}')
    return values


def _load_manifest(source):
    """Read and validate the extracted Sarai manifest; fail closed on mismatch."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f'Sarai manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'Sarai manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'Sarai manifest schema mismatch for identity content: {path}')
    if document.get('species') != SPECIES or document.get('enemy_id') != SOURCE_ID:
        raise StagingError(f'Sarai manifest identity mismatch for identity content: {path}')
    clips = document.get('clips')
    if not isinstance(clips, list) or not clips:
        raise StagingError(f'Sarai manifest carries no clips for identity content: {path}')
    return document, raw


def _clip_poses(document, clip_name):
    """Return the validated converted poses for one clip registry name."""
    match = [clip for clip in document.get('clips', []) if clip.get('file') == clip_name]
    if len(match) != 1:
        raise StagingError(f'Sarai clip missing or ambiguous for identity content: {clip_name}')
    clip = match[0]
    if clip.get('status') != 'converted':
        raise StagingError(f'Sarai clip unavailable for identity content: {clip_name}')
    poses = clip.get('poses')
    if not isinstance(poses, list) or not poses:
        raise StagingError(f'Sarai clip carries no poses for identity content: {clip_name}')
    if len(poses) > 128:
        raise StagingError(f'Sarai clip exceeds the native bank budget: {clip_name}')
    previous = -1
    for pose in poses:
        frame = pose.get('frame')
        if type(frame) is not int or frame <= previous or frame > 100000:
            raise StagingError(f'Sarai pose frames are not strictly increasing in {clip_name}')
        previous = frame
        name = pose.get('file')
        if not isinstance(name, str) or not _MODEL_RE.fullmatch(name) or not 5 <= len(name) <= 96:
            raise StagingError(f'Sarai pose filename rejected by the native bank grammar: {name!r}')
        digest = pose.get('sha256')
        if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
            raise StagingError(f'Sarai pose SHA-256 missing for identity content: {name}')
        _mouth_values(pose, clip_name)
    return poses


def _bank_text(magic, digest, rows):
    """Render one P2_DEMON_* bank: header plus `<frame> [<model>] <24 floats>`."""
    lines = [magic, digest, str(len(rows))]
    lines.extend(' '.join(str(token) for token in row) for row in rows)
    return ('\n'.join(lines) + '\n').encode('ascii')


def _pose_bank_payload(document, digest, clip_name):
    poses = _clip_poses(document, clip_name)
    return _bank_text(POSES_MAGIC, digest,
                      [(pose['frame'], pose['file'],
                        *_mouth_values(pose, clip_name)) for pose in poses])


def _mouth_bank_payload(document, digest):
    poses = _clip_poses(document, MOUTH_CLIP)
    return _bank_text(MOUTHS_MAGIC, digest,
                      [(pose['frame'], *_mouth_values(pose, MOUTH_CLIP)) for pose in poses])


def _check_events(clip_name, duration, events):
    """Mirror the native retail-event grammar so the staged table always parses."""
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise StagingError(f'Sarai clip duration out of native range: {clip_name}')
    if not isinstance(events, list) or len(events) > 4096:
        raise StagingError(f'Sarai clip event budget exceeded: {clip_name}')
    previous, loop_start = -1, None
    for entry in events:
        if (not isinstance(entry, list) or len(entry) != 2
                or type(entry[0]) is not int or type(entry[1]) is not int):
            raise StagingError(f'Sarai clip event malformed: {clip_name}')
        frame, kind = entry
        if frame < previous or frame < 0 or frame >= duration or not 0 <= kind < 1000:
            raise StagingError(f'Sarai clip event outside the native clip: {clip_name}')
        if kind == 0:
            loop_start = frame
        if kind == 1 and (loop_start is None or frame <= loop_start):
            raise StagingError(f'Sarai clip event loop unmatched: {clip_name}')
        previous = frame


def _events_payload(document):
    """Render the P2_RETAIL_EVENTS_1 table from every manifest clip, order kept."""
    bodies = []
    for clip in document.get('clips', []):
        name = clip.get('file')
        if not isinstance(name, str) or not _CLIP_RE.fullmatch(name):
            raise StagingError(f'Sarai clip name rejected by the native event grammar: {name!r}')
        duration = clip.get('source_frames')
        events = clip.get('events', [])
        _check_events(name, duration, events)
        digest = clip.get('sha256')
        if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
            raise StagingError(f'Sarai clip BCA SHA-256 missing for identity content: {name}')
        bodies.append(f'{name} {duration} {RETAIL_ATTRIBUTE} {digest} {len(events)}')
        bodies.extend(f'{frame} {kind}' for frame, kind in events)
    if not 1 <= len(document.get('clips', [])) <= 256:
        raise StagingError('Sarai clip count outside the native event budget')
    # The raw registry hash (sha256 of sarai/enemyanimmgr.txt) is not staged by
    # p2_prepare_content.py; tag the table with the sha256 of its own staged
    # motion body instead (documented in evidence.md). The native reader only
    # requires 64 hex here, and every motion row stays source-verbatim.
    registry = _sha(('\n'.join(bodies) + '\n').encode('ascii'))
    header = f'{EVENTS_MAGIC} {registry} {len(document["clips"])}'
    return ('\n'.join([header] + bodies) + '\n').encode('ascii'), registry


def _mesh_bytes(source, clip_name, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(source) / pose['file']
    if not path.is_file():
        raise StagingError(f'Sarai pose mesh missing for identity content: {path}')
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f'Sarai pose mesh unreadable for identity content: {path}') from error
    if _sha(data) != pose['sha256']:
        raise StagingError(f'Sarai pose hash mismatch for identity content: {path}')
    if not data:
        raise StagingError(f'Sarai pose mesh empty for identity content: {path}')
    return data


def plan(source):
    """Validate everything and return exact payloads; never writes.

    Returns ``(text_files, mesh_files, manifest_digest)`` where ``text_files``
    maps run-relative names to bytes and ``mesh_files`` maps room-relative
    mesh names to bytes.
    """
    source = Path(source)
    document, raw = _load_manifest(source)
    digest = _sha(raw)
    text_files = {}
    for clip_name, bank_name in POSE_BANKS:
        text_files[bank_name] = _pose_bank_payload(document, digest, clip_name)
    text_files[MOUTH_TXT] = _mouth_bank_payload(document, digest)
    text_files[EVENTS_TXT], _registry = _events_payload(document)
    mesh_files = {}
    for clip_name, _bank_name in POSE_BANKS:
        for pose in _clip_poses(document, clip_name):
            data = _mesh_bytes(source, clip_name, pose)
            if pose['file'] in mesh_files and mesh_files[pose['file']] != data:
                raise StagingError(f'Sarai pose mesh name collision: {pose["file"]}')
            mesh_files[pose['file']] = data
    rest = _clip_poses(document, MOUTH_CLIP)[0]
    if rest['frame'] != 0:
        raise StagingError(f'Sarai rest pose is not frame 0 for identity content: {MOUTH_CLIP}')
    mesh_files[REST_MOD] = mesh_files[rest['file']]
    return text_files, mesh_files, digest


def stage_sarai_host(source, run):
    """Stage the eight native Sarai host files from an extracted Sarai tree.

    ``source`` is the extracted `<content>/Sarai/` directory (`sarai.json`
    plus the sampled `<clip>_<frame>.mod` pose meshes); ``run`` is the run
    directory whose `assets/dataDir/courses/pikmin2room/` room and text-bank
    slots receive the staged files. Idempotent: a second call over the same
    run is a no-op success when every staged file is byte-identical; a
    conflicting staged file is refused with `StagingError` before any write.
    """
    source, run = Path(source), Path(run)
    if not run.is_dir():
        raise StagingError(f'Sarai run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'Sarai room directory missing for run staging: {room}')
    text_files, mesh_files, digest = plan(source)
    targets = {name: payload for name, payload in text_files.items()}
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    conflicts = sorted(name for name, payload in targets.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError('Refusing conflicting Sarai host staging: ' + ', '.join(conflicts))
    if all((run / name).is_file() for name in targets):
        staged = 'existing_identical'
    else:
        for name, payload in targets.items():
            (run / name).write_bytes(payload)
        staged = 'written'
    receipt = dict(species=SPECIES, source_id=SOURCE_ID, staged=staged,
                   manifest_sha256=digest,
                   files={name: _sha(payload) for name, payload in targets.items()})
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage_sarai_host(args.source, args.run), sort_keys=True, indent=2))
