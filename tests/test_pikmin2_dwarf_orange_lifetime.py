"""Unit tests for the lane-07 Dwarf Orange Bulborb actor-lifetime probe.

Covers the shared Teki actor-lifetime seam for the Dwarf Orange Bulborb
(species ``BlueKochappy``, source_id 44).  These tests are fully offline:
they exercise ``instrument()`` on a compact synthetic ``preview_p2_room.cpp``
stand-in and ``evidence()`` against synthetic native-log strings.  They do
not build anything, touch GL, open a save, or reach the network.

The target module (``experimental.pikmin2_dwarf_orange_lifetime``) is written
by another agent and may not exist yet; every test skips cleanly in that case
via a module-level ``importorskip`` and runs for real once the module lands.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

lt = pytest.importorskip(
    'experimental.pikmin2_dwarf_orange_lifetime',
    reason='lane-07 lifetime module not written yet',
)

# A single occurrence of each required runtime marker.
GOOD_LOG = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001',
    'P2_DO_LIFETIME_SQUAD alive=20',
    'P2_DO_LIFETIME_BIND id=211001 registered=1 control=0',
    'P2_FORGET_PROBE before=1',
    'P2_FORGET_PROBE after_engine_dokill=0',
    'PASS P2_FORGET_PROBE',
    'P2_REUSE_RESPAWN generator=211001',
    'P2_REUSE_PROBE generator=211001 same_address=0 registered_before_rebind=0',
    'P2_REUSE_PROBE rebound_registered=1 alive=1',
    'PASS P2_REUSE_PROBE',
    'P2_DO_CONTROL_ALIVE alive=1',
])

# A minimal-but-realistic stand-in source: exactly one class anchor, one body
# marker we can detect disappearing, and one later ``int main(``.
ORIGINAL_SOURCE = (
    'class RoomApp : public PlugPikiApp {\n'
    '  legacy_room_body_marker();\n'
    '};\n'
    'int main(\n'
)


def drop(fragment):
    return '\n'.join(line for line in GOOD_LOG.splitlines() if fragment not in line)


def failing(result):
    return [key for key, value in result['checks'].items() if not value]


# --- requirement 5: module-level constants ----------------------------------------------------


def test_constants_sanity():
    assert lt.ID_SOURCE == 211001
    assert lt.ID_CONTROL == 211002
    assert lt.HEALTH == 250
    assert lt.SOURCE_ID == 44
    assert lt.SPECIES == 'BlueKochappy'


def test_probe_exercises_shared_seam_only():
    assert isinstance(lt.PROBE, str) and lt.PROBE
    assert 'class RoomApp : public PlugPikiApp {' in lt.PROBE
    # The probe must drive the registration/setup seam it validates…
    assert 'pc_p2_dwarf_orange_registered' in lt.PROBE
    assert 'pc_p2_dwarf_orange_setup' in lt.PROBE
    # …but never call the engine-driven family forget directly.
    assert 'pc_p2_dwarf_orange_forget' not in lt.PROBE


# --- requirement 1: evidence() accepts a fully-good log ----------------------------------------


def test_evidence_passes_on_complete_log():
    result = lt.evidence(GOOD_LOG, 0)
    assert result['passed'] is True
    assert result['exit_code'] == 0
    assert result['checks']
    assert all(result['checks'].values())
    assert result['same_address_observed'] == 0


def test_same_address_is_observed_not_gated():
    # same_address is allocator-dependent; the seam invariant is the clean
    # rebind (registered_before_rebind=0), which holds either way.
    reuse_zero = lt.evidence(GOOD_LOG, 0)
    reuse_one = lt.evidence(
        GOOD_LOG.replace('same_address=0', 'same_address=1', 1), 0)
    assert reuse_zero['same_address_observed'] == 0
    assert reuse_one['same_address_observed'] == 1
    assert reuse_one['passed'] is True


# --- requirement 2: evidence() is strict -------------------------------------------------------


@pytest.mark.parametrize('name, fragment', [
    ('identity', 'P2_ENEMY_READY species=BlueKochappy source_id=44'),
    ('squad', 'P2_DO_LIFETIME_SQUAD alive='),
    ('bind', 'P2_DO_LIFETIME_BIND id=211001'),
    ('forget_before', 'P2_FORGET_PROBE before=1'),
    ('forget_after', 'P2_FORGET_PROBE after_engine_dokill=0'),
    ('forget_pass', 'PASS P2_FORGET_PROBE'),
    ('respawn', 'P2_REUSE_RESPAWN generator=211001'),
    ('reuse_clean', 'P2_REUSE_PROBE generator=211001 same_address=0 registered_before_rebind=0'),
    ('reuse_rebound', 'P2_REUSE_PROBE rebound_registered=1 alive=1'),
    ('reuse_pass', 'PASS P2_REUSE_PROBE'),
    ('control_alive', 'P2_DO_CONTROL_ALIVE alive=1'),
    ('window', '960x540'),
])
def test_missing_marker_fails(name, fragment):
    result = lt.evidence(drop(fragment), 0)
    assert result['passed'] is False, name
    assert failing(result), name


@pytest.mark.parametrize('name, before, after', [
    ('squad_alive_zero', 'P2_DO_LIFETIME_SQUAD alive=20', 'P2_DO_LIFETIME_SQUAD alive=0'),
    ('bind_control_one', 'control=0', 'control=1'),
    ('forget_after_one', 'after_engine_dokill=0', 'after_engine_dokill=1'),
    ('reuse_rebind_one', 'registered_before_rebind=0', 'registered_before_rebind=1'),
    ('rebound_alive_zero', 'rebound_registered=1 alive=1', 'rebound_registered=1 alive=0'),
    ('control_alive_zero', 'P2_DO_CONTROL_ALIVE alive=1', 'P2_DO_CONTROL_ALIVE alive=0'),
])
def test_wrong_value_fails(name, before, after):
    result = lt.evidence(GOOD_LOG.replace(before, after, 1), 0)
    assert result['passed'] is False, name
    assert failing(result), name


def test_nonzero_exit_code_fails():
    result = lt.evidence(GOOD_LOG, 7)
    assert result['exit_code'] == 7
    assert result['passed'] is False
    assert all(result['checks'].values())


# --- requirement 3: both PASS completion markers are required ----------------------------------


@pytest.mark.parametrize('marker', ['PASS P2_FORGET_PROBE', 'PASS P2_REUSE_PROBE'])
def test_requires_both_pass_completion_markers(marker):
    result = lt.evidence(drop(marker), 0)
    assert result['passed'] is False


# --- requirement 4: instrument() splices PROBE over the original class -------------------------


def test_instrument_splices_probe_and_keeps_main():
    out = lt.instrument(ORIGINAL_SOURCE)
    assert 'P2_DO_LIFETIME_BIND' in out
    assert 'P2_FORGET_PROBE' in out
    assert 'P2_REUSE_PROBE' in out
    assert 'PASS P2_REUSE_PROBE' in out
    assert 'int main(' in out
    assert out.count('class RoomApp : public PlugPikiApp {') == 1
    assert 'legacy_room_body_marker' not in out


def test_instrument_refuses_double_instrumentation():
    out = lt.instrument(ORIGINAL_SOURCE)
    with pytest.raises(ValueError):
        lt.instrument(out)


def test_instrument_raises_when_anchor_missing():
    with pytest.raises(ValueError):
        lt.instrument('int main(\n')
