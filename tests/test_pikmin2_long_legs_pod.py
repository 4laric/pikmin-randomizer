"""Flip-tests for the Long Legs transport/reward + source-timed gate in ``validate()``.

The family-owner lifecycle log is about to gain a transport/reward slice: the
Pod receipts for the Houdai (312001) and BigFoot (312002) corpses, the
``P2_LL_FREE_RECRUIT`` squad-freeing next to a corpse, and the ``source=1``
timing marker that proves the reward arrived from the source lifespan. These
tests drive the synthetic ``validate()`` contract only: they flip one marker at
a time out of a complete passing natural+receipt log and assert the
corresponding ``checks`` bool inverts. No GL, disc assets, save or real run are
touched.
"""
import re
from pathlib import Path

import pytest

from experimental.pikmin2_long_legs_lifecycle import validate

GOOD_LOG = '\n'.join([
    'P2_LONG_LEGS_BIND generator=312001 species=Houdai pose=bind visual_only=0 native_fsm=implemented',
    'P2_LONG_LEGS_BIND generator=312002 species=BigFoot pose=bind visual_only=0 native_fsm=implemented',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Land',
    'P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Wait',
    'P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=Wait',
    'P2_LL_READY squad=20 houdai_gen=312001 bigfoot_gen=312002 attack=20',
    'P2_LL_TIMING source=1',
    'P2_LONG_LEGS_CRUSH species=BigFoot generator=312002 pikmin=20',
    'P2_LONG_LEGS_DAMAGE species=BigFoot generator=312002 health=80.0 prior=95.0',
    'P2_LONG_LEGS_DAMAGE species=Houdai generator=312001 health=80.0 prior=100.0',
    'P2_LONG_LEGS_SHELL species=Houdai generator=312001',
    'P2_LONG_LEGS_SHELL_HIT species=Houdai generator=312001 pikmin=1',
    'P2_LL_NATURAL_DEATH bigfoot=1 health=0.00',
    'P2_LL_NATURAL_DEATH houdai=1 health=0.00',
    'P2_LONG_LEGS_DEAD species=BigFoot generator=312002 health=0 prior_health=10.0',
    'P2_LONG_LEGS_DEAD species=Houdai generator=312001 health=0 prior_health=10.0',
    'P2_LONG_LEGS_BIRTH species=BigFoot generator=312002 count=30',
    'P2_LL_FREE_RECRUIT species=BigFoot count=20',
    'P2_LL_CARRY species=BigFoot state=0 alive=1 transport=20 slot=0 carr=20 pokos=0 '
    'piki[free=0 atk=0 trans=20 carry=0 other=0]',
    'P2_LL_FREE_RECRUIT species=Houdai count=20',
    'P2_LL_CARRY species=Houdai state=0 alive=1 transport=4 slot=0 pokos=0',
    '[Pikipelago] P2_POD_RECEIPT id=corpse:longlegs:312002 value=2 new=1 pokos=2 seeds=0',
    '[Pikipelago] P2_POD_RECEIPT id=corpse:longlegs:312001 value=2 new=1 pokos=4 seeds=0',
    'P2_LL_CORPSE_DRAIN remaining=0',
    'P2_LL_SESSION navi=1 pikis=20 dayend=0',
    'P2_LL_FORGET species=BigFoot count=0 registered=0',
    'P2_LL_FORGET species=Houdai count=0 registered=0',
    'P2_LL_REENTRY species=BigFoot old=0x1 new=0x2 stale=0 fresh=1 count=2',
    'P2_LL_REENTRY species=Houdai old=0x3 new=0x4 stale=0 fresh=1 count=2',
    'PASS P2_LONG_LEGS_LIFECYCLE death=Houdai,BigFoot corpse=2 registry_empty=2 '
    'reentry=2 stale=0 duplicate_reward=0',
])

NEW_KEYS = ('bigfoot_receipt', 'houdai_receipt', 'free_recruit', 'corpse_one_shot',
            'source_timed')


def test_validate_returns_dict_with_all_new_checks_true():
    result = validate(GOOD_LOG, code=0)
    assert isinstance(result, dict)
    for key in NEW_KEYS:
        assert key in result['checks'], key
        assert result['checks'][key] is True, key
    for key in NEW_KEYS:
        assert result['gates'][key] == 'pass', key


def test_bigfoot_receipt_flips_off_when_removed():
    marker = '[Pikipelago] P2_POD_RECEIPT id=corpse:longlegs:312002 value=2 new=1 pokos=2 seeds=0'
    assert validate(GOOD_LOG, code=0)['checks']['bigfoot_receipt'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'absent'), code=0)
    assert flipped['checks']['bigfoot_receipt'] is False


def test_houdai_receipt_flips_off_when_removed():
    marker = '[Pikipelago] P2_POD_RECEIPT id=corpse:longlegs:312001 value=2 new=1 pokos=4 seeds=0'
    assert validate(GOOD_LOG, code=0)['checks']['houdai_receipt'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'absent'), code=0)
    assert flipped['checks']['houdai_receipt'] is False


def test_free_recruit_flips_off_when_removed():
    assert validate(GOOD_LOG, code=0)['checks']['free_recruit'] is True
    flipped = GOOD_LOG.replace('P2_LL_FREE_RECRUIT species=BigFoot count=20', 'absent') \
                      .replace('P2_LL_FREE_RECRUIT species=Houdai count=20', 'absent')
    assert 'P2_LL_FREE_RECRUIT' not in flipped
    assert validate(flipped, code=0)['checks']['free_recruit'] is False


def test_source_timed_flips_off_when_removed():
    marker = 'P2_LL_TIMING source=1'
    assert validate(GOOD_LOG, code=0)['checks']['source_timed'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'absent'), code=0)
    assert flipped['checks']['source_timed'] is False


def test_receipts_both_present():
    result = validate(GOOD_LOG, code=0)
    assert result['checks']['bigfoot_receipt'] is True
    assert result['checks']['houdai_receipt'] is True
    assert result['gates']['bigfoot_receipt'] == 'pass'


def test_natural_carry_true_when_transport_positive():
    result = validate(GOOD_LOG, code=0)
    assert result['checks']['natural_carry'] is True
    assert result['gates']['natural_carry'] == 'pass'


def test_natural_carry_flips_when_transport_zero():
    assert validate(GOOD_LOG, code=0)['checks']['natural_carry'] is True
    assert re.search(r'P2_LL_CARRY[^\n]*transport=0\b', GOOD_LOG) is None
    flipped = re.sub(r'transport=\d+', 'transport=0', GOOD_LOG)
    assert re.search(r'P2_LL_CARRY[^\n]*transport=0\b', flipped) is not None
    assert validate(flipped, code=0)['checks']['natural_carry'] is False


def test_corpse_one_shot_flips_when_registration_survives():
    # A delivered corpse must leave no registration: the native one-shot erase is
    # what stops MonoObjectMgr slot reuse crediting a future unrelated pellet.
    marker = 'P2_LL_CORPSE_DRAIN remaining=0'
    assert validate(GOOD_LOG, code=0)['checks']['corpse_one_shot'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'P2_LL_CORPSE_DRAIN remaining=1'), code=0)
    assert flipped['checks']['corpse_one_shot'] is False


def test_session_survives_flips_when_dayend():
    # The end-of-day path tears down the gameplay section and nulls naviMgr; the
    # APP only emits P2_LL_SESSION once the run completes without that teardown.
    # session_survives is true iff a `navi=1` line exists and no `dayend=1` /
    # EXITDAYEND teardown marker is present. Skip cleanly until the validator
    # wires the gate in (a parallel change); never assert the old vacuous result.
    result = validate(GOOD_LOG, code=0)
    if 'session_survives' not in result['checks']:
        pytest.skip('session_survives gate not yet wired into validate()')
    assert result['checks']['session_survives'] is True
    teardown = GOOD_LOG.replace('P2_LL_SESSION navi=1 pikis=20 dayend=0',
                                'P2_LL_SESSION navi=0 pikis=0 dayend=1')
    assert teardown != GOOD_LOG
    flipped = validate(teardown, code=0)
    assert flipped['checks']['session_survives'] is False


def test_fixture_source_has_no_forced_transport_write():
    # The `natural_carry` gate is only meaningful because the fixture cannot force
    # the carry: assert the lane fixture never writes TransportMode / a Transport
    # action (the dead `assignTransport` was deleted in review fix 3b). This is a
    # real signal -- reintroducing a forced write flips the gate's premise.
    source = (Path(__file__).resolve().parents[1]
              / 'experimental' / 'pikmin2_long_legs_lifecycle.py').read_text()
    assert 'assignTransport' not in source
    assert 'PikiAction::Transport' not in source
    # Only a READ of the mode is allowed (transportingCount); a forced WRITE
    # (`mMode=PikiMode::TransportMode`) would make the carry non-natural.
    assert 'mMode=PikiMode::TransportMode' not in source
    assert 'TransportMode' in source  # the read is still used by transportingCount
