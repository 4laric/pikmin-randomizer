"""Observer/negative tests for the MiniHoudai78 correlated birth (lane muse-groink, #500).

Pure marker predicates over log text: no native root or assets required.
Every PASS check must flip when its marker is stripped or disagreed, so the
observer can never report a natural generated birth from a log that did not
actually resolve, bind, place, and birth it on the accepted slot (328297937).

Generation 2 contract: the resolve/bind leg goes through the reviewed
muse-placement observer, so a ``bound=0`` refusal or a non-accepted slot
fails the join. The shell corridor is support-only evidence, never gating.
"""
from experimental.pikmin2_muse_groink import (
    ACCEPTED_SLOT,
    bound_generators,
    correlated_birth,
    muse_contract,
    pedestal_confusion,
    placement_slots,
    seed_targets,
    shell_corridor,
)

GENERATOR = '201078'
UID = '328297937'

assert ACCEPTED_SLOT == 328297937

FULL = (
    'P2_PLACEMENT_PROBE actors=1 evidence_slots=1\n'
    'P2_SEED_RESOLVE source_id=78 target=328297937 original_type=0 x=-150.0 z=1850.0\n'
    'P2_GENERATED_PLACEMENT source_id=78 target=328297937 generator=201078 bound=1\n'
    'P2_PLACEMENT_SLOT generator=201078 slot=328297937 actor=0 xyz=1 terrain=ground route=1 x=-150.0 y=30.0 z=1850.0 water_depth=0.00\n'
    'P2_GROINK_CARCASS_READY generator=201078 type=0 gauge_delay=2.000 recovery=3.000 max_health=1200.000\n'
)


def test_full_log_passes_gate1():
    checks = correlated_birth(FULL, GENERATOR)
    assert checks['gate1'] is True
    assert checks['seed_resolve'] is True
    assert checks['native_bound'] is True
    assert checks['resolve_bind_correlated'] is True
    assert checks['refusal_reason'] is None
    assert checks['slot_agrees'] is True
    assert checks['sidecar_ready'] is True
    # No death in a spawn-only log: reported, never gating.
    assert checks['carcass_began'] is False


def test_missing_resolve_flips():
    log = FULL.replace('P2_SEED_RESOLVE source_id=78', 'P2_SEED_RESOLVE source_id=99')
    checks = correlated_birth(log, GENERATOR)
    assert checks['seed_resolve'] is False
    assert checks['resolve_bind_correlated'] is False
    assert checks['gate1'] is False


def test_missing_bind_marker_flips():
    log = '\n'.join(line for line in FULL.splitlines()
                    if 'P2_GENERATED_PLACEMENT' not in line) + '\n'
    checks = correlated_birth(log, GENERATOR)
    assert checks['native_bound'] is False
    assert checks['gate1'] is False


def test_bind_refusal_fails_closed():
    log = FULL.replace('bound=1', 'bound=0 reason=slot-rejected')
    checks = correlated_birth(log, GENERATOR)
    assert checks['native_bound'] is False
    assert checks['refusal_reason'] == 'slot-rejected'
    assert checks['gate1'] is False


def test_non_accepted_slot_fails():
    log = FULL.replace('target=328297937', 'target=5465461').replace(
        'slot=328297937', 'slot=5465461')
    checks = correlated_birth(log, GENERATOR)
    assert checks['resolve_bind_correlated'] is False
    assert checks['refusal_reason'] == 'slot-not-accepted'
    assert checks['gate1'] is False


def test_slot_uid_disagreement_flips():
    log = FULL.replace('slot=328297937', 'slot=328297938')
    checks = correlated_birth(log, GENERATOR)
    assert checks['seed_resolve'] is True
    assert checks['resolve_bind_correlated'] is True
    assert checks['slot_agrees'] is False
    assert checks['gate1'] is False


def test_frog_only_bind_is_not_a_birth():
    # Legacy l21 shape: carcass markers on the vehicle but no seed resolve,
    # no native bind and no placement slot agreement.
    log = (
        'P2_GROINK_CARCASS_READY generator=201078 type=0 gauge_delay=2.000 recovery=3.000 max_health=1200.000\n'
        'P2_GROINK_CARCASS_BECOME generator=201078 pos=-150.000,0.000,1850.000 face_dir=0.000\n'
    )
    checks = correlated_birth(log, GENERATOR)
    assert checks['sidecar_ready'] is True
    assert checks['carcass_began'] is True
    assert checks['gate1'] is False


def test_ready_without_become_is_not_begun():
    assert GENERATOR not in bound_generators(FULL)
    assert correlated_birth(FULL, GENERATOR)['gate1'] is True
    begun = FULL + ('P2_GROINK_CARCASS_BECOME generator=201078 pos=-150.000,0.000,1850.000 face_dir=0.000\n')
    assert GENERATOR in bound_generators(begun)
    assert correlated_birth(begun, GENERATOR)['gate1'] is True


def test_missing_sidecar_ready_flips():
    log = '\n'.join(line for line in FULL.splitlines()
                    if 'P2_GROINK_CARCASS_READY' not in line) + '\n'
    checks = correlated_birth(log, GENERATOR)
    assert checks['sidecar_ready'] is False
    assert checks['gate1'] is False


def test_corridor_is_support_only():
    # A natural product birth carries no volley markers; the corridor is
    # reported, never gating.
    corridor = shell_corridor(FULL)
    assert corridor == {'attack_fire': False, 'sweep_or_strike': False}
    assert correlated_birth(FULL, GENERATOR)['gate1'] is True
    volley = FULL + ('P2_GROINK_ATTACK_FIRE tick=42 frame=26.0 cycle=0 emitted=3\n'
                     'P2_GROINK_STRIKE_PASS hits=6 deaths=1 health_start=25.000 health_end=0.000 placement=fixture_pinned\n')
    assert correlated_birth(volley, GENERATOR)['gate1'] is True


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


def test_no_pedestal_confusion_on_clean_78_log():
    assert pedestal_confusion(FULL, GENERATOR) is False
    assert seed_targets(FULL) == [UID]
    assert placement_slots(FULL) == {GENERATOR: UID}


def test_muse_contract_positive_control():
    log = (
        'P2_MUSE_GROINK_SIDECAR generator=201078 type=0\n'
        'P2_MUSE_GROINK_SLOT generator=201078 slot=328297937\n'
        'P2_MUSE_GROINK_RESOLVE source_id=78 target=328297937\n'
        'P2_MUSE_GROINK_BIRTH_POLICY births=1 timer_done=1\n'
        'PASS MUSE_GROINK_CORRELATED\n'
    )
    assert muse_contract(log, GENERATOR)['contract'] is True


def test_muse_contract_disagreement_flips():
    log = (
        'P2_MUSE_GROINK_SIDECAR generator=201078 type=0\n'
        'P2_MUSE_GROINK_SLOT generator=201078 slot=328297938\n'
        'P2_MUSE_GROINK_RESOLVE source_id=78 target=328297937\n'
        'P2_MUSE_GROINK_BIRTH_POLICY births=1 timer_done=1\n'
        'FAIL MUSE_GROINK_CORRELATED reason=slot_disagree\n'
    )
    checks = muse_contract(log, GENERATOR)
    assert checks['slot_agrees'] is False
    assert checks['contract'] is False
