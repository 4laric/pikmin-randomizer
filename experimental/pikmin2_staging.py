"""Generic, idempotent staging of a versioned P2 content manifest into a run tree.

The orchestrator is family-agnostic: it consumes a manifest of source-backed
entries, verifies each source hash, and stages files atomically under a
caller-provided run directory. Family extractors remain family-owned; this
module never imports them and never touches the network or retail assets.
"""
import argparse
import copy
import hashlib
import itertools
import json
import os
import re
import sys
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
    result = dict(schema=SCHEMA, version=version, entries=entries)
    if 'notes' in data:
        notes = data['notes']
        if not isinstance(notes, str):
            raise ValueError(f'Invalid manifest notes: {notes!r}')
        result['notes'] = notes
    return result


def load_manifest(path):
    """Read a JSON manifest file and validate it."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise ValueError(f'Malformed manifest JSON: {error}') from error
    return validate_manifest(data)


def dump_manifest(manifest, path):
    """Validate a manifest and write canonical JSON; return the validated form."""
    validated = validate_manifest(manifest)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(validated, indent=2) + '\n', encoding='utf-8')
    return validated


def build_manifest(version, entries, notes=''):
    """Normalize an explicit entry list into a validated manifest.

    Callers supply entries; the filesystem is never scanned for assets. Duplicate
    ids/destinations and malformed entries are rejected by ``validate_manifest``.
    """
    if not isinstance(entries, list):
        raise ValueError('entries must be a list')
    manifest = dict(schema=SCHEMA, version=version, notes=notes,
                    entries=copy.deepcopy(entries))
    return validate_manifest(manifest)


def _resolve(manifest, base):
    if isinstance(manifest, (str, Path)):
        path = Path(manifest)
        manifest = load_manifest(path)
        if base is None:
            base = path.parent
    else:
        manifest = validate_manifest(manifest)
    return manifest, Path(base) if base is not None else Path('.')


def _source_path(entry, base):
    source = Path(entry['source'])
    return source if source.is_absolute() else base / source


def verify_manifest(manifest, base=None):
    """Offline preflight: validate every source exists with the declared hash.

    Reads only sources; no destination is consulted or created. Returns a
    deterministic per-entry report with status ``ok``/``missing_source``/
    ``hash_mismatch``. A malformed manifest still raises ``ValueError``.
    """
    manifest, base = _resolve(manifest, base)
    rows = []
    summary = dict(entries=len(manifest['entries']), ok=0,
                   missing_source=0, hash_mismatch=0)
    for entry in manifest['entries']:
        source = _source_path(entry, base)
        found = None
        if not source.is_file():
            status = 'missing_source'
        else:
            found = sha256_file(source)
            status = 'ok' if found == entry['sha256'] else 'hash_mismatch'
        summary[status] += 1
        rows.append(dict(id=entry['id'], destination=entry['destination'],
                         source=entry['source'], sha256=entry['sha256'],
                         found_sha256=found, status=status))
    report = dict(schema=SCHEMA, version=manifest['version'],
                  ok=summary['missing_source'] == 0 and summary['hash_mismatch'] == 0,
                  entries=rows, summary=summary)
    if 'notes' in manifest:
        report['notes'] = manifest['notes']
    return report


def plan(manifest, destination, base=None):
    """Dry-run staging against a destination without modifying it.

    Per entry reports the action staging would take: ``stage`` (no destination),
    ``skip`` (identical destination bytes already present) or ``conflict``
    (destination exists with a different hash or is not a regular file). Also
    reports the planned temp name and any interrupted ``.staging`` temp.
    """
    manifest, base = _resolve(manifest, base)
    destination = Path(destination)
    rows = []
    summary = dict(entries=len(manifest['entries']), stage=0, skip=0,
                   conflict=0, interrupted=0)
    for index, entry in enumerate(manifest['entries']):
        target = destination.joinpath(*PurePosixPath(entry['destination']).parts)
        if not target.exists():
            action = 'stage'
        elif target.is_file() and sha256_file(target) == entry['sha256']:
            action = 'skip'
        else:
            action = 'conflict'
        temps = []
        if target.parent.is_dir():
            temps = sorted(name for name in os.listdir(target.parent)
                           if name.startswith(target.name)
                           and name.endswith(TEMP_SUFFIX)
                           and (target.parent / name).is_file())
        summary[action] += 1
        summary['interrupted'] += len(temps)
        rows.append(dict(id=entry['id'], kind=entry['kind'], source=entry['source'],
                         destination=entry['destination'], action=action,
                         planned_temp=f'{target.name}.{os.getpid()}.{index}{TEMP_SUFFIX}',
                         interrupted_temp=bool(temps), interrupted_temps=temps))
    interrupted = []
    if destination.is_dir():
        interrupted = sorted(path.relative_to(destination).as_posix()
                             for path in destination.rglob('*' + TEMP_SUFFIX)
                             if path.is_file())
    report = dict(schema=SCHEMA, version=manifest['version'],
                  destination=str(destination), ok=summary['conflict'] == 0,
                  entries=rows, interrupted=interrupted, summary=summary)
    if 'notes' in manifest:
        report['notes'] = manifest['notes']
    return report


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
        source = _source_path(entry, base)
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


def _report(report):
    print(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('verify', 'plan', 'stage'))
    parser.add_argument('manifest', type=Path)
    parser.add_argument('destination', nargs='?', type=Path)
    parser.add_argument('--base', type=Path, default=None)
    parser.add_argument('--receipt', type=Path, default=None)
    args = parser.parse_args(argv)
    if args.command == 'verify':
        return _report(verify_manifest(args.manifest, args.base))
    if args.destination is None:
        parser.error(f'{args.command} requires a destination')
    if args.command == 'plan':
        return _report(plan(args.manifest, args.destination, args.base))
    receipt = stage(args.manifest, args.destination, base=args.base,
                    receipt_path=args.receipt)
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
