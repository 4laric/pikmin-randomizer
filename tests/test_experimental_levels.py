from experimental.levels import LEVELS, BY_KEY
from randomizer.catalog import START_AREAS

def test_distinct_identity_despite_reused_native_ids():
    assert len(LEVELS)==len(BY_KEY)==10
    assert len(START_AREAS)==5
    for level in LEVELS[:5]:
        alternate=BY_KEY[level.key.replace('campaign:', 'challenge:')]
        assert alternate.area_id==level.area_id
        assert alternate.key!=level.key and alternate.stage_file!=level.stage_file
    assert len({level.stage_file for level in LEVELS})==10
