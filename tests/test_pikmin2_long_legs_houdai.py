"""Flip-tests for the Houdai (Man-at-Legs) natural-combat gate in ``validate()``.

The family-owner lifecycle log is verifying a new slice: Houdai (312001)
natural combat damage, shell firing/hits, natural death, and the absence of any
fixture-injected Houdai lethality. These tests drive the synthetic ``validate()``
contract only: they flip one marker at a time out of a complete passing log and
assert the corresponding ``checks`` bool inverts. No GL, disc assets, save or
real run are touched.
"""
from experimental.pikmin2_long_legs_lifecycle import validate

GOOD_LOG = '\n'.join([
    'P2_LONG_LEGS_BIND generator=312001 species=Houdai pose=bind visual_only=0 native_fsm=implemented',
    'P2_LONG_LEGS_BIND generator=312002 species=BigFoot pose=bind visual_only=0 native_fsm=implemented',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Land',
    'P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Wait',
    'P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=Wait',
    'P2_LL_READY squad=20 houdai_gen=312001 bigfoot_gen=312002 attack=40',
    'P2_LONG_LEGS_DAMAGE species=BigFoot generator=312002 health=80.0 prior=95.0',
    'P2_LONG_LEGS_CRUSH species=BigFoot generator=312002 pikmin=20',
    'P2_LL_NATURAL_DEATH bigfoot=1 health=0.00',
    'P2_LL_INJECT species=BigFoot injected_health=0 source=fixture not_natural_combat=1',
    'P2_LONG_LEGS_DEAD species=BigFoot generator=312002 health=0 prior_health=25.0',
    'P2_LONG_LEGS_BIRTH species=BigFoot generator=312002 count=30',
    'P2_LONG_LEGS_DAMAGE species=Houdai generator=312001 health=80.0 prior=100.0',
    'P2_LONG_LEGS_SHELL species=Houdai generator=312001',
    'P2_LONG_LEGS_SHELL_HIT species=Houdai generator=312001 pikmin=3',
    'P2_LL_NATURAL_DEATH houdai=1 health=0.00',
    'P2_LONG_LEGS_DEAD species=Houdai generator=312001 health=0 prior_health=10.0',
    'P2_LL_CORPSE species=BigFoot pellet=1 generator=312002',
    'P2_LL_CORPSE species=Houdai pellet=1 generator=312001',
    'P2_LL_FORGET species=BigFoot count=0 registered=0',
    'P2_LL_FORGET species=Houdai count=0 registered=0',
    'P2_LL_REENTRY species=BigFoot old=0x1 new=0x2 stale=0 fresh=1 count=2',
    'P2_LL_REENTRY species=Houdai old=0x3 new=0x4 stale=0 fresh=1 count=2',
    'P2_LL_NOREWARD pod=0 pokos=-1 fresh_corpses=0',
    'PASS P2_LONG_LEGS_LIFECYCLE death=Houdai,BigFoot corpse=2 registry_empty=2 '
    'reentry=2 stale=0 duplicate_reward=0',
])

HOUDAI_KEYS = ('houdai_natural_damage', 'houdai_shell_fires', 'houdai_shell_hits',
               'houdai_natural_death', 'houdai_no_inject')


def test_validate_returns_dict_with_all_houdai_checks_true():
    result = validate(GOOD_LOG, code=0)
    assert isinstance(result, dict)
    for key in HOUDAI_KEYS:
        assert key in result['checks'], key
        assert result['checks'][key] is True, key
    for key in HOUDAI_KEYS:
        assert result['gates'][key] == 'pass', key


def test_houdai_natural_damage_flips_off_when_removed():
    marker = 'P2_LONG_LEGS_DAMAGE species=Houdai generator=312001 health=80.0 prior=100.0'
    assert validate(GOOD_LOG, code=0)['checks']['houdai_natural_damage'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'absent'), code=0)
    assert flipped['checks']['houdai_natural_damage'] is False


def test_houdai_shell_fires_flips_off_when_removed():
    marker = 'P2_LONG_LEGS_SHELL species=Houdai generator=312001'
    assert validate(GOOD_LOG, code=0)['checks']['houdai_shell_fires'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'absent'), code=0)
    assert flipped['checks']['houdai_shell_fires'] is False


def test_houdai_shell_hits_flips_off_when_removed():
    marker = 'P2_LONG_LEGS_SHELL_HIT species=Houdai generator=312001 pikmin=3'
    assert validate(GOOD_LOG, code=0)['checks']['houdai_shell_hits'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'absent'), code=0)
    assert flipped['checks']['houdai_shell_hits'] is False


def test_houdai_natural_death_flips_off_without_natural_death_flag():
    marker = 'P2_LL_NATURAL_DEATH houdai=1 health=0.00'
    assert validate(GOOD_LOG, code=0)['checks']['houdai_natural_death'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'absent'), code=0)
    assert flipped['checks']['houdai_natural_death'] is False


def test_houdai_natural_death_flips_off_without_dead_output():
    marker = 'P2_LONG_LEGS_DEAD species=Houdai generator=312001 health=0 prior_health=10.0'
    assert validate(GOOD_LOG, code=0)['checks']['houdai_natural_death'] is True
    flipped = validate(GOOD_LOG.replace(marker, 'absent'), code=0)
    assert flipped['checks']['houdai_natural_death'] is False


def test_houdai_dead_output_requires_positive_prior_health():
    assert validate(GOOD_LOG, code=0)['checks']['houdai_natural_death'] is True
    changed = GOOD_LOG.replace(
        'P2_LONG_LEGS_DEAD species=Houdai generator=312001 health=0 prior_health=10.0',
        'P2_LONG_LEGS_DEAD species=Houdai generator=312001 health=0 prior_health=0.0')
    assert validate(changed, code=0)['checks']['houdai_natural_death'] is False


def test_houdai_damage_rejects_implausible_delta():
    assert validate(GOOD_LOG, code=0)['checks']['houdai_natural_damage'] is True
    variant = GOOD_LOG.replace(
        'P2_LONG_LEGS_DAMAGE species=Houdai generator=312001 health=80.0 prior=100.0',
        'P2_LONG_LEGS_DAMAGE species=Houdai generator=312001 health=130.0 prior=600.0')
    assert validate(variant, code=0)['checks']['houdai_natural_damage'] is False


def test_houdai_no_inject_stays_true_without_houdai_inject():
    assert validate(GOOD_LOG, code=0)['checks']['houdai_no_inject'] is True


def test_houdai_inject_flips_no_inject_false():
    injected = GOOD_LOG + '\nP2_LL_INJECT species=Houdai injected_health=0 source=fixture not_natural_combat=1'
    assert validate(injected, code=0)['checks']['houdai_no_inject'] is False
