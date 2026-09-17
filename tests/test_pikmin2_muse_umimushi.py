"""Tests for the lane umimushi71 observer (shard, #374).

Pins the natural (non-injected) two-pass contract: the fixture stages ONE
captain park outside every actor's sight radius, writes no health/mode/attack
state, and has no throw path; the near Blind Bloyster (generator 374006,
source 101) is drained by the engine's own squad-vs-actor combat until the
family FSM raises UMIMUSHI_DEAD, the driven engine funnel produces the bound
corpse, and a fresh process proves a single re-bind against a differing stale
pointer. The critical discrimination tests reject an injected-death log (DEAD
row with no engagement/HP decline), a synthetic captain-damage design, and
duplicate/identical rebirths.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    'pikmin2_muse_umimushi',
    ROOT / 'experimental/pikmin2_muse_umimushi.py')
_umimushi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_umimushi)

TARGET = _umimushi.TARGET
PASS_DEATH = _umimushi.PASS_DEATH
PASS_REBIRTH = _umimushi.PASS_REBIRTH
audit_fixture_source = _umimushi.audit_fixture_source
validate_death = _umimushi.validate_death
validate_rebirth = _umimushi.validate_rebirth

CLEAN_FIXTURE = open(ROOT / 'native/tools/p2_muse_umimushi_fixture.cpp').read()


def _death_log(completion=True, engagement=True, declined=True, injected=False,
               corpse=True, gone=True, markers=True, floor=True):
    rows = ['P2_UMIMUSHI_BIRTH id=374006 type=3 x=-108.000 y=30.000 z=1850.000']
    rows.append('P2_UMIMUSHI_CAPTAIN_PARKED nx=600.000 ny=0.000 nz=1200.000 reason=outside_all_sight')
    rows.append('P2_UMIMUSHI_SQUAD pikis=20')
    rows.append('P2_UMIMUSHI_BIND generator=374004 source_id=71 visual_only=0 blind=0')
    rows.append('P2_UMIMUSHI_BIND generator=374006 source_id=101 visual_only=0 blind=1')
    if engagement:
        rows += ['P2_UMIMUSHI_EAT generator=374006 pikmin=1',
                 'P2_UMIMUSHI_FLICK generator=374006 frame=9 pikmin=5',
                 'P2_UMIMUSHI_BITE generator=374006 frame=39 pikmin=1']
    if declined:
        rows += ['P2_UMIMUSHI_VITALS tick=200 hp=470.0 x=-109.1 y=0.0 z=1853.3 ground=-0.0',
                 'P2_UMIMUSHI_VITALS tick=400 hp=245.0 x=-109.9 y=0.0 z=1856.0 ground=-0.0']
    if markers and not injected:
        rows.append('P2_UMIMUSHI_DEAD generator=374006 source_id=101 health=0')
        rows.append('P2_UMIMUSHI_NATURAL_DEATH tick=538 hp_dropped=1')
    elif markers and injected:
        rows.append('P2_UMIMUSHI_DEAD generator=374006 source_id=101 health=0')
        rows.append('P2_UMIMUSHI_NATURAL_DEATH tick=538 hp_dropped=0')
    if floor:
        rows.append('P2_UMIMUSHI_DEATH_POS x=-109.01 y=0.00 z=1856.90 ground=-0.00')
    if gone:
        rows.append('P2_UMIMUSHI_FUNNEL_DROVE engine=dieSoon')
        rows.append('P2_UMIMUSHI_GONE tick=545')
        rows.append('P2_UMIMUSHI_NO_CORPSE source_no_loot' if corpse else 'P2_UMIMUSHI_CORPSE_PRESENT engine_funnel')
    if completion:
        rows.append(PASS_DEATH)
    return '\n'.join(rows) + '\n'


def test_audit_accepts_tracked_observer_fixture():
    audit = audit_fixture_source(CLEAN_FIXTURE)
    assert audit['passed'], audit['checks']


def test_audit_rejects_health_write_fixture():
    assert not audit_fixture_source(CLEAN_FIXTURE + '\nactor->mHealth = 0;\n')['passed']


def test_audit_rejects_forced_attack_fixture():
    assert not audit_fixture_source(CLEAN_FIXTURE + '\nstartAction(PikiAction::Attack);\n')['passed']


def test_audit_rejects_missing_captain_park():
    broken = CLEAN_FIXTURE.replace('P2_UMIMUSHI_CAPTAIN_PARKED', 'P2_UMIMUSHI_STAGED')
    assert not audit_fixture_source(broken)['passed']


def test_validate_accepts_clean_death_run():
    result = validate_death(_death_log(), 0, CLEAN_FIXTURE)
    assert result['passed'], result['checks']


def test_validate_rejects_injected_death_log():
    # A DEAD row with no genuine HP decline is exactly the injected substitute.
    result = validate_death(_death_log(injected=True), 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['natural_death'] is False


def test_validate_rejects_no_engagement_log():
    result = validate_death(_death_log(engagement=False), 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['natural_engagement'] is False


def test_validate_rejects_missing_disappearance():
    result = validate_death(_death_log(gone=False, completion=False), 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['resolution'] is False


def test_validate_accepts_corpse_path_without_gone():
    text = _death_log(gone=False)
    text = text.replace('P2_UMIMUSHI_GONE tick=545\n', '')
    text = text.replace('P2_UMIMUSHI_NO_CORPSE source_no_loot\n', '')
    text += 'P2_UMIMUSHI_FUNNEL_DROVE engine=dieSoon\nP2_UMIMUSHI_CORPSE_PRESENT engine_funnel\n'
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert result['passed'], result['checks']


def test_validate_rejects_proxy_corpse_without_funnel():
    text = _death_log(gone=False)
    text = text.replace('P2_UMIMUSHI_GONE tick=545\n', '')
    text = text.replace('P2_UMIMUSHI_NO_CORPSE source_no_loot\n', '')
    text += 'P2_UMIMUSHI_CORPSE_PRESENT engine_funnel\n'
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['funnel_driven'] is False


def test_validate_rejects_wrong_target_death():
    # A death of the ordinary (71) is not this slice's target and must not pass.
    text = _death_log().replace('generator=374006 source_id=101', 'generator=374004 source_id=71')
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['natural_death'] is False


def test_validate_maps_captain_down_to_blocked():
    result = validate_death('P2_FIXTURE_CAPTAIN_DOWN tick=10 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED\n', 86, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['blocked'] is False


def test_validate_rejects_dirty_fixture_even_with_clean_log():
    result = validate_death(_death_log(), 0, CLEAN_FIXTURE + '\nactor->mHealth = 0;\n')
    assert not result['passed']
    assert result['checks']['fixture_audit'] is False


def test_validate_accepts_death_on_ground_plane():
    result = validate_death(_death_log(), 0, CLEAN_FIXTURE)
    assert result['checks']['combat_floor'] is True


def test_validate_rejects_fall_death_below_floor():
    text = _death_log().replace('y=0.00 z=1856.90 ground=-0.00', 'y=-90.75 z=1856.90 ground=-0.00')
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['combat_floor'] is False


def test_validate_rejects_floating_death():
    text = _death_log().replace('y=0.00 z=1856.90 ground=-0.00', 'y=400.00 z=1856.90 ground=-0.00')
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['combat_floor'] is False


def test_validate_accepts_clean_rebirth():
    text = ('P2_UMIMUSHI_BIND generator=374006 source_id=101 blind=1\n'
            'P2_UMIMUSHI_REBOUND stale=0x1A2B3C fresh=0x4D5E6F generator=374006\n'
            + PASS_REBIRTH + '\n')
    result = validate_rebirth(text, 0)
    assert result['passed'], result['checks']


def test_validate_rejects_duplicate_rebirth():
    text = ('P2_UMIMUSHI_BIND generator=374006 source_id=101 blind=1\n'
            'P2_UMIMUSHI_BIND generator=374006 source_id=101 blind=1\n'
            'P2_UMIMUSHI_REBOUND stale=0x1A2B3C fresh=0x4D5E6F generator=374006\n'
            + PASS_REBIRTH + '\n')
    result = validate_rebirth(text, 0)
    assert not result['passed']
    assert result['checks']['rebind_once'] is False


def test_validate_rejects_identical_stale_fresh():
    text = ('P2_UMIMUSHI_BIND generator=374006 source_id=101 blind=1\n'
            'P2_UMIMUSHI_REBOUND stale=0x1a2b3c fresh=0x1a2b3c generator=374006\n'
            + PASS_REBIRTH + '\n')
    result = validate_rebirth(text, 0)
    assert not result['passed']