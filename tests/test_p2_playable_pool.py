import pytest

from randomizer.seed import P2_PLAYABLE_POOL, PLAYABLE_P2_SPECIES, generate, validate


def test_pool_table_derives_playable_tuple():
    assert PLAYABLE_P2_SPECIES == (44, 54, 59, 60, 61, 62, 23, 79,
                                   2, 33, 35, 43, 53, 67, 76,
                                   12, 13, 14, 28, 94, 68,
                                   17, 18, 24, 75,
                                   56, 63, 69,
                                   34, 70, 65, 71, 101,
                                   25, 15)
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
    # Admit-frogs5 (#871): the 35-species pool exceeds the 33-slot target
    # set, so full-playable generation fails closed (default-deny slot
    # contract) instead of silently dropping two species. Two more accepted
    # slots (lane 04) restore the exact fit; until then the product path
    # stays red by design and this pins the fail-closed behaviour.
    with pytest.raises(ValueError, match="no unique accepted placement target"):
        generate('12345', p2_enemies=True, p2_species='playable')
    # The admitted pair still binds natively as an explicit subset (no
    # proxy tier, no rebind): the clean product path for 25/15.
    m = generate('12345', p2_enemies=True, p2_species=[25, 15])
    assert {b['source_id'] for b in m['p2_layout']['bindings']} == {25, 15}
    validate(m)
    assert m == generate('12345', p2_enemies=True, p2_species=[25, 15])


def test_explicit_subset_and_default_all():
    assert {b['source_id'] for b in generate('7', p2_enemies=True, p2_species=[44, 54])['p2_layout']['bindings']} == {44, 54}
    # Roster wave (#871): 38 admitted identities exceed the 33-slot target
    # set, so the bare default (every admitted identity needs a unique
    # target) fails closed instead of silently dropping five species. The
    # product default is --p2-species playable (35 on 33 -- see
    # test_p2_species_density for the capacity pin).
    with pytest.raises(ValueError, match="no unique accepted placement target"):
        generate('7', p2_enemies=True)


@pytest.mark.parametrize('species', [[], [44, 3], ['44'], 'most'])
def test_rejects_bad_subsets(species):
    with pytest.raises(ValueError):
        generate('7', p2_enemies=True, p2_species=species)


def test_subset_requires_p2_enemies():
    with pytest.raises(ValueError):
        generate('7', p2_species='playable')
