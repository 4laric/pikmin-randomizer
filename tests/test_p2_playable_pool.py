import pytest

from randomizer.seed import P2_PLAYABLE_POOL, PLAYABLE_P2_SPECIES, generate, validate


def test_pool_table_derives_playable_tuple():
    assert PLAYABLE_P2_SPECIES == (44, 54, 59, 60, 61, 62)
    assert PLAYABLE_P2_SPECIES == tuple(row["source_id"] for row in P2_PLAYABLE_POOL)


def test_pool_table_rows_carry_evidence():
    assert len(P2_PLAYABLE_POOL) == len(PLAYABLE_P2_SPECIES)
    seen = set()
    for row in P2_PLAYABLE_POOL:
        assert type(row["source_id"]) is int
        assert row["enum_name"] and isinstance(row["enum_name"], str)
        evidence = row["evidence"]
        assert evidence["run"] and isinstance(evidence["run"], str)
        assert evidence["log"] and isinstance(evidence["log"], str)
        assert evidence["installer"] and isinstance(evidence["installer"], str)
        assert row["source_id"] not in seen
        seen.add(row["source_id"])
    assert seen == set(PLAYABLE_P2_SPECIES)


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
