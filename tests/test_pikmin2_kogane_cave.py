"""Lane 17 cave treasure override, relocation and flip resolution (#168/#219)."""
import pytest

from experimental import pikmin2_kogane_cave as cave
from experimental.pikmin2_kogane_assets import MAX_FLIPS, drop_for


def test_treasure_override_only_on_the_first_flip():
    assert cave.treasure_override('kogane', 1, 'TREASURE_1') == 'TREASURE_1'
    assert cave.treasure_override('wealthy', 1, 42) == 42
    assert cave.treasure_override('fart', 2, 'TREASURE_1') is None
    assert cave.treasure_override('kogane', MAX_FLIPS, 'TREASURE_1') is None
    assert cave.treasure_override('kogane', 1, None) is None


def test_treasure_override_replaces_the_table_on_the_first_flip():
    first = cave.resolve_flip('kogane', 1, carried_treasure='TREASURE_1')
    assert first['treasure'] == 'TREASURE_1'
    assert first['drop'] is None
    later = cave.resolve_flip('kogane', 2, carried_treasure='TREASURE_1')
    assert later['treasure'] is None
    assert later['drop'] == drop_for('kogane', 1, False)


@pytest.mark.parametrize('species,flip,in_cave,demo,hit', [
    ('kogane', 1, False, False, 0),
    ('kogane', 2, False, False, 1),
    ('kogane', 3, False, True, 2),
    ('wealthy', 1, True, False, 0),
    ('wealthy', 2, True, True, 1),
    ('fart', 3, False, True, 2),
])
def test_table_fallback_matches_the_audited_branches(species, flip, in_cave, demo, hit):
    outcome = cave.resolve_flip(species, flip, in_cave=in_cave, demo_flag=demo)
    assert outcome['drop'] == drop_for(species, hit, in_cave, demo)
    assert outcome['treasure'] is None


def test_escape_is_forced_from_the_third_flip():
    assert cave.resolve_flip('kogane', 1)['escape'] is False
    assert cave.resolve_flip('kogane', 2)['escape'] is False
    assert cave.resolve_flip('kogane', MAX_FLIPS)['escape'] is True


def test_relocation_only_for_unflipped_cave_beetles():
    assert cave.relocates(0, True) is True
    assert cave.relocates(1, True) is False
    assert cave.relocates(0, False) is False
    unflipped = cave.resolve_flip('kogane', 0, in_cave=True)
    assert unflipped['relocate'] is True and unflipped['drop'] is None
    surfaced = cave.resolve_flip('kogane', 0, in_cave=False)
    assert surfaced['relocate'] is False
    assert cave.resolve_flip('kogane', 1, in_cave=True)['relocate'] is False


def test_relocation_outcome_classifies_relocate_versus_death():
    relocated = cave.relocation_outcome(0, True)
    assert relocated == {'flip': 0, 'relocate': True, 'outcome': cave.RELOCATION}
    for flip_count, in_cave in ((1, True), (2, True), (MAX_FLIPS, True), (0, False)):
        outcome = cave.relocation_outcome(flip_count, in_cave)
        assert outcome['relocate'] is False
        assert outcome['outcome'] == cave.DEATH
        assert outcome['flip'] == flip_count


def test_relocation_outcome_rejects_invalid_inputs():
    with pytest.raises(ValueError, match='Invalid flip count'):
        cave.relocation_outcome(-1, True)
    with pytest.raises(ValueError, match='Invalid flip count'):
        cave.relocation_outcome(True, True)
    with pytest.raises(ValueError, match='Invalid cave flag'):
        cave.relocation_outcome(0, 1)
    with pytest.raises(ValueError, match='Invalid cave flag'):
        cave.relocates(0, 'cave')


def test_resolve_flip_rejects_non_boolean_flags():
    with pytest.raises(ValueError, match='Invalid cave flag'):
        cave.resolve_flip('kogane', 1, in_cave=1)
    with pytest.raises(ValueError, match='Invalid demo flag'):
        cave.resolve_flip('kogane', 1, demo_flag='yes')


def test_unknown_species_and_out_of_range_flips_are_rejected():
    with pytest.raises(ValueError, match='Unknown beetle species'):
        cave.resolve_flip('bulborb', 1)
    with pytest.raises(ValueError, match='Unknown beetle species'):
        cave.treasure_override('bulborb', 1, 'TREASURE_1')
    with pytest.raises(ValueError, match='Flip out of range'):
        cave.resolve_flip('kogane', -1)
    with pytest.raises(ValueError, match='Flip out of range'):
        cave.resolve_flip('kogane', MAX_FLIPS + 1)
    with pytest.raises(ValueError, match='Flip out of range'):
        cave.resolve_flip('kogane', True)
    with pytest.raises(ValueError, match='Flip out of range'):
        cave.treasure_override('kogane', 0, 'TREASURE_1')


def test_invalid_flip_counts_are_rejected():
    with pytest.raises(ValueError, match='Invalid flip count'):
        cave.relocates(-1, True)
    with pytest.raises(ValueError, match='Invalid flip count'):
        cave.relocates(True, True)
