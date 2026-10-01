"""Stage the OniKurage (Greater Spotted Jellyfloat, source 72) native visual files.

Wave 3 flyers (#960). Mirrors ``experimental/pikmin2_kurage_content.py``: the
native visual loader (``pc_p2_kurage_visual_setup_greater``) opens
``assets/dataDir/courses/pikmin2room/onikurage_wait.mod`` and
``.../onikurage_attack.mod`` (required) plus eight optional per-motion shapes
(``onikurage_move1``, ``move2``, ``type1``, ``type2``, ``flick1``, ``flick2``,
``dead1``, ``dead2``). The extractor (``experimental/pikmin2_onikurage_assets.py``)
writes them into the identity content tree and names each in ``onikurage.json``
``visuals``; this module carries them byte-for-byte to where the loader opens
them. Idempotent and fail-closed like the Kurage stager.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_staging import StagingError

SOURCE_ID = 72
SPECIES = 'OniKurage'
MANIFEST = 'onikurage.json'
ROOM = Path('assets/dataDir/courses/pikmin2room')
PROFILE = 'p2-onikurage-animation.txt'
FILE_PREFIX = 'onikurage_'
# The ten names the native loader opens; wait/attack must be present.
REQUIRED_VISUALS = ('wait', 'attack')
OPTIONAL_VISUALS = ('move1', 'move2', 'type1', 'type2', 'flick1', 'flick2',
                    'dead1', 'dead2')
_MODEL_RE = re.compile(r'[A-Za-z0-9_]+\.mod')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _load_manifest(source):
    """Read and validate the extracted OniKurage manifest; fail closed on mismatch."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f'OniKurage manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'OniKurage manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'OniKurage manifest schema mismatch for identity content: {path}')
    if document.get('species') != SPECIES or document.get('enemy_id') != SOURCE_ID:
        raise StagingError(f'OniKurage manifest identity mismatch for identity content: {path}')
    return document, raw


def _visual_payloads(source, document):
    """Return the validated ``{native name: pose bytes}`` the loader opens."""
    source = Path(source)
    visuals = document.get('visuals')
    if not isinstance(visuals, list) or not visuals:
        raise StagingError('OniKurage manifest carries no visuals for identity content')
    allowed = set(REQUIRED_VISUALS) | set(OPTIONAL_VISUALS)
    payloads, seen = {}, set()
    for entry in visuals:
        if not isinstance(entry, dict):
            raise StagingError('OniKurage visual entry is malformed')
        name = entry.get('name')
        if name not in allowed:
            raise StagingError(f'OniKurage visual name not in the native loader set: {name!r}')
        if name in seen:
            raise StagingError(f'OniKurage visual name repeated: {name!r}')
        seen.add(name)
        pose = entry.get('pose')
        if not isinstance(pose, str) or not _MODEL_RE.fullmatch(pose):
            raise StagingError(f'OniKurage visual pose rejected by the native grammar: {pose!r}')
        digest = entry.get('sha256')
        if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
            raise StagingError(f'OniKurage visual SHA-256 missing for identity content: {name}')
        path = source / pose
        if not path.is_file():
            raise StagingError(f'OniKurage visual mesh missing for identity content: {path}')
        try:
            data = path.read_bytes()
        except OSError as error:
            raise StagingError(f'OniKurage visual mesh unreadable for identity content: {path}') from error
        if _sha(data) != digest:
            raise StagingError(f'OniKurage visual hash mismatch for identity content: {path}')
        if not data:
            raise StagingError(f'OniKurage visual mesh empty for identity content: {path}')
        payloads[name] = data
    missing = [name for name in REQUIRED_VISUALS if name not in payloads]
    if missing:
        raise StagingError('OniKurage required visuals missing: ' + ', '.join(missing))
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
    # #972: sampled pose bank + profile (absent from pre-bank manifests).
    from experimental.pikmin2_kurage_bank import staged_bank
    files.update(staged_bank(source, document, FILE_PREFIX, PROFILE))
    return files, _sha(raw)


def validate(source):
    """Fail-closed pre-flight: every native loader file derivable and hash-bound."""
    plan(source)


def stage_onikurage_host(source, run):
    """Stage the native OniKurage visual files from an extracted OniKurage tree.

    ``source`` is the extracted ``<content>/OniKurage/`` directory (``onikurage.json``
    plus the sampled pose meshes it names); ``run`` is the run directory whose
    ``assets/dataDir/courses/pikmin2room/`` room receives the files.  Idempotent:
    a second call over the same run is a no-op success when every staged file is
    byte-identical; a conflicting staged file is refused with ``StagingError``
    before any write.
    """
    source, run = Path(source), Path(run)
    if not run.is_dir():
        raise StagingError(f'OniKurage run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'OniKurage room directory missing for run staging: {room}')
    files, digest = plan(source)
    conflicts = sorted(name for name, payload in files.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError('Refusing conflicting OniKurage host staging: ' + ', '.join(conflicts))
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
    print(json.dumps(stage_onikurage_host(args.source, args.run), sort_keys=True, indent=2))
