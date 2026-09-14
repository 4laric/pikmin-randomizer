"""Lane 18 Giant/small Breadbug coexistence validator tests (#168/#220)."""
import pytest

from experimental import pikmin2_breadbug_coexistence as coexist

READY = ('P2_GIANT_BREADBUG_ACTOR_READY generator=187001 nest=187002 '
         'native_type=8 xyz=-150.000,30.000,1850.000 boss=1')
MARKER = ('P2_GIANT_COEXIST small=186081 giant=187001 nest=187002 '
          'small_alive=1 giant_alive=1 independent=1')
PASS = ('PASS P2_GIANT_BREADBUG_ARENA spawn_identity press contest digest_heal '
        'defeat_throwup nest_linked')
LOG = '\n'.join((READY, MARKER, PASS))


def test_arena_config_renders_giant_nest_and_optional_small():
    base = coexist.arena_config(187001, 187002, (-150.0, 30.0, 1850.0),
                                (-150.0, 30.0, 1650.0))
    assert base == ('187001 187002\n-150.000 30.000 1850.000\n'
                    '-150.000 30.000 1650.000\n')
    full = coexist.arena_config(187001, 187002, (-150.0, 30.0, 1850.0),
                                (-150.0, 30.0, 1650.0), small_id=186081,
                                small_xyz=(150.0, 30.0, 1550.0))
    assert full.splitlines()[-1] == '186081 150.000 30.000 1550.000'


def test_arena_config_rejects_overlapping_roles():
    with pytest.raises(ValueError, match='small and nest share generator ids'):
        coexist.arena_config(187001, 187002, (0, 0, 0), (0, 0, 0),
                             small_id=187002, small_xyz=(0, 0, 0))
    with pytest.raises(ValueError, match='small_xyz requires a small_id'):
        coexist.arena_config(187001, 187002, (0, 0, 0), (0, 0, 0),
                             small_xyz=(0, 0, 0))
    with pytest.raises(ValueError, match='small_id requires a small_xyz'):
        coexist.arena_config(187001, 187002, (0, 0, 0), (0, 0, 0), small_id=186081)


def test_validate_accepts_a_live_independent_coexistence_log():
    report = coexist.validate(LOG)
    assert report['passed'] is True
    assert report['giant_unchanged'] is True
    assert report['small_id'] == 186081
    assert report['giant_id'] == 187001
    assert report['nest_id'] == 187002
    assert report['coexistence']['ok'] is True
    assert report['coexistence']['small_actors_independent'] is True
    assert report['p2_contest_semantics'] is False
    assert report['shared_cargo'] is False


def test_validate_requires_the_coexist_marker_and_the_giant_pass():
    with pytest.raises(ValueError, match='Expected one P2_GIANT_COEXIST marker'):
        coexist.validate('\n'.join((READY, PASS)))
    report = coexist.validate('\n'.join((READY, MARKER)))
    assert report['passed'] is False
    assert report['giant_unchanged'] is False


def test_validate_rejects_dead_or_entangled_actors():
    dead = LOG.replace('small_alive=1', 'small_alive=0')
    assert coexist.validate(dead)['passed'] is False
    assert coexist.validate(dead)['small_alive'] is False
    entangled = LOG.replace('independent=1', 'independent=0')
    assert coexist.validate(entangled)['passed'] is False
    shared = LOG.replace('small=186081', 'small=187002')
    with pytest.raises(ValueError, match='small and nest share generator ids'):
        coexist.validate(shared)


def test_validate_rejects_mismatched_or_duplicate_markers():
    with pytest.raises(ValueError, match='Expected one Giant actor READY line'):
        coexist.validate('\n'.join((MARKER, PASS)))
    with pytest.raises(ValueError, match='Expected one P2_GIANT_COEXIST marker'):
        coexist.validate('\n'.join((READY, MARKER, MARKER, PASS)))
    mismatched = MARKER.replace('giant=187001', 'giant=187009')
    with pytest.raises(ValueError, match='disagree with the registered actors'):
        coexist.validate('\n'.join((READY, mismatched, PASS)))


def test_staging_plan_names_the_missing_committed_giant_stager():
    plan = coexist.staging_plan()
    assert plan['runnable_from_committed_sources'] is False
    assert any('Giant actor generator pair' in step for step in plan['steps'])
    assert 'Giant actor arena stager' in plan['missing']
