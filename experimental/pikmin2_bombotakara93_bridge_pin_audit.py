"""Pin-discovery/ownership audit for the source-93 BombOtakara dynamic bridge.

Read-only (#791). Traces the generated-placement dynamic bridge refusing source
93 to its actual producer and decides the correct owner, emits a machine packet.

Traced chain (baseline; the audit FAILS CLOSED on drift instead of updating it):
  pc_port/pc_p2_generated_placement.cpp:113 -> pc_p2_otakara_bind_dynamic
  pc_port/pc_p2_otakara.cpp:551 -> pc_p2_otakara_bind_dynamic
  pc_port/pc_p2_otakara.cpp:427 -> speciesFromSource
speciesFromSource admits only 59/60/61/62 and returns -1 for 93, so the bridge
refuses the BombOtakara carrier (P2_MUSE_BOMBOTAKARA573_BIND_REFUSED
reason=dynamic_bridge_59_62_only).

Decision: bind source 93 through the #616 pc_p2_bomb_mgr_birth path, NOT by
extending the otakara bridge. pc_p2_otakara.h:22-24 explicitly excludes
BombOtakara (93) because it consumes the shared Bomb blast contract; the
maintained native tree already integrates pc_p2_bomb_mgr_birth.cpp (source 36)
while the generated-placement bridge is absent there.

No invented values: every anchor cites file + line; all six gates stay UNTESTED.
No runtime, build, manifest write or ADMIT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "p2-bombotakara93-bridge-pin-audit-v1"
ISSUE = 791
CONSUMER_LANE = "enemy-bombotakara93-payload"
CONSUMER_ISSUE = 573
PROVIDER_LANE = "provider-bomb-mgr-birth"
PROVIDER_ISSUE = 616
PROVIDER_SHARDS = ("actor-birth-projectiles", "placement-catalog")

BRIDGE_CALLSITE = {"file": "pc_port/pc_p2_generated_placement.cpp", "line": 113,
                   "symbol": "pc_p2_otakara_bind_dynamic", "case": 93}
BIND_SYMBOL = {"file": "pc_port/pc_p2_otakara.cpp", "line": 551,
               "symbol": "pc_p2_otakara_bind_dynamic"}
SOURCE_MAP = {"file": "pc_port/pc_p2_otakara.cpp", "line": 427,
              "symbol": "speciesFromSource"}
ADMITTED_SOURCES = (59, 60, 61, 62)
REFUSED_SOURCE = 93
BOMB_MGR_SOURCE_ID = 36
DECISION = "bind_93_via_616_bomb_mgr_birth"
REJECTED_ALTERNATIVE = "extend_otakara_bridge_for_93"
GATES = ("identity_spawn", "movement_animation", "attacks_receivers",
         "death_corpse", "transport_reward", "cleanup_reentry")
WAVE_FILES = {
    "bridge": "pc_port/pc_p2_generated_placement.cpp",
    "bridge_header": "pc_port/pc_p2_generated_placement.h",
    "otakara": "pc_port/pc_p2_otakara.cpp",
    "otakara_header": "pc_port/pc_p2_otakara.h",
    "bomb_mgr": "pc_port/pc_p2_bomb_mgr_birth.cpp",
    "bomb_mgr_header": "pc_port/pc_p2_bomb_mgr_birth.h",
}
INTEGRATED_IN_WAVE = ("bomb_mgr", "bomb_mgr_header")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_admitted_sources(text: str) -> set:
    """Return the `case N:` source IDs admitted inside speciesFromSource.

    Fails closed if the function is absent or declares no cases. This keeps the
    audit honest: the admitted set is read from source, never assumed.
    """
    if not isinstance(text, str) or not text:
        raise ValueError("speciesFromSource source text is empty")
    match = re.search(r"speciesFromSource\s*\([^)]*\)\s*\{", text)
    if not match:
        raise ValueError("speciesFromSource definition not found")
    start = match.end()
    depth = 1
    body = []
    for ch in text[start:]:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        body.append(ch)
    if depth != 0:
        raise ValueError("unterminated speciesFromSource body")
    admitted = {int(n) for n in re.findall(r"case\s+(\d+)\s*:", "".join(body))}
    if not admitted:
        raise ValueError("speciesFromSource admits no sources")
    return admitted


def check_source_map(admitted: set) -> None:
    expected = set(ADMITTED_SOURCES)
    if admitted != expected:
        raise ValueError("speciesFromSource drift: expected "
                         + str(sorted(expected)) + " found " + str(sorted(admitted)))
    if REFUSED_SOURCE in admitted:
        raise ValueError("speciesFromSource unexpectedly admits source 93")


def scan_roots(roots: dict) -> dict:
    """Record verbatim which audited files exist under each supplied root."""
    if not isinstance(roots, dict) or not roots:
        raise ValueError("roots must be a non-empty mapping of label -> path")
    presence = {}
    for label, base in roots.items():
        if not isinstance(base, (str, Path)):
            raise ValueError("root path for " + str(label) + " is not a path")
        root = Path(base)
        presence[label] = {
            key: (root / rel).is_file() for key, rel in WAVE_FILES.items()
        }
    return presence


def build_packet(presence: dict, source_map_text: str) -> dict:
    admitted = parse_admitted_sources(source_map_text)
    check_source_map(admitted)
    integrated = {label: [k for k in INTEGRATED_IN_WAVE if p.get(k)]
                  for label, p in presence.items()}
    packet = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "decision": DECISION,
        "rejected_alternative": REJECTED_ALTERNATIVE,
        "traced_chain": [BRIDGE_CALLSITE, BIND_SYMBOL, SOURCE_MAP],
        "admitted_sources": sorted(admitted),
        "refused_source": REFUSED_SOURCE,
        "bomb_mgr_source_id": BOMB_MGR_SOURCE_ID,
        "owner": {"lane": PROVIDER_LANE, "issue": PROVIDER_ISSUE,
                  "provider_shards": list(PROVIDER_SHARDS)},
        "consumer": {"lane": CONSUMER_LANE, "issue": CONSUMER_ISSUE},
        "wave_presence": presence,
        "integrated_in_wave": integrated,
        "missing_input": [
            "#186 shared-hook landing that invokes pc_p2_bomb_mgr_birth_update "
            "and pc_p2_bomb_mgr_birth_forget from the engine BTeki::update/doKill "
            "path (Section 2 host binding in pc_p2_bomb_mgr_birth.cpp:373/405).",
            "Source-93 carrier admission: register the BombOtakara carrier "
            "generator through the BombMgr carrier seam (p2-bomb-mgr-birth.txt / "
            "pc_p2_bomb_mgr_birth_carrier, pc_p2_bomb_mgr_birth.cpp:355), not the "
            "otakara dynamic bridge.",
            "Generated-placement bridge route for 93 if the consumer still binds "
            "through pc_p2_generated_placement_bind (pc_p2_generated_placement.cpp:98).",
        ],
        "first_executable_slice": {
            "kind": "engine_change",
            "callsites": [
                {"file": "pc_port/pc_p2_bomb_mgr_birth.cpp",
                 "symbol": "pc_p2_bomb_mgr_birth_update", "line": 373},
                {"file": "pc_port/pc_p2_bomb_mgr_birth.cpp",
                 "symbol": "pc_p2_bomb_mgr_birth_forget", "line": 405},
                {"file": "pc_port/pc_p2_generated_placement.cpp",
                 "symbol": "pc_p2_generated_placement_bind", "line": 98,
                 "add_case": 93},
            ],
            "reserve_owned_files": [
                "pc_port/pc_p2_generated_placement.cpp",
                "pc_port/pc_p2_generated_placement.h",
            ],
            "build_membership": ["native/CMakeLists.txt"],
            "verification_only": [
                "pc_port/pc_p2_bomb_mgr_birth.cpp",
                "pc_port/pc_p2_bomb_mgr_birth.h",
            ],
        },
        "destination_pins": {
            "wave_root": "fdd558123223f94d706b9a00973037553e864756",
            "wave_native": "a95040b66a0ffc9cdbfc649502569a29e66949a7",
            "consumer_root": "2c3d918916034de34c71aa65cd33d9bef4e97320",
            "consumer_native": "7bbeb3bacdf6b6712e7d92e5b503d89653229280",
            "provider_native": "6d4cbc4afc112c02b7166ef30d8a1f684c7f3ba5",
        },
        "decision_request_186": {
            "gate": "shared hook review",
            "proposed_files": [
                "pc_port/pc_p2_bomb_mgr_birth.cpp",
                "pc_port/pc_p2_bomb_mgr_birth.h",
            ],
            "request": "Approve landing the shared BTeki::update / doKill hook "
                       "callsites that drive pc_p2_bomb_mgr_birth_update/_forget "
                       "for the source-93 BombOtakara carrier, or reject.",
        },
        "gates": {gate: "UNTESTED" for gate in GATES},
        "limitations": [
            "Maintained native/ lacks the generated-placement bridge; its route "
            "is audited in the owner's private branch only.",
            "No runtime; destination pins are read-only audit inputs.",
        ],
    }
    check_packet(packet)
    return packet


def check_packet(packet: dict) -> None:
    if packet.get("schema") != SCHEMA:
        raise ValueError("unknown packet schema")
    if packet.get("decision") != DECISION:
        raise ValueError("unexpected producer decision")
    if packet.get("refused_source") != REFUSED_SOURCE:
        raise ValueError("refused source must be 93")
    if packet.get("bomb_mgr_source_id") != BOMB_MGR_SOURCE_ID:
        raise ValueError("bomb manager source id must be 36")
    for gate, status in packet.get("gates", {}).items():
        if status != "UNTESTED":
            raise ValueError("gate " + gate + " is not UNTESTED")
    slice_ = packet.get("first_executable_slice", {})
    if "native/CMakeLists.txt" not in slice_.get("build_membership", []):
        raise ValueError("first slice must name build membership")

# Baseline copied verbatim from the owner's private branch
# (pc_p2_otakara.cpp:427-435). Used only when no --source-map file is supplied.
BASELINE_SOURCE_MAP = """static int speciesFromSource(unsigned source) {
    switch (source) {
    case 59: return p2dweevil::FireId;
    case 60: return p2dweevil::WaterId;
    case 61: return p2dweevil::GasId;
    case 62: return p2dweevil::ElecId;
    default: return -1;
    }
}
"""


def run(roots: dict, output: Path, source_map_path: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    if source_map_path is not None:
        if not Path(source_map_path).is_file():
            raise ValueError("source map file not found: " + str(source_map_path))
        source_map_text = Path(source_map_path).read_text(encoding="utf-8",
                                                          errors="replace")
        origin = str(source_map_path)
    else:
        source_map_text = BASELINE_SOURCE_MAP
        origin = "embedded-baseline"
    presence = scan_roots(roots)
    packet = build_packet(presence, source_map_text)
    log = [
        "issue=" + str(ISSUE) + " decision=" + DECISION,
        "source_map_origin=" + origin,
        "source_map_sha256=" + sha256(source_map_text.encode("utf-8")),
    ]
    for label, row in presence.items():
        log.append("root=" + label + " present="
                   + ",".join(k for k, v in row.items() if v))
    log.append("packet validated: gates UNTESTED, decision=" + DECISION)
    (output / "packet.json").write_text(json.dumps(packet, indent=2) + "\n",
                                        encoding="utf-8")
    (output / "run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    packet["_log"] = log
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", default=[],
                        help="label=path pair (repeatable)")
    parser.add_argument("--source-map", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    roots = {}
    for item in args.root:
        if "=" not in item:
            raise SystemExit("--root expects label=path")
        label, path = item.split("=", 1)
        roots[label] = path
    if not roots:
        raise SystemExit("at least one --root is required")
    result = run(roots, args.output, args.source_map)
    print("decision=" + result["decision"] + " packet="
          + str(args.output / "packet.json"))


if __name__ == "__main__":
    main()
