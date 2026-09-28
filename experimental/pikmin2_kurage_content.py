"""Stage the Kurage (Lesser Spotted Jellyfloat, source 57) native visual files.

The native visual loader (``engine/pc_port/pc_p2_kurage_visual.cpp:32-54``)
opens ``assets/dataDir/courses/pikmin2room/kurage_wait.mod`` and
``.../kurage_attack.mod`` (required) plus eight optional per-motion shapes
(``kurage_move1.mod``, ``kurage_move2.mod``, ``kurage_type1.mod``,
``kurage_type2.mod``, ``kurage_flick1.mod``, ``kurage_flick2.mod``,
``kurage_dead1.mod``, ``kurage_dead2.mod``).  Missing files are non-fatal in
the loader (it logs ``P2_KURAGE_VISUAL_MISSING`` and draws the P1 host body),
but without ``wait`` and ``attack`` ``pc_p2_kurage_visual_setup()`` returns
false and the family silently keeps its host model -- the same
install-versus-content gap that kept Sarai out of the campaign.

The extractor (``experimental/pikmin2_kurage_assets.py``) writes those shapes
into the identity content tree as ``<clip>_<frame:04>.mod`` and names the exact
native file each one serves in ``kurage.json`` ``visuals``.  This module carries
them, byte-for-byte, to where the loader opens them, deriving every destination
from the extraction result.  It never converts or extracts assets and never
commits retail data.

Idempotent like the existing adapters: all payloads are computed and validated
before any mutation; a second call over the same run is a no-op success when
every staged file is byte-identical, and any conflicting staged file is refused
with ``StagingError`` before anything is written.  A missing or mismatched
source file raises ``StagingError`` -- never fabricates a shape.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_staging import StagingError

SOURCE_ID = 57
SPECIES = 'Kurage'
MANIFEST = 'kurage.json'
ROOM = Path('assets/dataDir/courses/pikmin2room')
FILE_PREFIX = 'kurage_'
# The ten names the native loader opens; wait/attack must be present.
REQUIRED_VISUALS = ('wait', 'attack')
OPTIONAL_VISUALS = ('move1', 'move2', 'type1', 'type2', 'flick1', 'flick2',
                    'dead1', 'dead2')
_MODEL_RE = re.compile(r'[A-Za-z0-9_]+\.mod')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _load_manifest(source):
    """Read and validate the extracted Kurage manifest; fail closed on mismatch."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f'Kurage manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'Kurage manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'Kurage manifest schema mismatch for identity content: {path}')
    if document.get('species') != SPECIES or document.get('enemy_id') != SOURCE_ID:
        raise StagingError(f'Kurage manifest identity mismatch for identity content: {path}')
    return document, raw


def _visual_payloads(source, document):
    """Return the validated ``{native name: pose bytes}`` the loader opens."""
    source = Path(source)
    visuals = document.get('visuals')
    if not isinstance(visuals, list) or not visuals:
        raise StagingError('Kurage manifest carries no visuals for identity content')
    allowed = set(REQUIRED_VISUALS) | set(OPTIONAL_VISUALS)
    payloads, seen = {}, set()
    for entry in visuals:
        if not isinstance(entry, dict):
            raise StagingError('Kurage visual entry is malformed')
        name = entry.get('name')
        if name not in allowed:
            raise StagingError(f'Kurage visual name not in the native loader set: {name!r}')
        if name in seen:
            raise StagingError(f'Kurage visual name repeated: {name!r}')
        seen.add(name)
        pose = entry.get('pose')
        if not isinstance(pose, str) or not _MODEL_RE.fullmatch(pose):
            raise StagingError(f'Kurage visual pose rejected by the native grammar: {pose!r}')
        digest = entry.get('sha256')
        if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
            raise StagingError(f'Kurage visual SHA-256 missing for identity content: {name}')
        path = source / pose
        if not path.is_file():
            raise StagingError(f'Kurage visual mesh missing for identity content: {path}')
        try:
            data = path.read_bytes()
        except OSError as error:
            raise StagingError(f'Kurage visual mesh unreadable for identity content: {path}') from error
        if _sha(data) != digest:
            raise StagingError(f'Kurage visual hash mismatch for identity content: {path}')
        if not data:
            raise StagingError(f'Kurage visual mesh empty for identity content: {path}')
        payloads[name] = data
    missing = [name for name in REQUIRED_VISUALS if name not in payloads]
    if missing:
        raise StagingError('Kurage required visuals missing: ' + ', '.join(missing))
    return payloads


def plan(source):
    """Validate everything and return exact payloads; never writes.

    Returns ``(files, manifest_digest)`` where ``files`` maps run-relative
    native destinations (``assets/dataDir/courses/pikmin2room/kurage_*.mod``)
    to the exact bytes the loader opens.
    """
    document, raw = _load_manifest(source)
    payloads = _visual_payloads(source, document)
    files = {str(ROOM / f'{FILE_PREFIX}{name}.mod'): data
             for name, data in payloads.items()}
    return files, _sha(raw)


def validate(source):
    """Fail-closed pre-flight: every native loader file derivable and hash-bound."""
    plan(source)


def stage_kurage_host(source, run):
    """Stage the native Kurage visual files from an extracted Kurage tree.

    ``source`` is the extracted ``<content>/Kurage/`` directory (``kurage.json``
    plus the sampled pose meshes it names); ``run`` is the run directory whose
    ``assets/dataDir/courses/pikmin2room/`` room receives the files.  Idempotent:
    a second call over the same run is a no-op success when every staged file is
    byte-identical; a conflicting staged file is refused with ``StagingError``
    before any write.
    """
    source, run = Path(source), Path(run)
    if not run.is_dir():
        raise StagingError(f'Kurage run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'Kurage room directory missing for run staging: {room}')
    files, digest = plan(source)
    conflicts = sorted(name for name, payload in files.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError('Refusing conflicting Kurage host staging: ' + ', '.join(conflicts))
    if all((run / name).is_file() for name in files):
        staged = 'existing_identical'
    else:
        for name, payload in files.items():
            (run / name).write_bytes(payload)
        staged = 'written'
    return dict(species=SPECIES, source_id=SOURCE_ID, staged=staged,
                manifest_sha256=digest,
                files={name: _sha(payload) for name, payload in files.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage_kurage_host(args.source, args.run), sort_keys=True, indent=2))
