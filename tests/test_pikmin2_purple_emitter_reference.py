import pytest
from experimental.pikmin2_purple_emitter_reference import parameter,candidate,receiver,collision_order


def test_retail_not_header_and_ambiguity():
    assert parameter(b'{P022} 4 20.000000','P022')==20
    with pytest.raises(ValueError):parameter(b'{P017} 4 60 {P017} 4 60','P017')
    with pytest.raises(ValueError):parameter(b'{P017} 4 nan','P017')


def test_xz_inclusive_plus_bounds_not_3d():
    assert candidate(60,999,0,0)
    assert not candidate(60.001,0,0,0)
    assert candidate(70,0,0,10)
    assert not candidate(70.001,0,0,10)
    assert candidate(36,1000,48,0)
    with pytest.raises(ValueError):candidate(0,0,0,-1)


def test_eligibility_guards():
    assert receiver(floor=True)
    assert not receiver(floor=False)
    assert not receiver(floor=True,alive=False)
    for key in ('dead','flying','hard_constrained','bitter','no_interrupt','bitter_immune','birth_drop_waiting'):
        assert not receiver(floor=True,**{key:True})


def test_damage_order_and_second_velocity_read():
    assert collision_order(-1,-1)[1:4]==['hipdrop:press_first_then_fallback','earthquake','press_again']
    assert 'press_again' not in collision_order(-1,0)
    assert 'earthquake' not in collision_order(0,-1)
    assert collision_order(-1,-1,target_piki=True)==[]
