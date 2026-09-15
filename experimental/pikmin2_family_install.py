"""Lane 05 orchestration for existing family installers (generated-session path).

Family installers stay family-owned and keep their own source/bank formats. This
module is the lane 05 consumer: it resolves a named installer, guarantees the
run's private model destination exists, calls the installer, and returns its
receipt. It never converts or extracts assets and never commits retail data.

Only installers with the shared ``install(source, run, actors) -> receipt`` shape
are registered; families with bespoke signatures (bulblax, breadbug, tank,
qurione, bigtreasure, fuefuki, dwarf, kogane, uji) need an explicit adapter
before they can be consumed here.

The binding layer (:func:`resolve_family`, :func:`install_layout`) maps a seed's
``p2_layout`` bindings (source id / enum name) to a family installer and stages
each identity's content into the run tree. The first real adapters are Dwarf
Orange Bulborb (``BlueKochappy``, source id 44) and Snow Bulborb
(``YellowKochappy``, source id 45); content roots are identity-keyed so the
launcher can install a generated session without per-family manual copying.
"""
import argparse
import hashlib
import itertools
import json
import os
import shutil
import sys
from importlib import import_module
from pathlib import Path

from experimental.pikmin2_staging import StagingError, sha256_file

ROOM = 'dataDir/courses/pikmin2room'
PLACEHOLDER = '.p2-family-install-placeholder'
BINDING_RECEIPT = 'p2-binding-receipt.json'
CACHE_RECEIPT = 'cache-receipt.json'
CACHE_KEY_PREFIX = 'p2bind-'
TEMP_SUFFIX = '.staging'
# Native session files that a fresh NativeRun lays down in the run root; a
# cache snapshot must never treat them as family-installed content.
SESSION_FILES = frozenset({
    'bootstrap.txt', 'state.txt', 'hello.txt', 'checks.txt', 'deaths.txt',
    'emperor.txt', 'overlay-manifest.json', 'native.log',
})
_TEMP = itertools.count()

# Family name -> module exposing ``install(source, run, actors)``.
FAMILY_MODULES = {
    'aquatic': 'experimental.pikmin2_aquatic_install',
    'bombsarai': 'experimental.pikmin2_bombsarai_install',
    'cannon_projectile': 'experimental.pikmin2_cannon_projectile_install',
    'dweevil': 'experimental.pikmin2_dweevil_install',
    'flora': 'experimental.pikmin2_flora_install',
    'flying': 'experimental.pikmin2_flying_install',
    'frog': 'experimental.pikmin2_frog_install',
    'ground_inverts': 'experimental.pikmin2_ground_inverts_install',
    'long_legs': 'experimental.pikmin2_long_legs_install',
    'mamuta': 'experimental.pikmin2_mamuta_install',
    'sheargrub': 'experimental.pikmin2_sheargrub_install',
    'snagret': 'experimental.pikmin2_snagret_install',
    'waterwraith': 'experimental.pikmin2_waterwraith_install',
}
_OVERRIDES = {}

# Identity-to-family mapping for the binding layer. Only identities whose family
# already has a lane 05 installer/adapter are registered; anything else resolves
# to a clear failure instead of silently binding to a P1 analogue.
IDENTITY_FAMILY = {
    44: 'dwarf_orange', 'bluekochappy': 'dwarf_orange',
    45: 'snow', 'yellowkochappy': 'snow',
}


def _validate_dwarf_orange(source):
    """Pre-flight check for the Dwarf Orange identity content (source only).

    Mirrors the source-side requirements of ``pikmin2_dwarf_orange_install.plan``
    (identity + reference binding) so a wrong/missing source is rejected before
    any ``<run>/assets`` destination is prepared; ``install`` re-checks the full
    contract and remains authoritative.
    """
    from experimental import pikmin2_dwarf_orange_install as dwarf
    source = Path(source)
    bank_json = source / 'bank' / 'dwarf-orange-bank.json'
    profile_json = source / 'profile' / 'dwarf-orange-profile.json'
    if not bank_json.is_file():
        raise StagingError(f'Dwarf Orange bank missing for identity content: {bank_json}')
    if not profile_json.is_file():
        raise StagingError(f'Dwarf Orange profile missing for identity content: {profile_json}')
    try:
        metadata = json.loads(bank_json.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Dwarf Orange bank unreadable for identity content: {bank_json}') from error
    if (metadata.get('schema'), metadata.get('species'), metadata.get('source_id'),
            metadata.get('health')) != (1, 'BlueKochappy', 44, 250):
        raise StagingError(f'Dwarf Orange bank identity mismatch for identity content: {bank_json}')
    reference = metadata.get('reference_sha256')
    if not reference or reference != dwarf.sha(profile_json.read_bytes()):
        raise StagingError(f'Dwarf Orange bank bound to a different source import: {bank_json}')


def _adapt_dwarf_orange(source, run, actors):
    """Adapter for the bespoke Dwarf Orange (BlueKochappy) installer.

    ``source`` is the identity content dir laid out as ``<source>/bank`` and
    ``<source>/profile``, matching the family bank builder's two outputs.
    """
    from experimental import pikmin2_dwarf_orange_install as dwarf
    return dwarf.install(Path(source) / 'bank', Path(source) / 'profile', Path(run),
                         [generator for generator, _species in actors])


def _validate_snow(source):
    """Pre-flight check for the Snow (YellowKochappy) identity content.

    Snow uses ``pikmin2_enemy``'s flat bank layout (``snow.json`` + ``p2-snow.txt``
    + ``snow_*.mod``); the identity and bank files must exist and declare Snow.
    """
    source = Path(source)
    snow_json = source / 'snow.json'
    if not snow_json.is_file():
        raise StagingError(f'Snow import missing for identity content: {snow_json}')
    if not (source / 'p2-snow.txt').is_file():
        raise StagingError(f'Snow bank config missing for identity content: {source / "p2-snow.txt"}')
    try:
        metadata = json.loads(snow_json.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Snow import unreadable for identity content: {snow_json}') from error
    if metadata.get('schema') != 1 or metadata.get('species') != 'YellowKochappy':
        raise StagingError(f'Snow import identity mismatch for identity content: {snow_json}')


def _adapt_snow(source, run, actors):
    """Adapter for the Snow (YellowKochappy) installer (flat ``pikmin2_enemy`` bank)."""
    from experimental import pikmin2_enemy as snow
    generators = [generator for generator, _species in actors]
    snow.install(Path(source), Path(run), generators)
    return dict(species='YellowKochappy', source_id=45, generators=generators)


# Bespoke-family adapters, exposed alongside the shared-contract installers.
# Each adapter carries an optional ``validate(source)`` pre-flight hook run by
# ``install_layout`` before any destination write.
ADAPTERS = {
    'dwarf_orange': {'install': _adapt_dwarf_orange, 'validate': _validate_dwarf_orange},
    'snow': {'install': _adapt_snow, 'validate': _validate_snow},
}


def available():
    """Sorted family names this module can install."""
    return sorted(FAMILY_MODULES | ADAPTERS | _OVERRIDES)


def register(name, installer):
    """Register (or override) a family installer with the shared signature."""
    if not isinstance(name, str) or not name:
        raise ValueError('family name must be a non-empty string')
    if not callable(installer):
        raise ValueError('installer must be callable')
    _OVERRIDES[name] = installer


def _installer(name):
    if name in _OVERRIDES:
        return _OVERRIDES[name]
    if name in ADAPTERS:
        return ADAPTERS[name]['install']
    if name not in FAMILY_MODULES:
        raise ValueError(f'unknown family installer: {name!r}')
    module = import_module(FAMILY_MODULES[name])
    return module.install


def _validator(name):
    if name in _OVERRIDES:
        return None
    if name in ADAPTERS:
        return ADAPTERS[name].get('validate')
    return None


def prepare_private_destination(run, retail_assets, room=ROOM):
    """Build ``<run>/assets`` with the model room real and the rest retail-linked.

    Reuses the room-overlay scheme: untouched directories stay junctions and
    files are hardlinked, but the family model room is materialized as a real
    directory so an installer can write into it without touching retail assets.
    """
    from scripts.preview_pikmin2_room import overlay
    assets = Path(run) / 'assets'
    if assets.exists():
        raise ValueError(f'run assets already prepared: {assets}')
    sentinel = f'{room}/{PLACEHOLDER}'
    overlay(Path(retail_assets), assets, {sentinel: b''})
    placeholder = assets / room / PLACEHOLDER
    if not placeholder.is_file():
        raise ValueError('room overlay did not materialize the private destination')
    placeholder.unlink()
    return assets


def install_family(name, source, run, actors, retail_assets=None):
    """Install a named family into ``run`` and return its receipt.

    When ``retail_assets`` is given the private model destination is prepared
    first; otherwise the caller must already have a private room tree.
    """
    run = Path(run)
    if retail_assets is not None:
        prepare_private_destination(run, Path(retail_assets))
    room = run / 'assets' / ROOM
    if not room.is_dir() or not room.resolve().is_relative_to(run.resolve()):
        raise ValueError('family install requires a private model destination; pass retail_assets')
    receipt = _installer(name)(Path(source), run, list(actors))
    if receipt is not None:
        (run / f'{name}-family-install-receipt.json').write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return receipt


def resolve_family(identity):
    """Resolve a P2 source id or enum name to a lane 05 family key.

    ``identity`` is an ``int`` source id or a ``str`` enum name (case-insensitive).
    Unknown identities raise ``ValueError`` rather than silently falling back to a
    P1 analogue, so an untracked identity never receives wrong content.
    """
    if isinstance(identity, bool):
        raise ValueError(f'unknown P2 identity: {identity!r}')
    if isinstance(identity, int):
        key = identity
    elif isinstance(identity, str):
        key = identity.strip().lower()
        if not key:
            raise ValueError(f'unknown P2 identity: {identity!r}')
    else:
        raise ValueError(f'unknown P2 identity: {identity!r}')
    family = IDENTITY_FAMILY.get(key)
    if family is None:
        raise ValueError(f'no family installer for P2 identity: {identity!r}')
    return family


def _resolve_binding_family(target, source_id, enum_name):
    """Resolve a binding's family, requiring its source id and enum name to agree.

    Both the source id and the enum name must resolve to the same family, so a
    binding like ``{"source_id": 999, "enum_name": "BlueKochappy"}`` fails closed
    instead of silently installing by name alone.
    """
    try:
        family = resolve_family(enum_name)
    except ValueError as exc:
        raise StagingError(f'no family installer for P2 enum {enum_name!r}') from exc
    if source_id is not None:
        try:
            family_by_id = resolve_family(source_id)
        except ValueError as exc:
            raise StagingError(
                f'no family installer for P2 source id {source_id!r}; disagrees with enum {enum_name!r}') from exc
        if family_by_id != family:
            raise StagingError(
                f'binding {target!r}: source id {source_id} ({family_by_id!r}) disagrees with enum {enum_name!r} ({family!r})')
    return family


def _content_files(run):
    """Snapshot the family-installed files in a run tree as ``{relpath: sha256}``.

    Captures only regular files the installer produced: run-root files (excluding
    the native session machinery and the binding receipt) and every file under the
    private model room. The assets overlay's retail junctions/hardlinks are never
    walked, so this is cheap and content-only.
    """
    files = {}
    for path in sorted(run.iterdir()):
        if path.is_file() and path.name not in SESSION_FILES and path.name != BINDING_RECEIPT:
            files[path.name] = sha256_file(path)
    room = run / 'assets' / ROOM
    if room.is_dir():
        for path in sorted(room.rglob('*')):
            if path.is_file():
                files[path.relative_to(run).as_posix()] = sha256_file(path)
    return files


def _populate_cache(cache_root, run, files, aggregate):
    """Copy the just-installed content into a session-level cache keyed by plan.

    The marker (``cache-receipt.json``) is written last. An interrupt mid-copy
    removes the whole partial ``p2bind-<digest>`` tree (never a half-written cache)
    and re-raises, so the next launch seeds a fresh install rather than reusing a
    partial tree.
    """
    tree = cache_root / 'tree'
    try:
        for relpath, digest in files.items():
            source = run / relpath
            destination = tree / relpath
            if not source.is_file() or sha256_file(source) != digest:
                raise StagingError(f'p2 content snapshot changed for {relpath}')
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.parent / f'{destination.name}.{os.getpid()}.{next(_TEMP)}{TEMP_SUFFIX}'
            try:
                shutil.copyfile(source, temp)
                os.replace(temp, destination)
            finally:
                if temp.exists():
                    temp.unlink()
    except BaseException:
        shutil.rmtree(cache_root, ignore_errors=True)
        raise
    marker = cache_root / CACHE_RECEIPT
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _replay_from_cache(run, cache_root, marker, retail_assets):
    """Materialize cached content into a fresh run without re-reading sources."""
    try:
        saved = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError('corrupt p2 content cache; clear it and restage') from error
    if not isinstance(saved, dict) or saved.get('schema') != 1 or saved.get('mode') != 'identity-binding':
        raise StagingError('conflicting or partial p2 content cache; clear it and restage')
    files = saved.get('files')
    if not isinstance(files, dict):
        raise StagingError('p2 content cache is missing its file manifest; clear it and restage')
    if (run / 'assets').exists():
        raise StagingError('run assets already exist; conflicting p2 binding install')
    run.mkdir(parents=True, exist_ok=True)
    if retail_assets is not None:
        prepare_private_destination(run, Path(retail_assets))
    tree = cache_root / 'tree'
    for relpath, digest in files.items():
        source = tree / relpath
        target = run / relpath
        if not source.is_file() or sha256_file(source) != digest:
            raise StagingError(f'p2 content cache missing or corrupt for {relpath}; clear it and restage')
        if target.is_file() and sha256_file(target) == digest:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.parent / f'{target.name}.{os.getpid()}.{next(_TEMP)}{TEMP_SUFFIX}'
        try:
            shutil.copyfile(source, temp)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
    receipt = dict(saved, cached=True)
    (run / BINDING_RECEIPT).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return receipt


def install_layout(run, layout, content_root, actor_bindings=None, retail_assets=None, cache_dir=None):
    """Stage each bound identity's family content into a generated-session run.

    ``layout`` is the seed's ``p2_layout`` mapping with ``bindings`` entries
    ``{"target", "source_id", "enum_name"}``. ``content_root`` is an identity-keyed
    content root; the source for a binding is ``content_root/<enum_name>``.
    ``actor_bindings`` maps every ``target`` token to its int native generator id
    (the runtime seam owned by lane 03/04 + native ``ENEMY_P2``); a missing mapping
    fails closed rather than installing untargeted content.

    ``cache_dir`` (optional) is a session-level cache directory. When supplied the
    staged content is keyed there (``p2bind-<plan digest>``), so a later launch into
    a fresh run dir materializes from the cache without re-reading sources and
    reports ``cached=True``. Without ``cache_dir``, the receipt remains at
    ``<run>/p2-binding-receipt.json`` and a matching receipt is a cached replay.

    Acceptance: fresh install, cached replay from the session cache, and fail-closed
    on unknown identities, source-id/enum disagreement, missing/wrong sources, the
    family pre-flight check, missing actor bindings, or a conflicting/partial tree.
    """
    run = Path(run)
    bindings = (layout or {}).get('bindings')
    if not isinstance(bindings, list) or not bindings:
        raise ValueError('p2_layout has no bindings')
    actor_bindings = dict(actor_bindings or {})

    # The plan digest identifies the bindings + actor map, so a matching receipt
    # or cache marker is a cached replay even after the content root is gone.
    canonical = {
        'bindings': [dict(b) for b in bindings],
        'actor_bindings': {str(t): int(g) for t, g in actor_bindings.items()},
    }
    plan_digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

    # Cached-replay detection happens before any source/binding validation, so a
    # replay never re-reads the content root (its sources may already be gone).
    cache_root = Path(cache_dir) / (CACHE_KEY_PREFIX + plan_digest) if cache_dir is not None else None
    if cache_root is not None and (cache_root / CACHE_RECEIPT).is_file():
        return _replay_from_cache(run, cache_root, cache_root / CACHE_RECEIPT, retail_assets)

    receipt_path = run / BINDING_RECEIPT
    if cache_root is None and receipt_path.is_file():
        try:
            existing = json.loads(receipt_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise StagingError('unreadable p2 binding receipt; clear the run tree to restage') from error
        if (isinstance(existing, dict) and existing.get('schema') == 1
                and existing.get('mode') == 'identity-binding'
                and existing.get('plan_digest') == plan_digest):
            return dict(existing, cached=True)
        raise StagingError('conflicting or partial p2 binding install detected; refusing to restage')

    # Validate every binding (identity resolution + agreement, source presence,
    # family pre-flight and actor binding) before creating or writing anything.
    plans = []
    for binding in bindings:
        target = binding.get('target')
        source_id = binding.get('source_id')
        enum_name = binding.get('enum_name')
        family = _resolve_binding_family(target, source_id, enum_name)
        source = Path(content_root) / enum_name
        if not source.is_dir():
            raise StagingError(f'missing content source for {enum_name!r}: {source}')
        validator = _validator(family)
        if validator is not None:
            validator(source)
        try:
            generator = int(actor_bindings[target])
        except KeyError:
            raise StagingError(f'no actor generator binding for target {target!r}') from None
        except (TypeError, ValueError):
            raise StagingError(f'actor generator for target {target!r} must be an int') from None
        plans.append((target, enum_name, family, source, generator))

    if (run / 'assets').exists():
        raise StagingError('run assets already exist; conflicting p2 binding install')

    run.mkdir(parents=True, exist_ok=True)
    if retail_assets is not None:
        prepare_private_destination(run, Path(retail_assets))
    receipts = {}
    try:
        for target, enum_name, family, source, generator in plans:
            receipts[target] = _installer(family)(source, run, [(generator, enum_name)])
    except BaseException:
        # A family installer that fails mid-copy must not leave a partial asset
        # tree or run-root sidecars (e.g. p2-snow.txt copied by the Snow adapter):
        # remove the private overlay (its retail junctions are not followed) plus
        # every adapter-produced run-root file, preserving only the native session
        # files and the (not-yet-written) binding receipt, then re-raise so the
        # next launch performs a fresh install.
        if (run / 'assets').exists():
            shutil.rmtree(run / 'assets', ignore_errors=True)
        if run.is_dir():
            for path in run.iterdir():
                if path.is_file() and path.name not in SESSION_FILES and path.name != BINDING_RECEIPT:
                    path.unlink(missing_ok=True)
        raise
    files = _content_files(run)
    aggregate = dict(schema=1, mode='identity-binding', plan_digest=plan_digest,
                     bindings=list(bindings), receipts=receipts, files=files)
    receipt_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if cache_root is not None:
        _populate_cache(cache_root, run, files, aggregate)
    return aggregate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', required=True, choices=available())
    parser.add_argument('--source', type=Path, required=True,
                        help='family bank/imported source directory')
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--retail', type=Path, default=None,
                        help='retail assets root; required to prepare a private destination')
    parser.add_argument('--actor', action='append', default=[],
                        help='generator_id:Species, repeatable')
    args = parser.parse_args(argv)
    actors = [(int(value.split(':', 1)[0]), value.split(':', 1)[1]) for value in args.actor]
    receipt = install_family(args.family, args.source, args.run, actors, retail_assets=args.retail)
    print(json.dumps(receipt, sort_keys=True, indent=2) if receipt is not None else '{}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
