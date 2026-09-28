import pytest
from experimental.pikmin2_kochappy_stun_reference import fit_after_landing,fit_tick,bounce_speed


def test_duration_strict_boundary_and_variants():
    assert fit_tick(4,1,5)==(5,'fit')
    assert fit_tick(5,.001,5)==(0,'living')
    assert fit_tick(5,.001,10)[1]=='fit'
    assert fit_tick(1,.1,10,dead=True)==(0,'living')
    assert fit_tick(1,.1,10,bitter_queued=True)==(0,'living')


def test_landing_probability_and_retained_timer():
    base=dict(steps=4,grounded=True,dead=False,timer=0,roll=.299)
    assert fit_after_landing(**base)=='fit'
    assert fit_after_landing(**dict(base,roll=.3))=='living'
    assert fit_after_landing(**dict(base,steps=3))=='earthquake'
    assert fit_after_landing(**dict(base,grounded=False))=='earthquake'
    assert fit_after_landing(**dict(base,no_interrupt=True))=='living'
    assert fit_after_landing(**dict(base,timer=2,roll=1,no_interrupt=True))=='fit'
    assert fit_after_landing(**dict(base,dead=True))=='living'


def test_bounce_and_invalid_values():
    assert bounce_speed(1,0)==200 and bounce_speed(1,1)==300
    for value in (float('nan'),float('inf'),-1):
        with pytest.raises(ValueError):fit_tick(0,value,10)
    with pytest.raises(ValueError):fit_after_landing(steps=4,grounded=True,dead=False,timer=0,roll=2)
