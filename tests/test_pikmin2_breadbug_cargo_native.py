import pytest
from scripts.test_pikmin2_breadbug_cargo_native import evidence

ROW='P2_BREADBUG_ACTOR_DRAW\nP2_BREADBUG_CARGO_RESULT grabbed=1 held_frames=60 moved=50.000 progress=30.000 released=1 alive=0'

def test_full_observation_and_incomplete_gates():
    assert evidence(ROW)['complete']
    for old,new in [('grabbed=1','grabbed=0'),('held_frames=60','held_frames=1'),('progress=30.000','progress=-10.000'),('released=1','released=0'),('P2_BREADBUG_ACTOR_DRAW','')]:
        assert not evidence(ROW.replace(old,new))['complete']

def test_missing_or_duplicate_result_rejected():
    for text in ('',ROW+'\n'+ROW):
        with pytest.raises(ValueError):evidence(text)
