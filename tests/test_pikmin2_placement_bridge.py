"""Directive-012 seed/native placement bridge: identity -> family and native wiring.

Lane 03 owns the seed -> native binding bridge. These tests pin the two halves of
this slice that are new:

* the root identity -> family map (and the Sarai actor-sidecar writer) now covers
  the admitted room-course cohort (Sarai 23, Otakara 59-62) in addition to the
  Dwarf Orange/Snow 44/45 pair, so a generated seed's ``install_layout`` stages
  the right family content instead of failing closed;
* the native side exposes the generic ``pc_randomizer_p2_source_for_70`` bridge
  and Sarai/Otakara consult it, so a randomizer-assigned generator selects the
  module rather than only a fixed ``p2-<family>-actors.txt`` set.

The native assertions are source-text pins (no build) and skip cleanly unless
``PIKMIN_NATIVE_ROOT`` points at a native checkout; no lane paths are hardcoded.
"""
import os
from pathlib import Path

import pytest

import experimental.pikmin2_family_install as family_install


def test_identity_family_covers_admitted_bridge_cohort():
    assert family_install.resolve_family(23) == 'sarai'
    for source_id in (59, 60, 61, 62):
        assert family_install.resolve_family(source_id) == 'dweevil'
    assert family_install.resolve_family('FireOtakara') == 'dweevil'
    assert family_install.resolve_family('Sarai') == 'sarai'
    # The existing pair is unchanged.
    assert family_install.resolve_family(44) == 'dwarf_orange'
    assert family_install.resolve_family(45) == 'snow'


def test_unknown_identity_still_fails_closed():
    with pytest.raises(ValueError):
        family_install.resolve_family(123456)


def test_sarai_adapter_writes_seed_derived_sidecar(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / 'sarai-attack-mouths.txt').write_text('P2_DEMON_MOUTHS_1 deadbeef 1\n', encoding='ascii')
    run = tmp_path / 'run'
    run.mkdir()
    assert family_install._validator('sarai')(source) is None
    # install_layout calls the adapter once per binding with a SINGLE generator,
    # so successive bindings must accumulate, not overwrite.
    first = family_install._adapt_sarai(source, run, [(211001, 'Sarai')])
    second = family_install._adapt_sarai(source, run, [(211002, 'Sarai')])
    text = (run / family_install.SARAI_ACTORS_TXT).read_text(encoding='ascii')
    assert text.splitlines()[0] == f'{family_install.SARAI_ACTORS_HEADER} 2'
    assert text.splitlines()[1:] == ['211001', '211002']
    assert first['source_id'] == 23 and first['generators'] == [211001]
    assert second['generators'] == [211001, 211002]


def test_sarai_validator_fails_closed_without_mouth_bank(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    with pytest.raises(family_install.StagingError):
        family_install._validator('sarai')(source)


def _native_root():
    root = os.environ.get('PIKMIN_NATIVE_ROOT')
    if not root:
        return None
    path = Path(root)
    return path if (path / 'pc_port' / 'pc_randomizer.cpp').is_file() else None


@pytest.mark.skipif(_native_root() is None, reason='PIKMIN_NATIVE_ROOT not set')
def test_wave_generated_placement_bridge_is_the_single_binding_owner():
    """The birth-time dispatcher is the surviving owner; lane-03 setup-time
    mechanisms (`findSeedActor`, the Otakara setup seed-scan) must be gone, so a
    merged branch cannot double-bind."""
    root = _native_root()
    genteki = (root / 'src' / 'plugPikiNakata' / 'genteki.cpp').read_text(encoding='utf-8')
    dispatcher = (root / 'pc_port' / 'pc_p2_generated_placement.cpp').read_text(encoding='utf-8')
    sarai = (root / 'pc_port' / 'pc_p2_sarai_manager.cpp').read_text(encoding='utf-8')
    otakara = (root / 'pc_port' / 'pc_p2_otakara.cpp').read_text(encoding='utf-8')
    # Survived: the birth-time binding from GenObjectTeki::birth.
    assert 'pc_p2_generated_placement_bind' in genteki
    assert 'pc_p2_sarai_manager_bind_dynamic' in dispatcher
    assert 'pc_p2_otakara_bind_dynamic' in dispatcher
    assert 'pc_p2_sarai_manager_bind_dynamic' in sarai and 'pc_p2_otakara_bind_dynamic' in otakara
    # Deleted: lane-03's superseded setup-time mechanisms.
    assert 'findSeedActor' not in sarai
    assert 'pc_randomizer_p2_source_for_70' not in otakara
    impl = (root / 'pc_port' / 'pc_randomizer.cpp').read_text(encoding='utf-8')
    header = (root / 'pc_port' / 'pc_randomizer.h').read_text(encoding='utf-8')
    assert 'pc_randomizer_p2_source_for_70' not in impl and 'pc_randomizer_p2_source_for_70' not in header
    # Fail-closed Otakara sidecar restored: a bad header/row returns, not binds.
    assert 'header != "P2_DWEEVIL_ACTORS_1"' in otakara
