"""Lane 05 slice 4: seed-to-native evidence markers flip when a bank/READY line is stripped.

Pure marker predicates over a native log: no native root or assets required. A
stripped ``P2_*_BANK`` or ``P2_ENEMY_READY`` line must flip its check, so the
evidence a probe reports can never pass on a log that did not actually load the
staged bank or bind the seed's identity.
"""
from experimental.pikmin2_seed_evidence import (
    cohort_markers, ready_species, resolve_markers)

BASE = (
    '[PC Port] Experimental preview window set to 960x540 windowed and centered\n'
    '[PC Generator] default: read 25 generators, 25 fully recognised\n'
    'P2_SNOW_BANK poses=60 mod_bytes=960000 texture_attach_calls=1 load_seconds=0.020\n'
    'P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=5001 behavior=P1\n'
    'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 health=250.0\n'
    'P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000 texture_attach_calls=1 load_seconds=0.021\n'
)


def test_full_log_passes_all_markers():
    assert all(cohort_markers(BASE).values())


def test_dwarf_bank_line_flips():
    assert cohort_markers(BASE)['dwarf_bank'] is True
    assert cohort_markers(BASE.replace('P2_DWARF_ORANGE_BANK', 'P2_OTHER_BANK'))['dwarf_bank'] is False


def test_snow_bank_line_flips():
    assert cohort_markers(BASE)['snow_bank'] is True
    assert cohort_markers(BASE.replace('P2_SNOW_BANK', 'P2_OTHER_BANK'))['snow_bank'] is False


def test_dwarf_ready_line_flips():
    assert cohort_markers(BASE)['dwarf_ready'] is True
    assert cohort_markers(BASE.replace('source_id=44', 'source_id=99'))['dwarf_ready'] is False


def test_snow_ready_line_flips():
    assert cohort_markers(BASE)['snow_ready'] is True
    assert cohort_markers(remove_line(BASE, 'species=YellowKochappy native_family'))['snow_ready'] is False


def test_roster_read_is_not_stock():
    assert cohort_markers(BASE)['roster_curated'] is True
    assert cohort_markers(BASE.replace('25 generators', '80 generators'))['roster_curated'] is False


def test_missing_room_file_flips():
    assert cohort_markers(BASE)['no_missing_room'] is True
    assert cohort_markers(BASE + 'FAILED to open assets/dataDir/courses/pikmin2room/snow_00.mod\n')['no_missing_room'] is False


def test_ready_species_order():
    assert ready_species(BASE) == ['YellowKochappy', 'BlueKochappy']


def remove_line(text, needle):
    return '\n'.join(line for line in text.splitlines() if needle not in line) + '\n'


RESOLVE_BASE = (
    'P2_PLACEMENT_PROBE actors=2 evidence_slots=2\n'
    'P2_SEED_RESOLVE source_id=45 target=843459898 original_type=3 x=-150.0 z=1700.0\n'
    'P2_PLACEMENT_SLOT generator=5001 slot=843459898 actor=3 xyz=1 terrain=ground route=1 x=-150.0 y=30.0 z=1700.0 water_depth=0.00\n'
    'P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=5001 behavior=P1\n'
    'P2_SEED_RESOLVE source_id=44 target=5465461 original_type=3 x=-150.0 z=1850.0\n'
    'P2_PLACEMENT_SLOT generator=211001 slot=5465461 actor=3 xyz=1 terrain=ground route=1 x=-150.0 y=30.0 z=1850.0 water_depth=0.00\n'
    'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 health=250.0\n'
)
GENERATORS = {44: 211001, 45: 5001}


def test_resolve_markers_pass():
    assert all(resolve_markers(RESOLVE_BASE, [44, 45], GENERATORS).values())


def test_seed_resolve_flips():
    marks = resolve_markers(RESOLVE_BASE, [44, 45], GENERATORS)
    assert marks['seed_resolve_BlueKochappy'] is True
    stripped = resolve_markers(RESOLVE_BASE.replace('P2_SEED_RESOLVE source_id=44', 'P2_SEED_RESOLVE source_id=99'), [44, 45], GENERATORS)
    assert stripped['seed_resolve_BlueKochappy'] is False
    assert stripped['slot_agree_BlueKochappy'] is False


def test_placement_slot_flips():
    marks = resolve_markers(RESOLVE_BASE, [44, 45], GENERATORS)
    assert marks['slot_agree_BlueKochappy'] is True
    stripped = resolve_markers(RESOLVE_BASE.replace('P2_PLACEMENT_SLOT generator=211001', 'P2_PLACEMENT_SLOT generator=211002'), [44, 45], GENERATORS)
    assert stripped['slot_agree_BlueKochappy'] is False


def test_out_of_cohort_emits_no_resolve():
    only44 = remove_line(RESOLVE_BASE, 'target=843459898')
    only44 = remove_line(only44, 'generator=5001')
    marks = resolve_markers(only44, [44], GENERATORS)
    assert marks['seed_resolve_BlueKochappy'] is True
    assert marks['no_seed_resolve_YellowKochappy'] is True
    assert marks['no_placement_slot_YellowKochappy'] is True
