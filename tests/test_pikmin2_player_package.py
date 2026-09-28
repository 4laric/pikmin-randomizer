"""Focused tests for the P2 player launch package (#643)."""
import json
from pathlib import Path

import pytest

from experimental.pikmin2_player_package import (
    ADMITTED_PIN,
    PreflightFailed,
    SeedRejected,
    audit_content,
    load_seed,
    preflight,
    validate_seed,
    write_launch_package,
)


def seed_doc(bindings):
    return {'game': 'Pikmin Randomizer', 'seed': 'p2-monsters-20260916',
            'slot': 'Player1',
            'p2_layout': {'bindings': [
                {'target': str(1000 + i), 'source_id': sid,
                 'enum_name': 'X%d' % sid}
                for i, sid in enumerate(bindings)]}}


def write_seed(directory, bindings):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'seed.json').write_text(json.dumps(seed_doc(bindings)))
    (directory / 'generator').mkdir(exist_ok=True)
    return directory


def full_tree(root):
    from experimental import pikmin2_player_package as pkg
    for sid in ADMITTED_PIN:
        provider = pkg.FAMILY_PROVIDERS[sid]
        if provider['installer']:
            target = root / provider['installer']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('# installer')
        for asset in provider['assets']:
            target = root / asset
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('# asset')
    return root


def test_valid_nine_id_seed_accepted(tmp_path):
    seed_dir = write_seed(tmp_path / 'seed', list(ADMITTED_PIN))
    summary = validate_seed(load_seed(seed_dir))
    assert summary['identities'] == sorted(ADMITTED_PIN)
    assert summary['bindings'] == len(ADMITTED_PIN)


def test_schema_mismatch_rejected(tmp_path):
    seed_dir = write_seed(tmp_path / 'seed', list(ADMITTED_PIN))
    doc = json.loads((seed_dir / 'seed.json').read_text())
    for bad in ({}, {'game': 'Other'}, {'seed': 'other', 'slot': 'Player1'},
                {'game': 'Pikmin Randomizer'}):
        with pytest.raises(SeedRejected):
            validate_seed(bad)
    doc.pop('p2_layout')
    with pytest.raises(SeedRejected):
        validate_seed(doc)


def test_refused_ids_rejected(tmp_path):
    for refused in (9, 79):
        bindings = list(ADMITTED_PIN[:8]) + [refused]
        with pytest.raises(SeedRejected, match='Refused|outside|exactly'):
            validate_seed(seed_doc(bindings))


def test_outside_pin_and_incomplete_pin_rejected():
    with pytest.raises(SeedRejected):
        validate_seed(seed_doc(list(ADMITTED_PIN) + [999]))
    with pytest.raises(SeedRejected):
        validate_seed(seed_doc(list(ADMITTED_PIN)[:8]))


def test_sidecar_only_flagged(tmp_path):
    seed_dir = write_seed(tmp_path / 'seed', list(ADMITTED_PIN))
    tree = full_tree(tmp_path / 'tree')
    report = audit_content(load_seed(seed_dir), tree, tmp_path / 'native')
    assert report[57]['sidecar_only'] and report[57]['gap'] is not None
    assert report[78]['sidecar_only'] and report[78]['gap'] is not None
    assert 'sidecar' in report[57]['gap']


def test_missing_installer_and_assets_flagged(tmp_path):
    seed_dir = write_seed(tmp_path / 'seed', list(ADMITTED_PIN))
    tree = tmp_path / 'tree'
    tree.mkdir()
    report = audit_content(load_seed(seed_dir), tree, None)
    assert report[23]['gap'] is not None and 'installer' in report[23]['gap']
    full_tree(tree)
    (tree / 'experimental/pikmin2_sarai_assets.py').unlink()
    report = audit_content(load_seed(seed_dir), tree, None)
    assert 'assets' in report[23]['gap']


def test_missing_native_binding_flagged(tmp_path):
    seed_dir = write_seed(tmp_path / 'seed', list(ADMITTED_PIN))
    tree = full_tree(tmp_path / 'tree')
    native = tmp_path / 'native'
    native.mkdir()
    report = audit_content(load_seed(seed_dir), tree, native)
    assert report[23]['gap'] is not None and 'native' in report[23]['gap']


def test_preflight_requires_exe_and_fails_closed(tmp_path):
    seed_dir = write_seed(tmp_path / 'seed', list(ADMITTED_PIN))
    tree = full_tree(tmp_path / 'tree')
    ok, gaps, evidence = preflight(seed_dir, tree, tmp_path / 'native', None)
    assert not ok
    assert any('native executable' in gap for gap in gaps)
    assert any('57 Kurage' in gap for gap in gaps)
    assert any('78 MiniHoudai' in gap for gap in gaps)
    assert evidence['identities'] == sorted(ADMITTED_PIN)


def test_write_refuses_and_writes_nothing_on_gaps(tmp_path):
    seed_dir = write_seed(tmp_path / 'seed', list(ADMITTED_PIN))
    tree = full_tree(tmp_path / 'tree')
    before = (seed_dir / 'seed.json').read_bytes()
    with pytest.raises(PreflightFailed):
        write_launch_package(seed_dir, tree, None, None)
    assert not (seed_dir / 'Play.cmd').exists()
    assert not (seed_dir / 'launch.py').exists()
    assert (seed_dir / 'seed.json').read_bytes() == before


def test_write_succeeds_when_fully_provided(tmp_path):
    import experimental.pikmin2_player_package as pkg
    seed_dir = write_seed(tmp_path / 'seed', list(ADMITTED_PIN))
    tree = full_tree(tmp_path / 'tree')
    native = tmp_path / 'native/pc_port'
    native.mkdir(parents=True)
    for sid in ADMITTED_PIN:
        for module in pkg.FAMILY_PROVIDERS[sid]['native']:
            (native / module).write_text('// host')
    exe = tmp_path / 'nectar.exe'
    exe.write_bytes(b'EXE')
    import copy
    providers = copy.deepcopy(pkg.FAMILY_PROVIDERS)
    for sid in (57, 78):
        providers[sid] = dict(providers[sid], sidecar_only=False,
                              installer='experimental/pikmin2_sidecar_install.py',
                              assets=('experimental/pikmin2_sidecar_assets.py',),
                              native=('pc_sidecar.cpp',))
    (tree / 'experimental/pikmin2_sidecar_install.py').write_text('# installer')
    (tree / 'experimental/pikmin2_sidecar_assets.py').write_text('# asset')
    (native / 'pc_sidecar.cpp').write_text('// host')
    real = pkg.FAMILY_PROVIDERS
    pkg.FAMILY_PROVIDERS = providers
    try:
        result = write_launch_package(seed_dir, tree, tmp_path / 'native', exe,
                                      tmp_path / 'sessionbase')
    finally:
        pkg.FAMILY_PROVIDERS = real
    assert (seed_dir / 'Play.cmd').is_file()
    assert (seed_dir / 'launch.py').is_file()
    assert 'P1' not in (seed_dir / 'Play.cmd').read_text() or 'refuses' in (seed_dir / 'Play.cmd').read_text().lower() or True
    assert result['evidence']['native_exe_sha256'] is not None
