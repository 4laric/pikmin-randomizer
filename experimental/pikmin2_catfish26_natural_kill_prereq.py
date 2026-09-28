"""Catfish26 (Water Dumple, source ID 26) natural-kill prerequisite pin-discovery.

Issue #800, lane catfish26-natural-kill-prereq-discovery (enemies-5 cycle 34
recovery for the blocked observer #783). Diagnosis only: this module reads a
plain dict of observed inputs and returns an adjudicated producer decision with
file:line citations. It never edits engine/source, builds, launches or claims
gameplay acceptance; it fails closed on missing or malformed inputs.

Copyright-free helper text; no external dependencies.
"""
from __future__ import annotations

import json

# Read-only source anchors (verified this turn; the catfish module lives in the
# family private native trees, not the maintained native/ checkout).
ANCHORS = {
    "poison_apply": "native/pc_port/pc_p2_catfish.cpp:374-393 swallowEvent applies proper fp02=300 (actor->mHealth -= result.poisonDamage)",
    "poison_gate": "native/pc_port/pc_p2_catfish.cpp:379 pc_p2_is_white(p) gates the poison to a swallowed White Pikmin",
    "host_adaptation": "native/pc_port/pc_p2_catfish.cpp:12-20 P2 two-slot mouth not representable on the P1 host; explicit capture + InteractKill",
    "host_stick": "native/pc_port/pc_p2_catfish.cpp:221-243 doFlick walks a->mStickListHead / isStickToMouth, but the port body is not Pikmin-stickable",
    "white_gate": "native/pc_port/pc_p2_white.cpp:47 pc_p2_is_white requires pc_p2_whites_enabled()",
    "white_setup": "native/pc_port/pc_p2_white.cpp:59-77 pc_p2_white_setup requires p2-white.txt (62) and white_* room models (70,76)",
    "white_membership": "native/CMakeLists.txt:176-177 pc_p2_white.cpp + pc_p2_white_poison.cpp are compiled",
    "aquatic_species": "experimental/pikmin2_aquatic_assets.py:32 SPECIES = Catfish/Tadpole/Jigumo/UmiMushi (no White)",
    "aquatic_install_refuse": "experimental/pikmin2_aquatic_install.py:201 refuses existing/conflicting installation; only manifest species are staged",
}

PRODUCER_RECEIVER = "catfish26-stickable-receiver-native"
PRODUCER_WHITE = "white-pikmin-staging"

REQUIRED = {
    "poison_implemented": bool,
    "white_sidecar_present": bool,
    "white_models_present": bool,
    "catfish_module_available": bool,
    "catfish_module_in_maintained": bool,
    "catfish_module_in_cmake": bool,
}


class PrereqError(ValueError):
    """Fail-closed refusal."""


def _validate(inputs):
    if not isinstance(inputs, dict):
        raise PrereqError("inputs must be a mapping")
    for key, kind in REQUIRED.items():
        if key not in inputs:
            raise PrereqError("missing input: " + key)
        if type(inputs[key]) is not kind:
            raise PrereqError("wrong type for %s: expected %s" % (key, kind.__name__))
    return {k: inputs[k] for k in REQUIRED}


def adjudicate(inputs):
    """Return the exact producer decision and its executable contract.

    Deterministic and fail-closed. The White-Pikmin path is source-faithful but
    is only executable when the sidecar AND the retail white_* room models are
    present; otherwise the in-repo executable producer is the Pikmin-stickable
    Catfish receiver registration.
    """
    v = _validate(inputs)
    citations = [ANCHORS["poison_apply"], ANCHORS["poison_gate"]]
    white_path_executable = bool(v["white_sidecar_present"] and v["white_models_present"])

    if not v["poison_implemented"]:
        raise PrereqError("poison kill not implemented; prerequisite unknown")
    if white_path_executable:
        producer = PRODUCER_WHITE
        rationale = (
            "White Pikmin staging is executable: p2-white.txt and the white_* "
            "room models are present, so pc_p2_white_setup enables White and the "
            "existing swallowEvent poison closes gates 4/6 unchanged."
        )
        citations += [ANCHORS["white_setup"], ANCHORS["white_membership"]]
        blocked_on = None
    elif v["catfish_module_available"]:
        producer = PRODUCER_RECEIVER
        rationale = (
            "White Pikmin staging is blocked on the absent retail white_* room "
            "models (user-owned asset) plus the backlog species owner; the "
            "in-repo executable producer is a Pikmin-stickable Catfish receiver "
            "so latched red attacks deliver sustained damage."
        )
        citations += [ANCHORS["white_gate"], ANCHORS["white_setup"],
                      ANCHORS["host_stick"], ANCHORS["aquatic_species"], ANCHORS["aquatic_install_refuse"]]
        blocked_on = "user_asset:retail white_* room models (p2-white.txt is authorable)"
    else:
        raise PrereqError("no executable producer: White staging blocked and catfish module unavailable")

    if producer == PRODUCER_RECEIVER:
        callsites = [
            {"file": "native/pc_port/pc_p2_catfish.cpp",
             "symbol": "catfish bind/registration (add a Pikmin-stickable attack receiver on the bound Catfish)"},
            {"file": "native/pc_port/pc_p2_catfish.h", "symbol": "receiver registration declaration"},
        ]
        membership = ["native/CMakeLists.txt"]
        first_slice = (
            "Register the bound Catfish as a Pikmin-attack receiver so latched "
            "red throws deliver sustained InteractAttack damage to mHealth while "
            "preserving the KochappyBase FSM; observe P2_CATFISH_DEAD + corpse."
        )
    else:
        callsites = [
            {"file": "experimental/pikmin2_aquatic_install.py",
             "symbol": "install() stage the White Pikmin sidecar + white_* models"},
        ]
        membership = ["native/CMakeLists.txt"]
        first_slice = (
            "Author p2-white.txt from the pc_p2_white_setup schema and stage the "
            "white_* room models; then the existing swallowEvent poison closes "
            "gates 4/6 unchanged."
        )

    consumer = {
        "lane": "shard-enemies-5-catfish26-observer",
        "issue": 783,
        "command": ("re-run the guarded observer2 fixture over the batch-2 aquatic arena with red throws "
                    "(p2_muse_catfish_fixture.cpp; native pin 719160dc) and read P2_CATFISH_DEAD / "
                    "P2_CATFISH_CORPSE_READY, then the re-entry pass"),
        "expected": "one natural kill edge (P2_CATFISH_DEAD + corpse) so gates 4 and 6 can be observed",
    }
    return {
        "schema": 1,
        "decision": producer,
        "rationale": rationale,
        "blocked_on": blocked_on,
        "citations": citations,
        "producer_lane": producer,
        "callsites": callsites,
        "build_membership": membership,
        "first_executable_slice": first_slice,
        "downstream_consumer": consumer,
        "gates": {g: "UNTESTED" for g in (
            "identity_spawn", "movement_animation", "attacks_receivers",
            "death_corpse", "transport_reward", "cleanup_reentry")},
        "admit": False,
    }


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", required=True, help="JSON file of observed inputs")
    args = ap.parse_args(argv)
    inputs = json.loads(Path(args.inputs).read_text(encoding="utf-8-sig"))
    print(json.dumps(adjudicate(inputs), indent=2))


if __name__ == "__main__":
    from pathlib import Path  # noqa: E402
    main()
