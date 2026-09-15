"""Lane-10 receiver contract guard (consumer emitters).

These tests pin the source-text contract every lane-10 emitter module must
honour, so a future family-emitter cannot silently FORK the immunity matrix or
drop the accepted/immune marker pair:

  * the module really drives an elemental receiver (InteractFire/Bubble/Gas/
    Denki) rather than mutating a Pikmin state directly;
  * immunity is always derived from the receiver's own lane-11 matrix
    (``p2_emitter_accepts`` / ``p2_species_immune``), never a hardcoded species
    table;
  * the module logs both an accepted marker and an immune/rejected marker,
    under distinct names, so the accepted/immune pair stays machine-observable.

They read the lane native worktree (a separate repo) and assert by source text;
the emitter FSMs themselves are exercised by the private runtime fixture, not by
this unit suite. The per-module checks are small pure helpers over the source
text so the negative forked-matrix self-test needs no build.
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

INTERACT_ELEMENTS = ("InteractFire", "InteractBubble", "InteractGas", "InteractDenki")
MATRIX_TOKENS = ("p2_emitter_accepts(", "p2_species_immune(")

# Lane-10 consumer emitters (proven set) and their accepted/immune marker pair.
EMITTERS = [
    dict(
        rel="pc_port/pc_p2_otakara.cpp",
        accepted=("P2_OTAKARA_DISCHARGE_HIT",),
        rejected=("P2_OTAKARA_DISCHARGE_IMMUNE",),
        elements=("InteractFire", "InteractBubble", "InteractGas", "InteractDenki"),
    ),
    dict(
        rel="pc_port/pc_p2_elecbug.cpp",
        accepted=("P2_ELECBUG_DENKI",),
        rejected=("P2_ELECBUG_IMMUNE",),
        elements=("InteractDenki",),
    ),
    dict(
        rel="pc_port/pc_p2_hiba.cpp",
        accepted=("P2_HIBA_FIRE_HIT", "P2_HIBA_GAS_HIT", "P2_HIBA_DENKI_HIT"),
        rejected=("P2_HIBA_FIRE_PASS", "P2_HIBA_GAS_PASS", "P2_HIBA_DENKI_PASS"),
        elements=("InteractFire", "InteractGas", "InteractDenki"),
    ),
]


def _native():
    """Return the lane native repo root, or None when no worktree is present.

    Discovery order: ``PIKMIN_NATIVE_ROOT`` (a native repo root, probed via its
    ``pc_port/`` subdir), ``P2_NATIVE_PC_PORT`` (pointing directly at a
    ``pc_port/`` dir; the root is its parent), then ``ROOT/native/pc_port``.
    """
    root = os.environ.get("PIKMIN_NATIVE_ROOT")
    if root and (Path(root) / "pc_port" / "pc_p2_otakara.cpp").is_file():
        return Path(root).resolve()
    pc_port = os.environ.get("P2_NATIVE_PC_PORT")
    if pc_port and (Path(pc_port) / "pc_p2_otakara.cpp").is_file():
        return Path(pc_port).resolve().parent
    candidate = ROOT / "native" / "pc_port"
    if (candidate / "pc_p2_otakara.cpp").is_file():
        return candidate.resolve().parent
    return None


def _has_element(text):
    """True iff the source constructs at least one elemental receiver."""
    return any(name in text for name in INTERACT_ELEMENTS)


def _delivers(text, elements):
    """True iff the source constructs each listed elemental receiver."""
    return all(name in text for name in elements)


def _consults_matrix(text):
    """True iff immunity is derived from the lane-10..11 matrix, not forked."""
    return any(token in text for token in MATRIX_TOKENS)


def _logs_markers(text, accepted_markers, rejected_markers):
    """True iff both an accepted and an immune/rejected marker are logged."""
    return (any(marker in text for marker in accepted_markers)
            and any(marker in text for marker in rejected_markers))


def _markers_distinct(accepted_markers, rejected_markers):
    """True iff accepted and immune/rejected marker names never collide."""
    return (bool(accepted_markers) and bool(rejected_markers)
            and not (set(accepted_markers) & set(rejected_markers)))


def module_passes(text, accepted_markers, rejected_markers):
    """Pure contract check shared by the positive and negative tests."""
    return (_has_element(text)
            and _consults_matrix(text)
            and _logs_markers(text, accepted_markers, rejected_markers)
            and _markers_distinct(accepted_markers, rejected_markers))


@pytest.mark.parametrize(
    "module",
    EMITTERS,
    ids=["otakara", "elecbug", "hiba"],
)
def test_emitter_honours_receiver_contract(module):
    native = _native()
    if native is None:
        pytest.skip("lane native worktree not available")
    text = (native / module["rel"]).read_text(errors="replace")

    assert _has_element(text), "no elemental receiver token found"
    assert _delivers(text, module["elements"]), "module no longer delivers its elements"
    assert _consults_matrix(text), "immunity matrix not consulted (likely forked)"
    assert _logs_markers(text, module["accepted"], module["rejected"]), \
        "accepted/immune marker pair not logged"
    assert _markers_distinct(module["accepted"], module["rejected"]), \
        "accepted and immune markers collide"


def test_contract_rejects_forked_matrix():
    fake = (
        "void forked_emit(Creature* owner, Piki* p) {\n"
        "    p->stimulate(InteractGas(owner, 1.0f));\n"
        '    std::printf("P2_FAKE_HIT applied=1\\n");\n'
        "}\n"
    )
    accepted = ("P2_FAKE_HIT",)
    rejected = ()

    assert _has_element(fake)
    assert not _consults_matrix(fake)
    assert not _logs_markers(fake, accepted, rejected)
    assert not _markers_distinct(accepted, rejected)
    assert module_passes(fake, accepted, rejected) is False
