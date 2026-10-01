"""Instrumentation and evidence tests for the reward lifecycle fixture (#397)."""
import pytest
from pathlib import Path

import experimental.pikmin2_reward_lifecycle as reward

SYNTHETIC = ("class RoomApp : public PlugPikiApp {\n"
             " int frames=0;\n"
             "};\n"
             "int main(int argc,char** argv) {\n"
             ' if(!pc_window_init("P2 room integration fixture",960,720))return 3;\n'
             " return 0; }\n")

LOG = (
    'P2_REWARD_TARGET generator=385875968 pokos=0 corpses=1\n'
    'P2_REWARD_ATTACK n=1 accepted=1 health=0.0\n'
    'P2_REWARD_DEATH n=1 generator=385875968\n'
    'P2_POD_RECEIPT id=corpse:385875968 value=2 new=1 pokos=2 seeds=0\n'
    'P2_REWARD_DELIVER n=1 ok=1 pokos_before=0 pokos_after=2\n'
    'P2_REWARD_RESPAWN generator=385875968 corpses_before=1 corpses_after=2\n'
    'P2_REWARD_REENTRY reused=1\n'
    'P2_REWARD_DEATH n=2 generator=385875968\n'
    'P2_POD_RECEIPT id=corpse:385875968 value=2 new=0 pokos=2 seeds=0\n'
    'P2_REWARD_DELIVER n=2 ok=1 pokos_before=2 pokos_after=2\n'
    'P2_REWARD_SUMMARY generator=385875968 deliver1=1 deliver2=1 pokos=2 corpses=2\n'
    'PASS P2_REWARD_LIFECYCLE\n')
LEDGER = 'P2_ECONOMY_1\ncorpse:385875968 2\n'


def test_instrument_replaces_roomapp_and_sets_window():
    source = reward.instrument(SYNTHETIC)
    assert 'P2_REWARD_TARGET' in source and 'int main(' in source
    assert 'Experimental preview window set to' in source
    assert source.index('P2_REWARD_TARGET') < source.index('int main(')
    with pytest.raises(ValueError):
        reward.instrument('int main() { return 0; }\n')
    with pytest.raises(ValueError):
        reward.instrument(source)


def test_instrument_current_export_preserves_startup():
    original = (Path(__file__).resolve().parents[1] / 'engine/tools/preview_p2_room.cpp').read_text()
    result = reward.instrument(original)
    assert result[result.index('int main('):] == original[original.index('int main('):]
    assert 'P2_REWARD_TARGET' in result


def test_validate_requires_duplicate_rejection_and_ledger():
    result = reward.validate(LOG, 0, LEDGER)
    assert result['passed'], result['checks']
    assert all(result['checks'].values())

    duplicated = LOG.replace('new=0 pokos=2', 'new=1 pokos=2')
    assert not reward.validate(duplicated, 0, LEDGER)['passed']

    two_rows = LEDGER + 'corpse:385875968 2\n'
    assert not reward.validate(LOG, 0, two_rows)['passed']

    assert not reward.validate(LOG, 1, LEDGER)['passed']
    assert not reward.validate(LOG, 0, None)['passed']


@pytest.mark.parametrize('marker', ['P2_REWARD_DEATH n=1', 'P2_REWARD_DEATH n=2',
                                    'P2_REWARD_DELIVER n=1', 'P2_REWARD_DELIVER n=2',
                                    'P2_REWARD_RESPAWN', 'P2_REWARD_REENTRY'])
def test_each_missing_stage_fails(marker):
    assert not reward.validate(LOG.replace(marker, 'absent'), 0, LEDGER)['passed']
