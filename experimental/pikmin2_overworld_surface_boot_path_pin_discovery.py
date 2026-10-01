"""Overworld surface boot-path pin discovery (lane provider-overworld-surface-boot-path-pin-discovery, #707).

Machine-readable registry of exact pins or explicit ABSENT verdicts for the
shared P2 overworld surface runtime path that blocks tutorial #696/#148 and
its siblings #660/#149, #150, #151. Root-only tooling: no source/shared/
family/native edits, no builds, no runtime. Stdlib only.

The four generic #132 native integration items (sunset driver, save
serializer, receipt ledger endpoint, generator-cache restore) were pinned by
#658 and are EXPLICITLY EXCLUDED here (recorded as excluded, not re-audited).
"""
import argparse
import hashlib
import json
import sys

SCHEMA = "p2-overworld-surface-boot-path-1"
ROOT_BASE = "c86e4029fc654f3548c47d858bd80b402b9977fd"
NATIVE_PIN = "b805d9c626e4f4558c95aef7cac311a5d9a2068f"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

EXCLUDED_132 = (
    "native sunset driver",
    "native save serializer",
    "native receipt ledger endpoint",
    "native generator-cache restore",
)

DOWNSTREAM = (696, 148, 660, 149, 150, 151)

ITEMS = (
    {
        "key": "course_boot",
        "question": "pc_port overworld course boot / surface entry path",
        "status": "ABSENT",
        "evidence": [
            "b805d9c6:pc_port/pc_bbft.cpp:44 --experimental-pikmin2-room (room preview only)",
            "b805d9c6:pc_port/pc_bbft.cpp:47 --experimental-challenge-level 0-4 (P1 challenge only)",
            "no overworld course boot flag exists in the pc_port boot-flag dispatch",
        ],
        "owner": None,
        "review_186": {
            "request": "Shared-native overworld course boot flag + stage-table registration",
            "scope": "New boot flag selecting a P2 overworld course with its decoded stage table; must not collide with --experimental-pikmin2-room or --experimental-challenge-level semantics",
        },
    },
    {
        "key": "day_trigger",
        "question": "day-advance / surface-transition trigger",
        "status": "ABSENT",
        "evidence": [
            "b805d9c6:pc_port/pc_p2_cave.cpp:220 gameflow.mWorldClock.setTime(...) is cave-internal only",
            "no day-advance trigger, surface-transition trigger, or sunset driver call path exists in pc_port",
            "c86e4029:experimental/pikmin2_surface_session_contract.py:57-60 MISSING_INTEGRATION names the native sunset driver as missing",
        ],
        "owner": None,
        "review_186": {
            "request": "Shared-native day-advance / surface-transition trigger",
            "scope": "Engine call path advancing the surface day clock and snapshotting time_of_day, mirroring the contract day-advance/sunset semantics",
        },
    },
    {
        "key": "exit_reentry",
        "question": "exit / re-entry (stage boundary) path for overworld surfaces",
        "status": "ABSENT",
        "evidence": [
            "b805d9c6:pc_port/pc_p2_cave.cpp:145 pc_p2_cave_request, :146 pc_p2_cave_interact, :154 pc_p2_cave_checkpoint are cave-only",
            "no overworld-surface exit/re-entry path exists anywhere in pc_port (cave paths do not transfer)",
        ],
        "owner": None,
        "review_186": {
            "request": "Shared-native overworld surface exit / re-entry path",
            "scope": "Stage-boundary exit with transition anchor plus re-entry restore for overworld courses (cave checkpoint logic does not transfer)",
        },
    },
)

DIAGNOSTIC_PLAN = {
    "stall": "pre-idle legal-data stage-load stall: engine boots through window/GL/audio/init, then goes silent before the first fixture idle tick",
    "observation_points": [
        "Last log line before silence (post-jaudio with no P2_ROOM_PREVIEW/P2_PREVIEW_HEAP = stage-load stall; P2_ROOM_PREVIEW without PREVIEW_HEAP = map-model load stall; idle WAIT markers present = load OK, hang is later)",
        "Process liveness + CPU (spinning on shader compile vs blocked on synchronous I/O)",
        "DVDOpen FAILED lines naming the missing CWD-relative assets/dataDir files",
        "CWD-relative assets/dataDir presence plus preview sidecars (cargo-free/pod/cargo)",
    ],
    "data_ready_assumption": (
        "A data-ready environment stages CWD-relative assets/dataDir (legal disc "
        "extraction) plus the preview sidecars the boot contract requires; without "
        "them the stall is a data absence, not an engine defect."
    ),
    "smallest_instrumentation": [
        "Bounded frame budget with WAIT heartbeat markers in fixture idle (markers present = engine reached idle; absent = pre-idle stall)",
        "Preflight imprint listing CWD, assets/dataDir presence, and sidecar presence before engine boot",
        "DVDOpen failure capture naming each missing file",
    ],
    "owner_contract": "#186 shared-review track (existing owner contract for shared diagnostics)",
}

STATUSES = ("PINNED", "ABSENT")
GATES = ("identity_spawn", "movement_animation", "attacks_receivers",
         "death_corpse", "transport_reward", "cleanup_reentry")


def build_registry():
    """The validated machine-readable pin-discovery registry."""
    return {
        "schema": SCHEMA,
        "lane": "provider-overworld-surface-boot-path-pin-discovery",
        "issue": 707,
        "root_base": ROOT_BASE,
        "native_pin": NATIVE_PIN,
        "items": [dict(item, evidence=list(item["evidence"])) for item in ITEMS],
        "excluded_132": [
            {"item": name, "owner": "#658 (save/session pin-discovery)",
             "status": "EXCLUDED"}
            for name in EXCLUDED_132
        ],
        "diagnostic_plan": {
            "stall": DIAGNOSTIC_PLAN["stall"],
            "observation_points": list(DIAGNOSTIC_PLAN["observation_points"]),
            "data_ready_assumption": DIAGNOSTIC_PLAN["data_ready_assumption"],
            "smallest_instrumentation": list(DIAGNOSTIC_PLAN["smallest_instrumentation"]),
            "owner_contract": DIAGNOSTIC_PLAN["owner_contract"],
        },
        "downstream": list(DOWNSTREAM),
        "guard_sha256": GUARD_SHA256,
        "runtime_claim": False,
        "gates": {g: "UNTESTED" for g in GATES},
    }


def validate_registry(registry):
    """Return a list of refusal reasons; empty means the registry is valid."""
    problems = []
    if not isinstance(registry, dict):
        return ["registry-must-be-dict"]
    if registry.get("schema") != SCHEMA:
        problems.append("bad-schema")
    if registry.get("root_base") != ROOT_BASE:
        problems.append("bad-root-base")
    if registry.get("native_pin") != NATIVE_PIN:
        problems.append("bad-native-pin")
    items = registry.get("items")
    if not isinstance(items, list) or len(items) != 3:
        problems.append("bad-items")
    else:
        for item in items:
            if item.get("status") not in STATUSES:
                problems.append("bad-status-" + str(item.get("key")))
                continue
            if not item.get("evidence"):
                problems.append("missing-evidence-" + str(item.get("key")))
            if item["status"] == "ABSENT":
                review = item.get("review_186")
                if not isinstance(review, dict) or not review.get("request"):
                    problems.append("missing-186-request-" + str(item.get("key")))
            if item["status"] == "PINNED":
                if not item.get("owner"):
                    problems.append("missing-owner-" + str(item.get("key")))
    excluded = registry.get("excluded_132")
    if (not isinstance(excluded, list) or len(excluded) != 4
            or any(e.get("status") != "EXCLUDED" for e in excluded)):
        problems.append("bad-excluded-132")
    plan = registry.get("diagnostic_plan")
    if not isinstance(plan, dict):
        problems.append("bad-diagnostic-plan")
    else:
        for key in ("stall", "observation_points", "data_ready_assumption",
                    "smallest_instrumentation", "owner_contract"):
            if not plan.get(key):
                problems.append("missing-plan-" + key)
    if sorted(registry.get("downstream", [])) != sorted(DOWNSTREAM):
        problems.append("bad-downstream")
    gates = registry.get("gates")
    if not isinstance(gates, dict) or set(gates) != set(GATES):
        problems.append("bad-gates")
    if registry.get("runtime_claim") is not False:
        problems.append("no-runtime-claims")
    return problems


def registry_sha256(registry):
    return hashlib.sha256(
        json.dumps(registry, indent=1, sort_keys=True).encode("utf-8")).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Overworld surface boot-path pin discovery")
    parser.add_argument("--registry-out", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    registry = build_registry()
    problems = validate_registry(registry)
    if problems:
        for problem in problems:
            print("REFUSED reason=%s" % problem)
        return 1
    if args.check or args.registry_out is None:
        print("PIN_DISCOVERY_PASS items=%d absent=%d excluded_132=%d" % (
            len(registry["items"]),
            sum(1 for i in registry["items"] if i["status"] == "ABSENT"),
            len(registry["excluded_132"])))
    if args.registry_out:
        with open(args.registry_out, "w", encoding="utf-8") as f:
            f.write(json.dumps(registry, indent=1, sort_keys=True))
            f.write("\n")
        print("registry=%s sha256=%s" % (args.registry_out, registry_sha256(registry)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
