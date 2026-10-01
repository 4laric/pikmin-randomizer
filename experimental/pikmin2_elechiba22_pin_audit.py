"""ElecHiba source-22 admission pin audit (#816, shard enemies-1).

Read-only inventory of the source-22 ElecHiba binding/admission path.
Pure-python predicates over file text so the audit runs without a native
build; the verdicts below were produced against the maintained wave
(claude/p2-deepseek-wave-native) and main.

Headline finding: ElecHiba (22) is a FIXED HAZARD (electrical wire), not an
actor. Its admission path is the lane-22 hiba sidecar
(pc_port/pc_p2_hiba.{h,cpp}, pc_p2_hiba_policy.h), gated on
p2-hiba-native.txt, delivering InteractDenki through the lane-10/11 receiver
contracts. There is no pc_p2_elechiba.* family module anywhere, so the
ElecBug28 delivery-bridge pattern (bind/forget + Onion receipt) is
inapplicable by category, not merely unimplemented.
"""

import re

HIBA_HEADER = "pc_port/pc_p2_hiba.h"
HIBA_SOURCE = "pc_port/pc_p2_hiba.cpp"
HIBA_POLICY = "pc_port/pc_p2_hiba_policy.h"
ELECBUG_HEADER = "pc_port/pc_p2_elecbug.h"

ELEC_HIBA_SYMBOLS = (
    "pc_p2_hiba_setup",
    "pc_p2_hiba_denki_hit_seen",
    "pc_p2_hiba_denki_immune_seen",
    "pc_p2_hiba_denki_lethal",
)

ELECBUG_SYMBOLS = (
    "pc_p2_elecbug_setup",
    "pc_p2_elecbug_forget",
)


def find_symbols(text, symbols):
    """Map each symbol to True when its word-boundary occurrence exists."""
    if not isinstance(text, str):
        raise ValueError("text must be str")
    return {name: re.search(r"\b" + re.escape(name) + r"\b", text) is not None
            for name in symbols}


def classify_admission(header_text):
    """Classify the admission category from a family header's text.

    Returns one of: 'fixed-hazard-sidecar', 'actor-family-module', 'absent'.
    Raises ValueError on non-str input (fail closed).
    """
    if not isinstance(header_text, str):
        raise ValueError("header_text must be str")
    if not header_text.strip():
        return "absent"
    if "fixed-hazard" in header_text or "fixed hazard" in header_text:
        return "fixed-hazard-sidecar"
    if "BTeki" in header_text or "family-owned" in header_text:
        return "actor-family-module"
    return "absent"


def delivery_bridge_applicable(classification):
    """Only actor-family modules can take the ElecBug28 delivery bridge."""
    if classification not in ("fixed-hazard-sidecar", "actor-family-module", "absent"):
        raise ValueError("unknown classification: %r" % (classification,))
    return classification == "actor-family-module"


def audit_record(wave_header, main_present):
    """Build the JSON-serializable audit verdict for source 22."""
    symbols = find_symbols(wave_header, ELEC_HIBA_SYMBOLS)
    classification = classify_admission(wave_header)
    return {
        "source_id": 22,
        "identity": "ElecHiba",
        "binding_path": [HIBA_HEADER, HIBA_SOURCE, HIBA_POLICY],
        "symbols_present": symbols,
        "classification": classification,
        "delivery_bridge_applicable": delivery_bridge_applicable(classification),
        "in_maintained_main": bool(main_present),
        "producer": {"lane": 22, "issues": [170, 447], "note": "no live registry lane owns #170/#447"},
        "blocker": None if main_present else "module wave-only; needs integrator landing, not a new family module",
    }
