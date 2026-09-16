"""Flip tests for the muse l62 Long Legs observer (#502)."""
import re
from pathlib import Path

import pytest

from experimental.pikmin2_muse_longlegs import (
    check_bigfoot_walk_seen,
    check_death_intent,
    check_no_carcass_source,
    check_walk_translation,
    parse_walks,
    validate,
)

GOOD_LOG = """\
Experimental preview window set to 960x540 windowed and centered
P2_LONG_LEGS_BIND generator=312001 species=Houdai pose=bind visual_only=0 native_fsm=implemented
P2_LONG_LEGS_BIND generator=312002 species=BigFoot pose=bind visual_only=0 native_fsm=implemented
P2_MUSE_WALK_READY squad=20 houdai_gen=312001 bigfoot_gen=312002
P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Walk
P2_LONG_LEGS_WALK species=Houdai generator=312001 from=120.0,1850.0 to=40.0,1810.0 speed=250.0
P2_LONG_LEGS_WALK_END species=Houdai generator=312001 distance=120.0 seconds=0.60
P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=Walk
P2_LONG_LEGS_WALK species=BigFoot generator=312002 from=330.0,1900.0 to=300.0,1890.0 speed=70.0
P2_LONG_LEGS_WALK_END species=BigFoot generator=312002 distance=31.6 seconds=0.50
P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Shot
P2_LONG_LEGS_DAMAGE species=Houdai generator=312001 health=120.00 prior=130.00
P2_LONG_LEGS_DAMAGE species=Houdai generator=312001 health=100.00 prior=120.00
P2_LONG_LEGS_DEAD species=Houdai generator=312001 health=0 prior_health=10.00
P2_MUSE_WALK_NATURAL_DEATH houdai=1 health=0.00 tick=4000
P2_MUSE_WALK_SESSION navi=1 pikis=14
PASS P2_MUSE_LONGLEGS_WALK walk+Houdai-drain
"""


def test_good_log_passes():
    result = validate(GOOD_LOG)
    assert result['passed'] is True, result['gates']
    assert result['gates']['walk_translation'] == 'pass'
    assert result['gates']['houdai_death'] == 'pass'
    assert result['gates']['preserved'] == 'pass'


def test_missing_walk_end_fails_walk_gate():
    log = GOOD_LOG.replace(
        'P2_LONG_LEGS_WALK_END species=Houdai generator=312001 distance=120.0 seconds=0.60\n', '')
    result = validate(log)
    assert result['passed'] is False
    assert result['gates']['walk_translation'] == 'fail'
    assert result['gates']['houdai_death'] == 'pass'


def test_short_full_speed_walk_passes():
    # run4 shape: Flick-interrupted Walk, 38.5u in 0.16s (~240 u/s, source 250).
    log = GOOD_LOG.replace('distance=120.0 seconds=0.60', 'distance=38.5 seconds=0.16')
    result = validate(log)
    assert result['passed'] is True
    assert result['gates']['walk_translation'] == 'pass'


def test_pinned_walk_fails_translation():
    log = GOOD_LOG.replace('distance=120.0 seconds=0.60', 'distance=0.0 seconds=3.50')
    result = validate(log)
    assert result['passed'] is False
    assert result['gates']['walk_translation'] == 'fail'


def test_teleport_speed_fails_translation():
    log = GOOD_LOG.replace('distance=120.0 seconds=0.60', 'distance=500.0 seconds=0.50')
    result = validate(log)
    assert result['passed'] is False
    assert result['gates']['walk_translation'] == 'fail'


def test_houdai_birth_breaks_death_gate():
    log = GOOD_LOG + 'P2_LONG_LEGS_BIRTH species=Houdai generator=312001 count=5\n'
    result = validate(log)
    assert result['passed'] is False
    assert result['gates']['houdai_death'] == 'fail'
    assert result['death']['houdai_no_birth'] is False


def test_injected_houdai_death_is_not_natural():
    log = GOOD_LOG + 'P2_LL_INJECT species=Houdai not_natural_combat=1\n'
    result = validate(log)
    assert result['passed'] is False
    assert result['natural_vs_injected']['inject_present'] is True
    assert result['natural_vs_injected']['houdai_death_natural'] is False


def test_missing_window_breaks_preserved():
    log = GOOD_LOG.replace(
        'Experimental preview window set to 960x540 windowed and centered\n', '')
    result = validate(log)
    assert result['passed'] is False
    assert result['gates']['preserved'] == 'fail'


def test_no_carcass_source_against_real_checkout():
    result = check_no_carcass_source()
    assert result['passed'] is True, result['detail']


def test_bigfoot_walk_seen_reports_entry():
    assert check_bigfoot_walk_seen(GOOD_LOG)['seen'] is True
    assert check_bigfoot_walk_seen('P2_LONG_LEGS_STATE species=BigFoot state=Wait\n')['seen'] is False


def test_parse_walks_shapes():
    entries, ends = parse_walks(GOOD_LOG)
    assert len(entries) == 2 and len(ends) == 2
    houdai = [e for e in entries if e['species'] == 'Houdai'][0]
    assert houdai['speed'] == pytest.approx(250.0)
    assert check_walk_translation(GOOD_LOG)['passed'] is True


def test_fixture_source_has_no_forced_transport_write():
    root = Path(__file__).resolve().parents[1]
    path = root / 'native' / 'tools' / 'p2_muse_longlegs_fixture.cpp'
    assert path.exists(), 'reserved fixture %s missing' % path
    text = path.read_text(errors='replace')
    assert 'TransportMode' not in text
    assert not re.search(r'mMode\s*=\s*PikiMode::Transport', text)
    assert 'P2_MUSE_WALK_READY' in text
