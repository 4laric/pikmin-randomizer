"""Tests for the lane umimushi71 observer (shard, #374).

Pins the two-pass validator contract for UmiMushi source ID 71 (+Blind 101
bound alongside) gates 4 and 6 through a real thrown-Pikmin path: the
staged captain marker, genuine throw rows, the family death row strictly
after the first throw, disappearance with a recorded corpse finding, a
single fresh re-bind against the stale pointer, and a clean no-substitute
fixture audit. The critical discrimination tests prove an injected-death
log -- family DEAD row but no throw rows -- is rejected, as are
proxy-corpse and duplicate-rebirth logs.
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


def _death_log(completion=True, throws=(1, 2, 3), injected=False, corpse=True,
               gone=True, markers=True, floor=True):
    rows = ['P2_UMIMUSHI_BIRTH id=374004 type=3 x=-108.000 y=30.000 z=1850.000']
    if not injected:
        rows.append('P2_UMIMUSHI_THROW_STAGED nx=292.000 ny=30.000 nz=1850.000 '
                    'bx=-108.000 by=30.000 bz=1850.000')
    rows.append('P2_UMIMUSHI_SQUAD pikis=20')
    if not injected:
        rows += ['P2_UMIMUSHI_THROW n=%d generator=374004 dist=400.0 hp=1400.0' % n for n in throws]
    if markers:
        rows.append('P2_UMIMUSHI_BIND generator=374004 source_id=71')
        rows.append('P2_UMIMUSHI_BIND generator=374006 source_id=101')
        rows.append('P2_UMIMUSHI_DEAD generator=374004 source_id=71 health=0')
        rows.append('P2_UMIMUSHI_NATURAL_DEATH tick=5000 throws=%d umi_alive=0' % len(throws))
    if floor:
        rows.append('P2_UMIMUSHI_DEATH_POS x=-100.00 y=28.50 z=1900.00 ground=28.80')
    if gone:
        rows.append('P2_UMIMUSHI_FUNNEL_DROVE engine=dieSoon')
        rows.append('P2_UMIMUSHI_GONE tick=5100')
        rows.append('P2_UMIMUSHI_NO_CORPSE source_no_loot' if corpse else 'P2_UMIMUSHI_CORPSE_PRESENT')
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


def test_audit_rejects_missing_release_pair():
    broken = CLEAN_FIXTURE.replace('mFSM->transit', 'mFSM->hold')
    assert not audit_fixture_source(broken)['passed']


def test_validate_accepts_clean_death_run():
    result = validate_death(_death_log_on_floor(), 0, CLEAN_FIXTURE)
    assert result['passed'], result['checks']


def test_validate_rejects_injected_death_log():
    # Family DEAD row with no throw rows or staged marker must NOT validate.
    result = validate_death(_death_log(injected=True), 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['throw_stimulus'] is False


def test_validate_rejects_missing_disappearance():
    result = validate_death(_death_log(gone=False, completion=False), 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['resolution'] is False


def test_validate_accepts_corpse_path_without_gone():
    # Corpse pellet via the driven funnel resolves the gate without removal.
    text = _death_log(gone=False)
    text = text.replace('P2_UMIMUSHI_GONE tick=5100\n', '')
    text = text.replace('P2_UMIMUSHI_NO_CORPSE source_no_loot\n', '')
    text += 'P2_UMIMUSHI_FUNNEL_DROVE engine=dieSoon\nP2_UMIMUSHI_CORPSE_PRESENT\n'
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert result['passed'], result['checks']


def test_validate_rejects_proxy_corpse_without_funnel():
    # A corpse finding without the driven funnel marker is unprovenanced.
    text = _death_log(gone=False)
    text = text.replace('P2_UMIMUSHI_GONE tick=5100\n', '')
    text = text.replace('P2_UMIMUSHI_NO_CORPSE source_no_loot\n', '')
    text += 'P2_UMIMUSHI_CORPSE_PRESENT\n'
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['funnel_driven'] is False


def test_validate_rejects_blind_bind_missing():
    # Both 71 and 101 binds are required; the arena stages both actors.
    text = _death_log_on_floor().replace('P2_UMIMUSHI_BIND generator=374006 source_id=101\n', '')
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert not result['passed']


def test_validate_maps_captain_down_to_blocked():
    result = validate_death('P2_FIXTURE_CAPTAIN_DOWN tick=10 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED\n', 86, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['blocked'] is False


def test_validate_rejects_dirty_fixture_even_with_clean_log():
    result = validate_death(_death_log(), 0, CLEAN_FIXTURE + '\nactor->mHealth = 0;\n')
    assert not result['passed']
    assert result['checks']['fixture_audit'] is False


def _death_log_on_floor(completion=True):
    text = _death_log(completion=completion, floor=False)
    return text.replace(PASS_DEATH + chr(10),
                        'P2_UMIMUSHI_DEATH_POS x=-100.00 y=28.50 z=1900.00 ground=28.80' + chr(10) + PASS_DEATH + chr(10))


def test_validate_accepts_death_on_arena_floor():
    result = validate_death(_death_log_on_floor(), 0, CLEAN_FIXTURE)
    assert result['passed'], result['checks']
    assert result['checks']['combat_floor'] is True


def test_validate_rejects_void_death_without_floor():
    text = _death_log_on_floor().replace('y=28.50 z=1900.00 ground=28.80', 'y=0.00 z=1847.76 ground=0.00')
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['combat_floor'] is False


def test_validate_rejects_fall_death_below_floor():
    text = _death_log_on_floor().replace('y=28.50 z=1900.00 ground=28.80', 'y=-0.75 z=1943.00 ground=28.80')
    result = validate_death(text, 0, CLEAN_FIXTURE)
    assert not result['passed']
    assert result['checks']['combat_floor'] is False


def test_validate_accepts_clean_rebirth():
    text = ('P2_UMIMUSHI_BIND generator=374004 source_id=71\n'
            'P2_UMIMUSHI_REBOUND stale=0x1A2B3C fresh=0x4D5E6F generator=374004\n'
            + PASS_REBIRTH + '\n')
    result = validate_rebirth(text, 0)
    assert result['passed'], result['checks']


def test_validate_rejects_duplicate_rebirth():
    text = ('P2_UMIMUSHI_BIND generator=374004 source_id=71\n'
            'P2_UMIMUSHI_BIND generator=374004 source_id=71\n'
            'P2_UMIMUSHI_REBOUND stale=0x1A2B3C fresh=0x4D5E6F generator=374004\n'
            + PASS_REBIRTH + '\n')
    result = validate_rebirth(text, 0)
    assert not result['passed']
    assert result['checks']['rebind_once'] is False


def test_validate_rejects_identical_stale_fresh():
    text = ('P2_UMIMUSHI_BIND generator=374004 source_id=71\n'
            'P2_UMIMUSHI_REBOUND stale=0x1a2b3c fresh=0x1a2b3c generator=374004\n'
            + PASS_REBIRTH + '\n')
    result = validate_rebirth(text, 0)
    assert not result['passed']