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
each identity's content into the run tree. The Dwarf Orange Bulborb
(``BlueKochappy``, source id 44) is the first real adapter; content roots are
identity-keyed so the launcher can install a generated session without per-family
manual copying.
"""
import argparse
import hashlib
import json
import sys
from importlib import import_module
from pathlib import Path

from experimental.pikmin2_staging import StagingError

ROOM = 'dataDir/courses/pikmin2room'
PLACEHOLDER = '.p2-family-install-placeholder'

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
IDENTITY_FAMILY = {44: 'dwarf_orange', 'bluekochappy': 'dwarf_orange'}


def _adapt_dwarf_orange(source, run, actors):
    """Adapter for the bespoke Dwarf Orange (BlueKochappy) installer.

    ``source`` is the identity content dir laid out as ``<source>/bank`` and
    ``<source>/profile``, matching the family bank builder's two outputs.
    """
    from experimental import pikmin2_dwarf_orange_install as dwarf
    source = Path(source)
    bank = source / 'bank'
    profile = source / 'profile'
    if not (bank / 'dwarf-orange-bank.json').is_file():
        raise ValueError(f'Dwarf Orange bank missing for identity content: {bank / "dwarf-orange-bank.json"}')
    if not (profile / 'dwarf-orange-profile.json').is_file():
        raise ValueError(f'Dwarf Orange profile missing for identity content: {profile / "dwarf-orange-profile.json"}')
    return dwarf.install(bank, profile, Path(run), [generator for generator, _species in actors])


# Bespoke-family adapters, exposed alongside the shared-contract installers.
ADAPTERS = {'dwarf_orange': _adapt_dwarf_orange}


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
        return ADAPTERS[name]
    if name not in FAMILY_MODULES:
        raise ValueError(f'unknown family installer: {name!r}')
    module = import_module(FAMILY_MODULES[name])
    return module.install


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


def install_layout(run, layout, content_root, actor_bindings=None, retail_assets=None):
    """Stage each bound identity's family content into a generated-session run.

    ``layout`` is the seed's ``p2_layout`` mapping with ``bindings`` entries
    ``{"target", "source_id", "enum_name"}``. ``content_root`` is an identity-keyed
    content root; the source for a binding is ``content_root/<enum_name>``.
    ``actor_bindings`` maps every ``target`` token to its int native generator id
    (the runtime seam owned by lane 03/04 + native ``ENEMY_P2``); a missing mapping
    fails closed rather than installing untargeted content.

    Acceptance: fresh install, cached replay (a matching on-disk binding receipt is
    reused without re-reading sources) and fail-closed on unknown identities,
    missing/wrong sources, missing actor bindings, or a conflicting/partial tree.
    """
    run = Path(run)
    bindings = (layout or {}).get('bindings')
    if not isinstance(bindings, list) or not bindings:
        raise ValueError('p2_layout has no bindings')
    actor_bindings = dict(actor_bindings or {})

    # The plan digest identifies the bindings + actor map, so a matching receipt
    # is a cached replay even after the content root has moved or been deleted.
    canonical = {
        'bindings': [dict(b) for b in bindings],
        'actor_bindings': {str(t): int(g) for t, g in actor_bindings.items()},
    }
    plan_digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

    receipt_path = run / 'p2-binding-receipt.json'
    if receipt_path.is_file():
        try:
            existing = json.loads(receipt_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise StagingError('unreadable p2 binding receipt; clear the run tree to restage') from error
        if (isinstance(existing, dict) and existing.get('schema') == 1
                and existing.get('mode') == 'identity-binding'
                and existing.get('plan_digest') == plan_digest):
            return dict(existing, cached=True)
        raise StagingError('conflicting or partial p2 binding install detected; refusing to restage')

    # Validate every binding before creating or writing anything.
    plans = []
    for binding in bindings:
        target = binding.get('target')
        enum_name = binding.get('enum_name')
        family = resolve_family(enum_name)
        source = Path(content_root) / enum_name
        if not source.is_dir():
            raise StagingError(f'missing content source for {enum_name!r}: {source}')
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
    for target, enum_name, family, source, generator in plans:
        receipts[target] = _installer(family)(source, run, [(generator, enum_name)])
    aggregate = dict(schema=1, mode='identity-binding', plan_digest=plan_digest,
                     bindings=list(bindings), receipts=receipts)
    receipt_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + '\n', encoding='utf-8')
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
