"""Lane 05 orchestration for existing family installers (generated-session path).

Family installers stay family-owned and keep their own source/bank formats. This
module is the lane 05 consumer: it resolves a named installer, guarantees the
run's private model destination exists, calls the installer, and returns its
receipt. It never converts or extracts assets and never commits retail data.

Only installers with the shared ``install(source, run, actors) -> receipt`` shape
are registered; families with bespoke signatures (bulblax, breadbug, tank,
qurione, bigtreasure, fuefuki, dwarf, kogane, uji) need an explicit adapter
before they can be consumed here.
"""
import argparse
import json
import sys
from importlib import import_module
from pathlib import Path

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


def available():
    """Sorted family names this module can install."""
    return sorted(FAMILY_MODULES | _OVERRIDES)


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
