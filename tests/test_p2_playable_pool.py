import pytest

from randomizer.seed import PLAYABLE_P2_SPECIES, generate, validate


def test_playable_pool_binds_only_playable_species():
    m = generate('12345', p2_enemies=True, p2_species='playable')
    ids = {b['source_id'] for b in m['p2_layout']['bindings']}
    assert ids == set(PLAYABLE_P2_SPECIES)
    validate(m)
    assert m == generate('12345', p2_enemies=True, p2_species='playable')


def test_explicit_subset_and_default_all():
    assert {b['source_id'] for b in generate('7', p2_enemies=True, p2_species=[44, 54])['p2_layout']['bindings']} == {44, 54}
    assert {b['source_id'] for b in generate('7', p2_enemies=True)['p2_layout']['bindings']} > set(PLAYABLE_P2_SPECIES)


@pytest.mark.parametrize('species', [[], [44, 3], ['44'], 'most'])
def test_rejects_bad_subsets(species):
    with pytest.raises(ValueError):
        generate('7', p2_enemies=True, p2_species=species)


def test_subset_requires_p2_enemies():
    with pytest.raises(ValueError):
        generate('7', p2_species='playable')
