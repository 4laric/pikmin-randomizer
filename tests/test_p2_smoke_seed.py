"""Unit tests for scripts/p2_smoke_seed.py (#944): the any-slot override builder.

No ISO reads and no launch: the override document, slot picking, round-robin
assignment, content-cache reuse (stubbed copies/extractor) and the launcher
text are covered here; the seed generation test runs the real bridge against
the committed document so a resolver change that stops honouring the override
fails loudly.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import p2_smoke_seed as smoke


@pytest.fixture(scope='module')
def document():
    return smoke.load_default_document()


@pytest.fixture(scope='module')
def roster():
    from experimental.pikmin2_enemy_roster import load_and_validate
    return load_and_validate()


def test_ordinary_slots_can_skip_slots_gated_behind_a_later_day(document):
    all_slots = smoke.ordinary_slots(document, 'foh')
    day2 = smoke.ordinary_slots(document, 'foh', smoke.SEED_START_DAY)
    assert len(day2) < len(all_slots)
    assert all(s['first_day'] <= smoke.SEED_START_DAY for s in day2)
    gated = {s['label'] for s in all_slots} - {s['label'] for s in day2}
    assert 'hope_14-29_24' in gated and 'hope_4-29_2237' in gated


def test_foh_landing_origin_is_the_measured_captain_start():
    assert smoke.LANDING_BY_AREA['foh'] == (-316.0, 2022.0)
    assert smoke.parse_origin('-316,2022') == (-316.0, 2022.0)
    with pytest.raises(smoke.SmokeSeedError):
        smoke.parse_origin('nope')


def test_stage_content_extracts_before_copying_cached_species(tmp_path):
    cache = tmp_path / 'cache'
    (cache / 'Cached').mkdir(parents=True)
    (cache / 'Cached' / 'a.txt').write_text('x')
    out = tmp_path / 'content'
    manifest = {'p2_layout': {'bindings': [
        {'source_id': 75, 'enum_name': 'Cached'}, {'source_id': 78, 'enum_name': 'Fresh'}]}}
    seen = {}

    def prepare(iso, dest, wanted):
        seen['dest_empty_at_extract'] = not any(dest.iterdir())
        (dest / 'Fresh').mkdir()
        (dest / 'Fresh' / 'b.txt').write_text('y')
        return {'extracted_enums': ['Fresh']}

    summary = smoke.stage_content(manifest, out, cache, 'iso', prepare_fn=prepare)
    assert seen['dest_empty_at_extract'] is True
    assert (out / 'Cached' / 'a.txt').exists() and (out / 'Fresh' / 'b.txt').exists()
    assert summary['from_cache'] == ['Cached'] and summary['extracted'] == ['Fresh']


def test_ordinary_slots_exclude_protected_boss_and_held(document):
    slots = smoke.ordinary_slots(document, 'foh')
    labels = {s['label'] for s in slots}
    assert 'hope_snagret_pit' not in labels and 'hope_snagret_part' not in labels
    assert all(s['stage'] == 1 for s in slots)
    # #948: every Forest of Hope campaign generator (ground, grub, frog, dwarf,
    # flying cohorts), not only the probed ground ones.
    assert len(slots) == 21
    held = {int(h['uid']) for h in document['held_parts']}
    spring = smoke.ordinary_slots(document, 'spring')
    assert not held & {int(s['uid']) for s in spring}
    assert 'spring_puffy_blowhog_uf02' not in {s['label'] for s in spring}
    with pytest.raises(smoke.SmokeSeedError):
        smoke.ordinary_slots(document, 'moon')


def test_slot_positions_cover_every_ordinary_slot(document):
    positions = smoke.slot_positions()
    for area in ('foh', 'impact', 'navel', 'spring'):
        for slot in smoke.ordinary_slots(document, area):
            assert int(slot['uid']) in positions, slot['label']
    # Probe lines override/extend the catalog positions.
    text = 'P2_PLACEMENT_SLOT generator=1 slot=1254096625 actor=11 xyz=1 terrain=ground route=1 x=-1531.1 y=-7.4 z=3298.8 water_depth=0.00\n'
    assert smoke.slot_positions(text)[1254096625] == [-1531.1, -7.4, 3298.8]


def test_pick_slots_near_start_orders_by_landing_distance(document):
    slots = smoke.ordinary_slots(document, 'foh')
    positions = smoke.slot_positions()
    near = smoke.pick_slots(slots, 3, near_start=True, positions=positions)
    distances = [smoke.distance_xz(positions[int(s['uid'])]) for s in near]
    assert distances == sorted(distances)
    assert near[0]['uid'] == 2506165730  # hope_0-29_3073, ~72 units from the ship
    assert smoke.pick_slots(slots, 'all') == slots
    assert smoke.pick_slots(slots, None) == slots
    assert smoke.pick_slots(slots, 2) == slots[:2]
    with pytest.raises(smoke.SmokeSeedError):
        smoke.pick_slots(slots, 99)
    with pytest.raises(smoke.SmokeSeedError):
        smoke.pick_slots(slots, 0)


def test_pick_slots_unknown_position_sorts_last():
    slots = [{'uid': 1}, {'uid': 2}, {'uid': 3}]
    picked = smoke.pick_slots(slots, 'all', near_start=True, positions={3: [10, 0, 0], 1: [5, 0, 0]})
    assert [s['uid'] for s in picked] == [1, 3, 2]


def test_assign_round_robin_cycles_species():
    slots = [{'uid': u} for u in (10, 20, 30, 40, 50)]
    assert smoke.assign_round_robin([58, 32], slots) == {10: 58, 20: 32, 30: 58, 40: 32, 50: 58}
    with pytest.raises(smoke.SmokeSeedError):
        smoke.assign_round_robin([58, 32, 41, 38, 78, 17], slots)  # more species than slots
    with pytest.raises(smoke.SmokeSeedError):
        smoke.assign_round_robin([58, 58], slots)
    with pytest.raises(smoke.SmokeSeedError):
        smoke.assign_round_robin([], slots)


def test_parse_helpers():
    assert smoke.parse_bosses('94:hope_snagret_pit, 73:impact_goolix') == {94: 'hope_snagret_pit', 73: 'impact_goolix'}
    assert smoke.parse_bosses('') == {}
    assert smoke.parse_species('58, 32') == [58, 32]
    for bad in ('94', 'x:hope', '94:a,94:b'):
        with pytest.raises(smoke.SmokeSeedError):
            smoke.parse_bosses(bad)
    with pytest.raises(smoke.SmokeSeedError):
        smoke.parse_species('58,dirigibug')


def test_build_override_pins_exactly_the_assignment(document, roster):
    slots = smoke.ordinary_slots(document, 'foh')[:3]
    assignments = smoke.assign_round_robin([58, 32], slots)
    override = smoke.build_override(document, roster, assignments, {94: 'hope_snagret_pit'})
    profiles = {p['identity']: p for p in override['profiles']}
    bomb, demon, dango = profiles['BombSarai'], profiles['Demon'], profiles['DangoMushi']
    assert bomb['accepted_slot_uids'] == sorted(u for u, s in assignments.items() if s == 58)
    assert demon['accepted_slot_uids'] == sorted(u for u, s in assignments.items() if s == 32)
    assert dango['accepted_slot_uids'] == [295337326]
    assert bomb['cohort'] is None and bomb['requires_corpse_route'] is False and bomb['min_first_day'] == 0
    assert 'ground' in bomb['terrains'] and bomb['accepted_gates']
    # Every other identity accepts nothing; the committed document is untouched.
    for identity, profile in profiles.items():
        if identity not in ('BombSarai', 'Demon', 'DangoMushi'):
            assert profile['accepted_slot_uids'] == []
    base = {p['identity']: p for p in document['profiles']}
    # #948: the committed profile accepts every constraint-compatible slot
    # (its evidence slot among them), and the override never touches it.
    assert 1787125272 in base['BombSarai']['accepted_slot_uids']
    assert len(base['BombSarai']['accepted_slot_uids']) > 2
    assert override['slots'] == document['slots']
    from randomizer.p2_placement import validate_document
    validate_document(override)


def test_build_override_rejects_misuse(document, roster):
    slots = smoke.ordinary_slots(document, 'foh')[:2]
    # #948: an arena boss may take ordinary slots in a smoke seed; it just
    # cannot be listed both ways.
    override = smoke.build_override(document, roster, smoke.assign_round_robin([94], slots))
    dango = next(p for p in override['profiles'] if p['identity'] == 'DangoMushi')
    assert dango['is_boss'] is False and dango['encounter_descriptor'] is None
    assert dango['accepted_slot_uids'] == sorted(int(s['uid']) for s in slots)
    with pytest.raises(smoke.SmokeSeedError, match='both in --species and --bosses'):
        smoke.build_override(document, roster, smoke.assign_round_robin([94], slots), {94: 'hope_snagret_pit'})
    with pytest.raises(smoke.SmokeSeedError, match='not in the P2 roster'):
        smoke.build_override(document, roster, smoke.assign_round_robin([9999], slots))
    with pytest.raises(smoke.SmokeSeedError, match='unknown arena'):
        smoke.build_override(document, roster, smoke.assign_round_robin([58], slots), {94: 'nowhere'})
    with pytest.raises(smoke.SmokeSeedError, match='no arena profile'):
        smoke.build_override(document, roster, smoke.assign_round_robin([58], slots), {32: 'hope_snagret_pit'})
    with pytest.raises(smoke.SmokeSeedError, match='not in the placement document'):
        smoke.build_override(document, roster, {12345: 58})


def test_generate_honours_override_exactly(document, roster):
    """The real bridge binds precisely the requested (slot, species) pairs."""
    from randomizer.seed import generate, validate
    slots = smoke.pick_slots(smoke.ordinary_slots(document, 'foh'), 4, near_start=True,
                             positions=smoke.slot_positions())
    assignments = smoke.assign_round_robin([58, 32], slots)
    bosses = {94: 'hope_snagret_pit'}
    override = smoke.build_override(document, roster, assignments, bosses)
    manifest = generate('smoke-test', 'solo', 'Player1', starting_area='forest', p2_enemies=True,
                        p2_placement=override, p2_species=smoke.species_pool(assignments, bosses),
                        goal_mode='emperor_bulblax', combined_captain=True, progressive_maturity=True)
    validate(manifest)
    bound = smoke.check_layout(manifest, assignments, bosses, document)
    assert bound == {**assignments, 295337326: 94}
    assert manifest['profile'] == 'foh-day2'
    # 58 lands on FoH slots the committed document never accepts for it.
    for uid, sid in assignments.items():
        if sid == 58:
            assert uid not in (1787125272, 613834665)


def test_check_layout_reports_drift(document):
    manifest = {'p2_layout': {'bindings': [{'target': '2506165730', 'source_id': 32, 'enum_name': 'Demon'}]}}
    with pytest.raises(smoke.SmokeSeedError, match='wanted 58'):
        smoke.check_layout(manifest, {2506165730: 58}, {}, document)


def test_stage_content_reuses_cache_and_extracts_only_missing(tmp_path):
    manifest = {'p2_layout': {'bindings': [
        {'target': '1', 'source_id': 58, 'enum_name': 'BombSarai'},
        {'target': '2', 'source_id': 32, 'enum_name': 'Demon'},
        {'target': '3', 'source_id': 94, 'enum_name': 'DangoMushi'},
    ]}}
    cache = tmp_path / 'cache'
    (cache / 'BombSarai').mkdir(parents=True)
    (cache / 'BombSarai' / 'identity.json').write_text('{}')
    content = tmp_path / 'content'
    (content / 'Demon').mkdir(parents=True)
    (content / 'Demon' / 'demon.json').write_text('{}')
    copies = []

    def copy(src, dst):
        copies.append((Path(src).name, Path(dst)))
        Path(dst).mkdir(parents=True, exist_ok=True)
        (Path(dst) / 'copied').write_text('1')

    calls = []

    def prepare_fn(iso, out, wanted):
        calls.append((iso, Path(out), list(wanted)))
        (Path(out) / 'DangoMushi').mkdir(parents=True)
        (Path(out) / 'DangoMushi' / 'dangomushi.json').write_text('{}')
        return {'extracted_enums': ['DangoMushi']}

    summary = smoke.stage_content(manifest, content, cache, 'fake.iso', prepare_fn=prepare_fn, copy=copy)
    assert summary['reused'] == ['Demon']
    assert summary['from_cache'] == ['BombSarai']
    assert summary['missing_ids'] == [94] and summary['extracted'] == ['DangoMushi']
    assert calls == [('fake.iso', content, [94])]
    # BombSarai copied cache -> content; DangoMushi copied content -> cache.
    assert ('BombSarai', content / 'BombSarai') in copies
    assert ('DangoMushi', cache / 'DangoMushi') in copies
    # Nothing missing and no ISO: fine. Missing and no ISO: clear error.
    again = smoke.stage_content(manifest, content, cache, None, prepare_fn=prepare_fn, copy=copy)
    assert again['missing_ids'] == [] and len(calls) == 1
    with pytest.raises(smoke.SmokeSeedError, match='no --iso'):
        smoke.stage_content({'p2_layout': {'bindings': [{'target': '9', 'source_id': 41, 'enum_name': 'Fuefuki'}]}},
                            tmp_path / 'other', cache, None, prepare_fn=prepare_fn, copy=copy)


def test_launcher_sets_env_and_runs_randomizer(tmp_path):
    text = smoke.launcher_text(tmp_path / 's.json', tmp_path / 'content', tmp_path / 'actors.json',
                               tmp_path, r'C:\x\nectar.exe', smoke.DEFAULT_ASSETS)
    assert "$env:PIKMIN_P2_SMOKE_ANY_SLOT = '1'" in text
    assert 'py -3.12 -m randomizer run' in text
    assert '--p2-content' in text and '--p2-actors' in text and '--session-dir $session' in text
    assert "Remove-Item Env:PIKMIN_P2_SMOKE_ANY_SLOT" in text
    assert "Push-Location '" + str(smoke.ROOT) + "'" in text


def test_ordinary_slots_can_drop_slots_gated_behind_a_later_day(document):
    every = smoke.ordinary_slots(document, 'foh')
    day2 = smoke.ordinary_slots(document, 'foh', max_first_day=smoke.START_DAY)
    assert day2 and len(day2) < len(every)
    assert all(int(s.get('first_day', 0)) <= smoke.START_DAY for s in day2)
    assert {s['uid'] for s in day2} <= {s['uid'] for s in every}
    assert smoke.ordinary_slots(document, 'foh', max_first_day=99) == every


def test_pick_uids_names_exact_ordinary_slots(document):
    slots = smoke.ordinary_slots(document, 'foh', max_first_day=smoke.START_DAY)
    want = [int(slots[3]['uid']), int(slots[1]['uid'])]
    picked = smoke.pick_uids(slots, want)
    assert [int(s['uid']) for s in picked] == want
    with pytest.raises(smoke.SmokeSeedError):
        smoke.pick_uids(slots, [12345])
    assert smoke.parse_uids('1, 2') == [1, 2]
    for bad in ('', 'x', '1,1'):
        with pytest.raises(smoke.SmokeSeedError):
            smoke.parse_uids(bad)


def test_landing_is_the_measured_captain_start_not_the_origin():
    assert smoke.LANDING['foh'] != smoke.LANDING_XZ
    assert smoke.parse_landing('-464, 1967') == (-464.0, 1967.0)
    with pytest.raises(smoke.SmokeSeedError):
        smoke.parse_landing('nope')


def test_launcher_sets_and_clears_extra_env(tmp_path):
    text = smoke.launcher_text(tmp_path / 's.json', tmp_path / 'content', tmp_path / 'actors.json',
                               tmp_path, r'C:\x\nectar.exe', smoke.DEFAULT_ASSETS,
                               extra_env={'PIKMIN_P2_KING_WAKE_RANGE': '400'})
    assert "$env:PIKMIN_P2_KING_WAKE_RANGE = '400'" in text
    assert "Remove-Item Env:PIKMIN_P2_KING_WAKE_RANGE" in text
    assert text.index("$env:PIKMIN_P2_KING_WAKE_RANGE") < text.index('Push-Location')
    plain = smoke.launcher_text(tmp_path / 's.json', tmp_path / 'content', tmp_path / 'actors.json',
                                tmp_path, r'C:\x\nectar.exe', smoke.DEFAULT_ASSETS)
    assert 'PIKMIN_P2_KING_WAKE_RANGE' not in plain


def test_parse_env_validates():
    assert smoke.parse_env(['A_B=1', 'C=x=y']) == {'A_B': '1', 'C': 'x=y'}
    assert smoke.parse_env(None) == {}
    for bad in ('NOEQUALS', '=v', '1BAD=v', 'A-B=v', smoke.SMOKE_ENV + '=1'):
        with pytest.raises(smoke.SmokeSeedError):
            smoke.parse_env([bad])


def test_cli_rejects_bad_slots(tmp_path):
    with pytest.raises(SystemExit):
        smoke.main(['--area', 'foh', '--slots', 'two', '--species', '58', '--seed', 's', '--out', str(tmp_path)])


def test_landing_origins_match_the_stage_generator_headers():
    # #958: the captain start of every area is the x/z the stage default.gen header stores
    # at bytes 4..16; the smoke seed's measured LANDING table must agree with the retail assets.
    import struct
    stages = Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets/dataDir/stages')
    if not stages.is_dir():
        pytest.skip('local retail assets absent')
    for area, folder in (('impact', 'practice'), ('foh', 'stage1'), ('navel', 'stage2'), ('spring', 'stage3')):
        x, _, z = struct.unpack_from('>3f', (stages / folder / 'default.gen').read_bytes(), 4)
        assert smoke.LANDING[area] == pytest.approx((x, z), abs=1.0), area
