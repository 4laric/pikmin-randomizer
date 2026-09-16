"""Observer/negative tests for the MiniHoudai78 correlated birth (lane muse-groink, #500).

Pure marker predicates over log text: no native root or assets required.
Every PASS check must flip when its marker is stripped or disagreed, so the
observer can never report a natural generated birth from a log that did not
actually resolve, place, bind, and fire it.
"""
from experimental.pikmin2_muse_groink import (
    bound_generators,
    correlated_birth,
    muse_contract,
    pedestal_confusion,
    placement_slots,
    seed_targets,
    shell_corridor,
)

GENERATOR = '201001'
UID = '5465461'

FULL = (
    'P2_PLACEMENT_PROBE actors=1 evidence_slots=1\n'
    'P2_SEED_RESOLVE source_id=78 target=5465461 original_type=3 x=-150.0 z=1850.0\n'
    'P2_PLACEMENT_SLOT generator=201001 slot=5465461 actor=3 xyz=1 terrain=ground route=1 x=-150.0 y=30.0 z=1850.0 water_depth=0.00\n'
    'P2_GROINK_CARCASS_READY generator=201001 type=0 gauge_delay=2.000 recovery=3.000 max_health=1200.000\n'
    'P2_GROINK_CARCASS_BECOME generator=201001 pos=-150.000,0.000,1850.000 face_dir=0.000\n'
    'P2_GROINK_ATTACK_FIRE tick=42 frame=26.0 cycle=0 emitted=3\n'
    'P2_GROINK_FLIGHT_SWEEP_PASS steps=90 hits=0 wind=0\n'
    'P2_GROINK_STRIKE_PASS hits=6 deaths=1 health_start=25.000 health_end=0.000 placement=fixture_pinned\n'
)


def test_full_log_passes_gate1():
    checks = correlated_birth(FULL, GENERATOR)
    assert checks['gate1'] is True
    assert all(value is True for value in checks.values())


def test_missing_resolve_flips():
    log = FULL.replace('P2_SEED_RESOLVE source_id=78', 'P2_SEED_RESOLVE source_id=99')
    checks = correlated_birth(log, GENERATOR)
    assert checks['seed_resolve'] is False
    assert checks['slot_agrees'] is False
    assert checks['gate1'] is False


def test_slot_uid_disagreement_flips():
    log = FULL.replace('slot=5465461', 'slot=5465462')
    checks = correlated_birth(log, GENERATOR)
    assert checks['seed_resolve'] is True
    assert checks['slot_agrees'] is False
    assert checks['gate1'] is False


def test_frog_only_bind_is_not_a_birth():
    # Legacy l21 shape: carcass markers on the Frog vehicle but no
    # seed resolve and no placement slot agreement.
    log = (
        'P2_GROINK_CARCASS_READY generator=201001 type=0 gauge_delay=2.000 recovery=3.000 max_health=1200.000\n'
        'P2_GROINK_CARCASS_BECOME generator=201001 pos=-150.000,0.000,1850.000 face_dir=0.000\n'
    )
    checks = correlated_birth(log, GENERATOR)
    assert checks['actor_bound'] is True
    assert checks['gate1'] is False


def test_ready_without_become_is_not_born():
    log = FULL.replace('P2_GROINK_CARCASS_BECOME generator=201001', 'P2_GROINK_CARCASS_UNBOUND generator=201001')
    assert GENERATOR not in bound_generators(log)
    assert correlated_birth(log, GENERATOR)['gate1'] is False


def test_corridor_fire_required():
    log = '\n'.join(line for line in FULL.splitlines()
                    if 'P2_GROINK_ATTACK_FIRE' not in line) + '\n'
    checks = correlated_birth(log, GENERATOR)
    assert checks['corridor_fire'] is False
    assert checks['gate1'] is False


def test_corridor_sweep_required():
    log = '\n'.join(line for line in FULL.splitlines()
                    if 'SWEEP_PASS' not in line and 'STRIKE_PASS' not in line) + '\n'
    corridor = shell_corridor(log)
    assert corridor == {'attack_fire': True, 'sweep_or_strike': False}
    assert correlated_birth(log, GENERATOR)['gate1'] is False


def test_corridor_alone_never_closes_gate1():
    log = (
        'P2_GROINK_ATTACK_FIRE tick=42 frame=26.0 cycle=0 emitted=3\n'
        'P2_GROINK_STRIKE_PASS hits=6 deaths=1 health_start=25.000 health_end=0.000 placement=fixture_pinned\n'
    )
    assert correlated_birth(log, GENERATOR)['gate1'] is False


def test_pedestal_97_claim_rejected_for_78():
    log = FULL.replace('P2_SEED_RESOLVE source_id=78', 'P2_SEED_RESOLVE source_id=97')
    assert correlated_birth(log, GENERATOR, source_id=78)['gate1'] is False
    assert pedestal_confusion(log, GENERATOR) is True
    # A 97 resolve is some other lane's gate, never ours.
    assert correlated_birth(log, GENERATOR, source_id=97)['seed_resolve'] is True


def test_no_pedestal_confusion_on_clean_78_log():
    assert pedestal_confusion(FULL, GENERATOR) is False
    assert seed_targets(FULL) == [UID]
    assert placement_slots(FULL) == {GENERATOR: UID}


def test_muse_contract_positive_control():
    log = (
        'P2_MUSE_GROINK_SIDECAR generator=201001 type=0\n'
        'P2_MUSE_GROINK_SLOT generator=201001 slot=5465461\n'
        'P2_MUSE_GROINK_RESOLVE source_id=78 target=5465461\n'
        'P2_MUSE_GROINK_BIRTH_POLICY births=1 timer_done=1\n'
        'PASS MUSE_GROINK_CORRELATED\n'
    )
    assert muse_contract(log, GENERATOR)['contract'] is True


def test_muse_contract_disagreement_flips():
    log = (
        'P2_MUSE_GROINK_SIDECAR generator=201001 type=0\n'
        'P2_MUSE_GROINK_SLOT generator=201001 slot=5465462\n'
        'P2_MUSE_GROINK_RESOLVE source_id=78 target=5465461\n'
        'P2_MUSE_GROINK_BIRTH_POLICY births=1 timer_done=1\n'
        'FAIL MUSE_GROINK_CORRELATED reason=slot_disagree\n'
    )
    checks = muse_contract(log, GENERATOR)
    assert checks['slot_agrees'] is False
    assert checks['contract'] is False
