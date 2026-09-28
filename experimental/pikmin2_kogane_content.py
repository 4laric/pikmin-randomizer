"""Stage the Kogane (Iridescent Flint Beetle, source 9) native host files.

The native Kogane host (`pc_p2_kogane_setup` in
`native/pc_port/pc_p2_kogane.cpp:30-81`) binds nothing unless the run
directory carries every file it opens: `p2-kogane-native.txt` (parsed by
`p2kogane::read` in `native/pc_port/pc_p2_kogane_policy.h:8-17`) plus, for
each of its three clips, the `count` pose meshes
`assets/dataDir/courses/pikmin2room/kogane_<clip>_<ii>.mod`
(`pc_p2_kogane.cpp:48` pre-pass, `:61` `gameflow.loadShape` -- one staged
file satisfies both reads). The existing `_adapt_kogane` adapter already
writes the sidecar; the pose meshes are the missing piece, so this module
stages exactly those, derived from the extraction result.

Source layout (extracted `<content>/Kogane/` tree, as produced by the
proposed `extract_kogane` wiring of
`experimental.pikmin2_kogane_assets.extract`, mirroring `extract_sarai`):

* `beetles.json` (schema 1, family `Kogane`, species `kogane`/`wealthy`/
  `fart` with enemy ids 9/10/11): `shared.clips` entries carry `file`
  (`<clip>.bca`), `source_frames`, `status` (`converted`) and `poses`
  (`frame`, `file` (`<clip>_<ordinal:02>.mod`), `sha256`).
* The referenced `<clip>_<ordinal>.mod` pose meshes, flattened next to the
  manifest (copied from the extractor's `shared/` bank by `extract_kogane`).

Staged layout (run directory):

* `assets/dataDir/courses/pikmin2room/kogane_<clip>_<ii>.mod`: byte copy of
  bank pose ordinal `ii` of sidecar clip `<clip>`, for `ii` in
  `0 .. sidecar count - 1`. The ordinal (not the sampled BCA frame) selects
  the mesh because the native loader indexes `kogane_%s_%02d.mod` by
  position in the sidecar frame list.

The sidecar is an input, never an output: its actor rows (generator ids)
come from the seed, so only the adapter can write it. Staging parses it
with the exact `p2kogane::read` grammar and fails closed when it is
missing, malformed, or names a clip/pose count the bank cannot supply --
never fabricates a pose. Verified against the retail disc (GPVE01):
`extract(..., pose_limit=3)` yields `move.bca`/`wait.bca` (15 frames;
poses 0,7,14) and `damage.bca` (50 frames; poses 0,24,49), so the sidecar
clip names line up with the bank while its placeholder durations
(move 12, damage 30) do not match the bank's `source_frames` (15, 50);
setup never compares them, so staging does not gate on durations either.

Idempotent like the Sarai stager: all payloads are computed and validated
before any mutation; a second call over the same run is a no-op success
when every staged file is byte-identical, and any conflicting staged file
is refused with `StagingError` before anything is written.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_staging import StagingError

SOURCE_ID = 9
FAMILY = 'Kogane'
MANIFEST = 'beetles.json'
NATIVE_TXT = 'p2-kogane-native.txt'
ROOM = Path('assets/dataDir/courses/pikmin2room')
MESH_PREFIX = 'kogane'

# Species registry name -> retail enemy id (pikmin2_kogane_assets.SPECIES).
EXPECTED_SPECIES = {'kogane': 9, 'wealthy': 10, 'fart': 11}

# Clip names accepted by p2kogane::read (pc_p2_kogane_policy.h:13).
NATIVE_CLIPS = ('move', 'wait', 'damage')

_NATIVE_HEADER = 'P2_KOGANE_NATIVE_1'
_MODEL_RE = re.compile(r'[A-Za-z0-9_]+\.mod')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _parse_sidecar(text):
    """Parse `p2-kogane-native.txt` with the exact `p2kogane::read` grammar.

    Returns ``[(clip_name, count, frames), ...]``. Mirrors
    `native/pc_port/pc_p2_kogane_policy.h:8-17` token for token so a sidecar
    accepted here is accepted by native setup (and vice versa).
    """
    tokens = text.split()
    cursor = [0]

    def take():
        if cursor[0] >= len(tokens):
            raise StagingError('Kogane sidecar truncated for identity content')
        token = tokens[cursor[0]]
        cursor[0] += 1
        return token

    def take_int():
        try:
            return int(take())
        except ValueError as error:
            raise StagingError('Kogane sidecar carries a non-integer field') from error

    if take() != _NATIVE_HEADER:
        raise StagingError('Kogane sidecar header mismatch for identity content')
    if take() != 'karada':
        raise StagingError('Kogane sidecar karada tag mismatch for identity content')
    karada = take_int()
    if not 0 <= karada <= 64:
        raise StagingError('Kogane sidecar karada slot out of native range')
    if take() != 'actors':
        raise StagingError('Kogane sidecar actors tag mismatch for identity content')
    actor_count = take_int()
    if not 1 <= actor_count <= 100:
        raise StagingError('Kogane sidecar actor count out of native range')
    seen_ids = set()
    for _ in range(actor_count):
        generator = take_int()
        species = take_int()
        if not 0 < generator <= 0xFFFFFFFF or not 9 <= species <= 11:
            raise StagingError('Kogane sidecar actor row out of native range')
        if generator in seen_ids:
            raise StagingError('Kogane sidecar carries a duplicate generator')
        seen_ids.add(generator)
    seen_clips = set()
    clips = []
    for _ in range(3):
        name = take()
        count = take_int()
        duration = take_int()
        if name not in NATIVE_CLIPS or name in seen_clips:
            raise StagingError(f'Kogane sidecar clip rejected by the native clip set: {name!r}')
        seen_clips.add(name)
        if not 2 <= count <= 24 or not 1 <= duration <= 10000:
            raise StagingError(f'Kogane sidecar clip out of native range: {name}')
        frames = [take_int() for _ in range(count)]
        if (any(frame < 0 or frame >= duration for frame in frames)
                or any(b <= a for a, b in zip(frames, frames[1:]))
                or frames[0] != 0 or frames[-1] != duration - 1):
            raise StagingError(f'Kogane sidecar frames outside the native clip: {name}')
        clips.append((name, count, frames))
    if cursor[0] != len(tokens):
        raise StagingError('Kogane sidecar carries trailing data')
    return clips


def _load_manifest(source):
    """Read and validate the extracted Kogane manifest; fail closed."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f'Kogane manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'Kogane manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'Kogane manifest schema mismatch for identity content: {path}')
    if document.get('family') != FAMILY:
        raise StagingError(f'Kogane manifest identity mismatch for identity content: {path}')
    species = document.get('species', {})
    if (set(species) != set(EXPECTED_SPECIES)
            or any(species[name].get('enemy_id') != enemy_id
                   for name, enemy_id in EXPECTED_SPECIES.items())):
        raise StagingError(f'Kogane manifest species/ID mismatch for identity content: {path}')
    shared = document.get('shared', {})
    if not isinstance(shared.get('clips'), list) or not shared['clips']:
        raise StagingError(f'Kogane manifest carries no clips for identity content: {path}')
    return document, raw


def _bank_clip(document, clip_name):
    """Return the validated converted bank poses for one sidecar clip name."""
    registry = f'{clip_name}.bca'
    match = [clip for clip in document.get('shared', {}).get('clips', [])
             if clip.get('file') == registry]
    if len(match) != 1:
        raise StagingError(f'Kogane clip missing or ambiguous for identity content: {registry}')
    clip = match[0]
    if clip.get('status') != 'converted':
        raise StagingError(f'Kogane clip unavailable for identity content: {registry}')
    poses = clip.get('poses')
    if not isinstance(poses, list) or not poses:
        raise StagingError(f'Kogane clip carries no poses for identity content: {registry}')
    for pose in poses:
        frame = pose.get('frame')
        if type(frame) is not int or frame < 0 or frame > 10000:
            raise StagingError(f'Kogane pose frame out of native range in {registry}')
        name = pose.get('file')
        if not isinstance(name, str) or not _MODEL_RE.fullmatch(name) or not 5 <= len(name) <= 96:
            raise StagingError(f'Kogane pose filename rejected by the native bank grammar: {name!r}')
        digest = pose.get('sha256')
        if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
            raise StagingError(f'Kogane pose SHA-256 missing for identity content: {name}')
    return poses


def _mesh_bytes(source, registry, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(source) / pose['file']
    if not path.is_file():
        raise StagingError(f'Kogane pose mesh missing for identity content: {path}')
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f'Kogane pose mesh unreadable for identity content: {path}') from error
    if _sha(data) != pose['sha256']:
        raise StagingError(f'Kogane pose hash mismatch for identity content: {path}')
    if not data:
        raise StagingError(f'Kogane pose mesh empty for identity content: {path}')
    return data


def plan(source, run):
    """Validate everything and return exact payloads; never writes.

    Returns ``(mesh_files, sidecar_clips, manifest_digest)`` where
    ``mesh_files`` maps room-relative mesh names
    (`kogane_<clip>_<ii>.mod`) to bytes and ``sidecar_clips`` is the parsed
    sidecar ``[(clip_name, count, frames), ...]`` the selection derives from.
    """
    source, run = Path(source), Path(run)
    if not run.is_dir():
        raise StagingError(f'Kogane run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'Kogane room directory missing for run staging: {room}')
    sidecar = run / NATIVE_TXT
    if not sidecar.is_file():
        raise StagingError(f'Kogane native sidecar missing for run staging: {sidecar}')
    try:
        sidecar_text = sidecar.read_text(encoding='ascii')
    except (OSError, ValueError) as error:
        raise StagingError(f'Kogane native sidecar unreadable for run staging: {sidecar}') from error
    clips = _parse_sidecar(sidecar_text)
    document, raw = _load_manifest(source)
    digest = _sha(raw)
    mesh_files = {}
    for clip_name, count, _frames in clips:
        poses = _bank_clip(document, clip_name)
        if len(poses) < count:
            raise StagingError(
                f'Kogane bank poses cannot supply sidecar clip {clip_name}: '
                f'need {count}, have {len(poses)}')
        registry = f'{clip_name}.bca'
        for ordinal in range(count):
            data = _mesh_bytes(source, registry, poses[ordinal])
            name = f'{MESH_PREFIX}_{clip_name}_{ordinal:02d}.mod'
            if name in mesh_files and mesh_files[name] != data:
                raise StagingError(f'Kogane pose mesh name collision: {name}')
            mesh_files[name] = data
    return mesh_files, clips, digest


def stage_kogane_host(source, run):
    """Stage the native Kogane host pose meshes from an extracted tree.

    ``source`` is the extracted `<content>/Kogane/` directory (`beetles.json`
    plus the sampled `<clip>_<ordinal>.mod` pose meshes); ``run`` is the run
    directory whose `p2-kogane-native.txt` sidecar selects the clips and whose
    `assets/dataDir/courses/pikmin2room/` room receives the staged meshes.
    Idempotent: a second call over the same run is a no-op success when every
    staged file is byte-identical; a conflicting staged file is refused with
    `StagingError` before any write.
    """
    source, run = Path(source), Path(run)
    mesh_files, clips, digest = plan(source, run)
    targets = {str(ROOM / name): payload for name, payload in mesh_files.items()}
    conflicts = sorted(name for name, payload in targets.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError('Refusing conflicting Kogane host staging: ' + ', '.join(conflicts))
    if all((run / name).is_file() for name in targets):
        staged = 'existing_identical'
    else:
        for name, payload in targets.items():
            (run / name).write_bytes(payload)
        staged = 'written'
    receipt = dict(species='Kogane', source_id=SOURCE_ID, staged=staged,
                   manifest_sha256=digest,
                   clips={name: {'count': count, 'frames': frames}
                          for name, count, frames in clips},
                   files={name: _sha(payload) for name, payload in targets.items()})
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage_kogane_host(args.source, args.run), sort_keys=True, indent=2))
