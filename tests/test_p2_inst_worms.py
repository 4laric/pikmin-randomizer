"""Worm-lane identity wiring: SnakeCrow (34), SnakeWhole (70), Imomushi (65),
UmiMushi (71), UmiMushiBlind (101) via shared families (#871, inst-worms).

Covers the root half of "done" per species: IDENTITY_FAMILY row, no proxy
row coexistence (import fails closed), extractor wiring, and the aquatic
Blind-variant alias. Native behaviour + campaign evidence are covered
separately (pc_p2_snakejoint/imomushi/umimushi + bot campaign).
"""
from experimental import pikmin2_family_install as family
from randomizer.p2_proxy import load_rows
from scripts import p2_prepare_content as prepare


def test_worms_resolve_to_shared_families():
    assert family.resolve_family(34) == 'snagret'
    assert family.resolve_family(70) == 'snagret'
    assert family.resolve_family(65) == 'ground_inverts'
    assert family.resolve_family(71) == 'aquatic'
    assert family.resolve_family(101) == 'aquatic'
    assert family.resolve_family('SnakeCrow') == 'snagret'
    assert family.resolve_family('SnakeWhole') == 'snagret'
    assert family.resolve_family('Imomushi') == 'ground_inverts'
    assert family.resolve_family('UmiMushi') == 'aquatic'
    assert family.resolve_family('UmiMushiBlind') == 'aquatic'


def test_worms_have_no_proxy_rows():
    rows = load_rows()
    by_id = {row['source_id'] for row in rows}
    assert 34 not in by_id
    assert 70 not in by_id
    assert 65 not in by_id
    assert 71 not in by_id
    assert 101 not in by_id


def test_worms_extractor_wiring():
    assert prepare.EXTRACTORS[34] == 'extract_snagret'
    assert prepare.EXTRACTORS[70] == 'extract_snagret'
    assert prepare.EXTRACTORS[65] == 'extract_ground'
    assert prepare.EXTRACTORS[71] == 'extract_aquatic'
    assert prepare.EXTRACTORS[101] == 'extract_aquatic'
    assert prepare.ENUM_FOR_SOURCE[34] == 'SnakeCrow'
    assert prepare.ENUM_FOR_SOURCE[70] == 'SnakeWhole'
    assert prepare.ENUM_FOR_SOURCE[65] == 'Imomushi'
    assert prepare.ENUM_FOR_SOURCE[71] == 'UmiMushi'
    assert prepare.ENUM_FOR_SOURCE[101] == 'UmiMushiBlind'


def test_aquatic_blind_shares_umimushi_bank():
    from experimental import pikmin2_aquatic_install as aquatic

    # Blind actors resolve visuals to UmiMushi (shared bank), while the
    # actors file keeps the Blind name for the native Blind path.
    assert aquatic._actor_species([(1, 'UmiMushiBlind')]) == ['UmiMushi']
    assert aquatic._actor_species([(1, 'UmiMushi'), (2, 'UmiMushiBlind')]) == ['UmiMushi']
    payload = aquatic.actors_text([(123, 'UmiMushiBlind')])
    assert payload == b'P2_AQUATIC_ACTORS_1\n1\n123 UmiMushiBlind\n'
