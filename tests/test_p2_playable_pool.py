import pytest

from randomizer.seed import P2_PLAYABLE_POOL, P2_REQUIRES_PURPLE, PLAYABLE_P2_SPECIES, generate, validate

# #958: Purple-only species are bound only by a --p2-purple-campaign seed.
DEFAULT_POOL = set(PLAYABLE_P2_SPECIES) - set(P2_REQUIRES_PURPLE)


def test_pool_table_derives_playable_tuple():
    assert PLAYABLE_P2_SPECIES == (44, 54, 59, 60, 61, 62, 23, 79,
                                   2, 33, 35, 43, 53, 67, 76,
                                   12, 13, 14, 28, 94, 68,
                                   17, 18, 24, 75,
                                   56, 63, 69,
                                   34, 70, 65, 71, 101,
                                   25, 15, 78, 73, 32, 38, 40, 41, 58, 57, 72, 30)
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
    # #893: a pool that outgrows its slots is sampled per seed. #899: the
    # Crawbster 94 moved to a boss arena, so the other 35 now fit exactly.
    assert ids <= DEFAULT_POOL
    assert ids | set(m['p2_layout'].get('unplaced', [])) == DEFAULT_POOL
    validate(m)
    assert m == generate('12345', p2_enemies=True, p2_species='playable')
    assert 'p2_purple_campaign' not in m
    full = generate('12345', p2_enemies=True, p2_species='playable', p2_purple_campaign=True)
    assert full['p2_purple_campaign'] is True
    validate(full)
    bound = {b['source_id'] for b in full['p2_layout']['bindings']}
    assert bound | set(full['p2_layout'].get('unplaced', [])) == set(PLAYABLE_P2_SPECIES)
    assert 40 in bound | {row['source_id'] for row in full['p2_layout']['boss_arenas']['placed']}


def test_purple_only_species_need_the_purple_campaign():
    # #958: OoPanModoki::pressCallBack (panModoki.cpp:1738) accepts Purple presses
    # only, so a default seed never binds the Giant Breadbug and a manifest that
    # does bind it must carry the opt-in.
    for bare in (generate('9', p2_enemies=True), generate('9', p2_enemies=True, p2_species='playable')):
        assert 40 not in {b['source_id'] for b in bare['p2_layout']['bindings']}
        assert 40 not in {r['source_id'] for r in bare['p2_layout']['boss_arenas']['placed']}
    with pytest.raises(ValueError, match='Purple'):
        generate('9', p2_enemies=True, p2_species=[40])
    with pytest.raises(ValueError, match='requires p2_enemies'):
        generate('9', p2_purple_campaign=True)
    opt = generate('9', p2_enemies=True, p2_species=[40], p2_purple_campaign=True)
    validate(opt)
    assert {r['source_id'] for r in opt['p2_layout']['boss_arenas']['placed']} == {40}
    stripped = {k: v for k, v in opt.items() if k != 'p2_purple_campaign'}
    with pytest.raises(ValueError, match='Purple'):
        validate(stripped)


def test_explicit_subset_and_default_all():
    assert {b['source_id'] for b in generate('7', p2_enemies=True, p2_species=[44, 54])['p2_layout']['bindings']} == {44, 54}
    # #888: roster admission equals the pool, so the bare default (every
    # admitted identity) draws from exactly the playable pool; #893 samples it.
    bare = generate('7', p2_enemies=True)
    bound = {b['source_id'] for b in bare['p2_layout']['bindings']}
    assert bound | set(bare['p2_layout'].get('unplaced', [])) == DEFAULT_POOL


@pytest.mark.parametrize('species', [[], [44, 3], ['44'], 'most'])
def test_rejects_bad_subsets(species):
    with pytest.raises(ValueError):
        generate('7', p2_enemies=True, p2_species=species)


def test_subset_requires_p2_enemies():
    with pytest.raises(ValueError):
        generate('7', p2_species='playable')
