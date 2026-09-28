"""Pytest for Fuefuki gate-1 natural-spawn receipt (source 41)."""
from experimental.pikmin2_fuefuki_spawn_receipt import parse

GEN = 245001


def canonical_log():
    return "\n".join(
        [
            "P2_PLACEMENT_SLOT x=10.0 y=0.0 z=20.0 terrain=ground route=a generator=245001",
            "P2_SEED_RESOLVE source_id=41 target=245001",
            "P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=245001 type=11",
        ]
    ) + "\n"


def test_canonical_log_gate1_ok():
    receipt = parse(canonical_log())
    assert receipt["placement"] is True
    assert receipt["seed_resolve_41"] is True
    assert receipt["native_ready"] is True
    assert receipt["generator"] == 245001
    assert receipt["same_generator"] is True
    assert receipt["gate1_ok"] is True


def test_truncated_no_native_log():
    text = "\n".join(
        [
            "P2_PLACEMENT_SLOT x=10.0 y=0.0 z=20.0 terrain=ground route=a generator=245001",
            "P2_SEED_RESOLVE source_id=41 target=245001",
        ]
    ) + "\n"
    receipt = parse(text)
    assert receipt["placement"] is True
    assert receipt["seed_resolve_41"] is True
    assert receipt["native_ready"] is False
    assert receipt["gate1_ok"] is False


def test_mismatched_generators():
    text = "\n".join(
        [
            "P2_PLACEMENT_SLOT x=10.0 y=0.0 z=20.0 terrain=ground route=a generator=245001",
            "P2_SEED_RESOLVE source_id=41 target=245002",
            "P2_FUEFUKI_TEKI_DEAD generator=245003",
        ]
    ) + "\n"
    receipt = parse(text)
    assert receipt["placement"] is True
    assert receipt["seed_resolve_41"] is True
    assert receipt["native_ready"] is True
    assert receipt["same_generator"] is False
    assert receipt["gate1_ok"] is False
