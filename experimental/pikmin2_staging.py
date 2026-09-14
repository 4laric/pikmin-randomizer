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
import shutil
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
    if not parts or any(part == '..' or ":" in part or part.rstrip(" .") != part for part in parts):
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
    if 'identities' in data:
        identities = data['identities']
        if (not isinstance(identities, list) or not identities
                or any(type(v) is not int or isinstance(v, bool) or v < 0 for v in identities)
                or len(set(identities)) != len(identities)):
            raise ValueError(f'Invalid manifest identities: {identities!r}')
        result['identities'] = sorted(identities)
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


def build_manifest(version, entries, notes='', identities=None):
    """Normalize an explicit entry list into a validated manifest.

    Callers supply entries; the filesystem is never scanned for assets. Duplicate
    ids/destinations and malformed entries are rejected by ``validate_manifest``.
    ``identities`` declares the P2 source IDs the content serves.
    """
    if not isinstance(entries, list):
        raise ValueError('entries must be a list')
    manifest = dict(schema=SCHEMA, version=version, notes=notes,
                    entries=copy.deepcopy(entries))
    if identities is not None:
        manifest['identities'] = list(identities)
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
        if not temp.resolve().is_relative_to(destination.resolve()):
            raise StagingError(f'Temporary path escapes staging directory: {temp}')
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
    # Preflight resolved paths before cleanup or writes: generated names can
    # encounter user-created symlinks/junctions in an existing run tree.
    root = destination.resolve()
    for entry in manifest['entries']:
        target = destination.joinpath(*PurePosixPath(entry['destination']).parts)
        if not target.resolve().is_relative_to(root):
            raise StagingError(f'Destination escapes staging directory: {entry["destination"]}')
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


SESSION_CONTENT_DIR = 'content'
CACHE_RECEIPT = 'cache-receipt.json'


def cache_key(manifest):
    """Stable cache directory name for a validated manifest (version + content)."""
    manifest = validate_manifest(manifest)
    return f"v{manifest['version']}-{staged_digest(manifest['entries'])}"


def _materialize(tree, destination, manifest):
    """Copy a verified cache tree into the session destination; report statuses."""
    root = destination.resolve()
    rows = []
    for entry in manifest['entries']:
        source = tree.joinpath(*PurePosixPath(entry['destination']).parts)
        target = destination.joinpath(*PurePosixPath(entry['destination']).parts)
        if not target.resolve().is_relative_to(root):
            raise StagingError(f'Destination escapes staging directory: {entry["destination"]}')
        if not source.is_file() or sha256_file(source) != entry['sha256']:
            raise StagingError(f'Content cache is missing or corrupt for entry {entry["id"]}; clear it and restage')
        if target.is_file() and sha256_file(target) == entry['sha256']:
            rows.append(dict(id=entry['id'], destination=entry['destination'], status='cached'))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.parent / f'{target.name}.{os.getpid()}.{next(_TEMP)}{TEMP_SUFFIX}'
        try:
            shutil.copyfile(source, temp)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
        rows.append(dict(id=entry['id'], destination=entry['destination'], status='materialized'))
    return rows


def _stage_asset_overlay(manifest, retail, destination, base, bound):
    """Build the run's private native asset tree with the content applied.

    Mirrors the room-overlay scheme: untouched directories stay junctions to the
    retail root, untouched files are hardlinked, and only the manifest files are
    materialized. Sources are verified before any destination is created, so a
    missing/wrong source leaves nothing behind. This is the connection that lets
    native asset lookup read the staged content tree.
    """
    from scripts.preview_pikmin2_room import overlay
    overrides = {}
    for entry in manifest['entries']:
        source = _source_path(entry, base)
        if not source.is_file():
            raise StagingError(f'Missing source for entry {entry["id"]}: {entry["source"]}')
        if sha256_file(source) != entry['sha256']:
            raise StagingError(f'Source hash mismatch for entry {entry["id"]}')
        overrides[entry['destination']] = source.read_bytes()
    if not Path(retail).is_dir():
        raise StagingError(f'Retail assets root is not a directory: {retail}')
    if destination.exists():
        raise StagingError(f'Content overlay destination already exists: {destination}')
    overlay(Path(retail), destination, overrides)
    receipt = dict(schema=SCHEMA, manifest_version=manifest['version'], mode='asset-overlay',
                   staged_digest=staged_digest(manifest['entries']), destination=str(destination),
                   identities=bound,
                   entries=[dict(id=e['id'], destination=e['destination'], status='staged')
                            for e in manifest['entries']],
                   summary=dict(entries=len(manifest['entries']), staged=len(manifest['entries']),
                                cached=0, repaired=0, cleaned_temp=0))
    receipt_path = destination.parent / (destination.name + '-content-receipt.json')
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


def stage_session_content(manifest, destination, base=None, cache_dir=None,
                          required_identities=None, retail_assets=None):
    """Stage a session's declared content automatically, with an optional cache.

    ``manifest`` is a lane 05 content manifest mapping or path. ``required_identities``
    are the seed's P2 source IDs: the manifest must declare an ``identities`` list
    that covers them, or ``StagingError`` is raised, so content is validated
    against the identities it serves. With ``retail_assets`` the destination is the
    run's native asset tree and the content is applied as a room overlay (junctions
    to retail, staged files materialized) so native lookup reads it. Otherwise
    content is installed under ``<destination>/content`` with an optional cache:
    sources are verified before anything is written, per-file atomic (no
    half-written file), and a mid-run failure can leave a resumable partial tree.
    """
    manifest, base = _resolve(manifest, base)
    declared = set(manifest.get('identities', []))
    required = set(required_identities or [])
    if required and not required <= declared:
        raise StagingError(
            f"content manifest does not cover required P2 identities: {sorted(required - declared)}")
    bound = sorted(str(value) for value in (declared or required))
    if retail_assets is not None:
        return _stage_asset_overlay(manifest, Path(retail_assets), Path(destination), base, bound)
    destination = Path(destination) / SESSION_CONTENT_DIR
    if cache_dir is None:
        receipt = stage(manifest, destination, base=base)
        return dict(receipt, cached=False, destination=str(destination), identities=bound)
    key = cache_key(manifest)
    cache_root = Path(cache_dir) / key
    tree = cache_root / 'tree'
    marker = cache_root / CACHE_RECEIPT
    if marker.is_file():
        cached = True
        receipt = json.loads(marker.read_text(encoding='utf-8'))
    else:
        cached = False
        receipt = stage(manifest, tree, base=base, receipt_path=marker)
    rows = _materialize(tree, destination, manifest)
    summary = dict(receipt.get('summary', {}))
    summary.update(materialized=sum(1 for r in rows if r['status'] == 'materialized'),
                   reused=sum(1 for r in rows if r['status'] == 'cached'))
    return dict(receipt, cached=cached, destination=str(destination),
                entries=rows, summary=summary, identities=bound)


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
