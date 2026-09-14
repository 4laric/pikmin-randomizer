"""Generic, idempotent staging of a versioned P2 content manifest into a run tree.

The orchestrator is family-agnostic: it consumes a manifest of source-backed
entries, verifies each source hash, and stages files atomically under a
caller-provided run directory. Family extractors remain family-owned; this
module never imports them and never touches the network or retail assets.
"""
import copy
import hashlib
import itertools
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

SCHEMA = 1
KINDS = ('model', 'texture', 'anim', 'config', 'sidecar')
TEMP_SUFFIX = '.staging'
RECEIPT_SUFFIX = '-staging-receipt.json'
_ABSOLUTE = re.compile(r'^[A-Za-z]:|^[/\\]')
_HEX = re.compile(r'[0-9a-fA-F]{64}')
_TEMP = itertools.count()


class StagingError(ValueError):
    """A valid manifest cannot be staged because a source or destination is bad."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _destination(value):
    if not isinstance(value, str) or not value:
        raise ValueError('Destination must be a non-empty string')
    normalized = value.replace('\\', '/')
    if _ABSOLUTE.match(normalized):
        raise ValueError(f'Absolute destination rejected: {value!r}')
    parts = PurePosixPath(normalized).parts
    if not parts or any(part == '..' for part in parts):
        raise ValueError(f'Unsafe destination rejected: {value!r}')
    if parts[-1].endswith(TEMP_SUFFIX):
        raise ValueError(f'Destination may not be a staging temp name: {value!r}')
    return '/'.join(parts)


def validate_manifest(manifest):
    """Normalize and validate a manifest mapping; raise ValueError if malformed."""
    if not isinstance(manifest, Mapping):
        raise ValueError('Manifest must be a mapping')
    data = copy.deepcopy(dict(manifest))
    if data.get('schema') != SCHEMA:
        raise ValueError(f'Unknown manifest schema: {data.get("schema")!r}')
    version = data.get('version')
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError(f'Invalid manifest version: {version!r}')
    raw = data.get('entries')
    if not isinstance(raw, list):
        raise ValueError('Manifest entries must be a list')
    entries = []
    ids = set()
    destinations = set()
    for index, entry in enumerate(raw):
        if not isinstance(entry, Mapping):
            raise ValueError(f'Entry {index} must be a mapping')
        entry = dict(entry)
        ident = entry.get('id')
        if not isinstance(ident, str) or not ident:
            raise ValueError(f'Entry {index} has an invalid id')
        if ident in ids:
            raise ValueError(f'Duplicate entry id: {ident}')
        kind = entry.get('kind')
        if kind not in KINDS:
            raise ValueError(f'Unsupported kind for entry {ident}: {kind!r}')
        source = entry.get('source')
        if not isinstance(source, str) or not source:
            raise ValueError(f'Entry {ident} has an invalid source')
        destination = _destination(entry.get('destination'))
        if destination in destinations:
            raise ValueError(f'Duplicate destination: {destination}')
        digest = entry.get('sha256')
        if not isinstance(digest, str) or not _HEX.fullmatch(digest):
            raise ValueError(f'Entry {ident} has an invalid sha256')
        ids.add(ident)
        destinations.add(destination)
        entries.append(dict(id=ident, kind=kind, source=source,
                            destination=destination, sha256=digest.lower()))
    return dict(schema=SCHEMA, version=version, entries=entries)


def load_manifest(path):
    """Read a JSON manifest file and validate it."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise ValueError(f'Malformed manifest JSON: {error}') from error
    return validate_manifest(data)


def _resolve(manifest, base):
    if isinstance(manifest, (str, Path)):
        path = Path(manifest)
        manifest = load_manifest(path)
        if base is None:
            base = path.parent
    else:
        manifest = validate_manifest(manifest)
    return manifest, Path(base) if base is not None else Path('.')


def staged_digest(entries):
    """Deterministic digest over the ordered (id, destination, sha256) set."""
    ordered = [dict(id=e['id'], destination=e['destination'], sha256=e['sha256'])
               for e in entries]
    blob = json.dumps(ordered, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return sha256_bytes(blob)


def _clean_temps(destination):
    removed = 0
    for temp in sorted(destination.rglob('*' + TEMP_SUFFIX)):
        if temp.is_file():
            temp.unlink()
            removed += 1
    return removed


def _stage_entry(entry, source, target):
    if target.exists():
        if not target.is_file():
            raise StagingError(f'Destination is not a file for entry {entry["id"]}: {target}')
        if sha256_file(target) == entry['sha256']:
            return 'cached'
        status = 'repaired'
    else:
        status = 'staged'
    data = source.read_bytes()
    if sha256_bytes(data) != entry['sha256']:
        raise StagingError(f'Source changed for entry {entry["id"]}')
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, NotADirectoryError) as error:
        raise StagingError(f'Unsafe destination parent for entry {entry["id"]}: {error}') from error
    temp = target.parent / f'{target.name}.{os.getpid()}.{next(_TEMP)}{TEMP_SUFFIX}'
    try:
        temp.write_bytes(data)
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    return status


def stage(manifest, destination, base=None, receipt_path=None):
    """Stage a manifest into destination and return/write a receipt.

    Sources are fully verified before any destination is created, so a missing
    or wrong-hash source fails without leaving a partial tree. Existing correct
    destinations are cached and never rewritten; wrong-hash destinations and
    leftover `.staging` temps are repaired in place. Each write is atomic.
    """
    manifest, base = _resolve(manifest, base)
    destination = Path(destination)
    resolved = {}
    for entry in manifest['entries']:
        source = Path(entry['source'])
        if not source.is_absolute():
            source = base / source
        if not source.is_file():
            raise StagingError(f'Missing source for entry {entry["id"]}: {entry["source"]}')
        digest = sha256_file(source)
        if digest != entry['sha256']:
            raise StagingError(f'Source hash mismatch for entry {entry["id"]}: '
                               f'expected {entry["sha256"]}, found {digest}')
        resolved[entry['id']] = source
    destination.mkdir(parents=True, exist_ok=True)
    if not destination.is_dir():
        raise StagingError(f'Destination is not a directory: {destination}')
    cleaned = _clean_temps(destination)
    rows = []
    tally = dict(staged=0, cached=0, repaired=0)
    for entry in manifest['entries']:
        target = destination.joinpath(*PurePosixPath(entry['destination']).parts)
        status = _stage_entry(entry, resolved[entry['id']], target)
        tally[status] += 1
        rows.append(dict(id=entry['id'], kind=entry['kind'],
                         source_sha256=entry['sha256'], destination=entry['destination'],
                         staged=status != 'cached', status=status))
    receipt = dict(schema=SCHEMA, manifest_version=manifest['version'],
                   staged_digest=staged_digest(manifest['entries']), entries=rows,
                   summary=dict(entries=len(rows), cleaned_temp=cleaned, **tally))
    if receipt_path is None:
        receipt_path = destination.parent / (destination.name + RECEIPT_SUFFIX)
    if receipt_path:
        receipt_path = Path(receipt_path)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt
