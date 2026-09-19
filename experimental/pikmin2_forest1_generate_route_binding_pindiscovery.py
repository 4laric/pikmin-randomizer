"""Forest1 generate-manifest route-binding pin-discovery (issue #801).

Lane forest1-generate-route-binding-pindiscovery. Read-only pin-discovery /
ownership slice for the blocked consumer cave-forest1-collision-routes-obs
(#773, downstream #154). It pins the canonical generator-line ``spawn``
parser and route-binding callsites, defines the required grammar/loader
extension and first executable slice, and adjudicates a staged generate
manifest fail-closed. It runs no build, edits no engine file and is never an
engine unblock.
"""
import re

PACKET = "p2-forest1-generate-route-binding-pindiscovery/1"
CONSUMER_ISSUE = 773
DOWNSTREAM_ISSUE = 154
AUDIT_HANDOFF_SHA256 = "5dd7420d"
DEFECT = "SPAWN_ROUTE_BINDING_MISSING"
OWNER_LINE = "#129 generator/actor staging"
PROVIDER_SHARD = "provider-cave-generation"

# Canonical generate-manifest parser and binding callsites (integrated line).
CALLSITES = [
    {
        "file": "native/pc_port/pc_p2_cave_generate.h",
        "symbol": "struct Spawn { std::string id; int count; }",
        "line": 73,
        "role": "spawn record has no route/group field",
        "status": "integrated",
    },
    {
        "file": "native/pc_port/pc_p2_cave_generate.h",
        "symbol": "readManifest(std::istream&, Manifest&) spawn loop",
        "line": 151,
        "role": "parses 'spawn <id> <count>' with no route token",
        "status": "integrated",
    },
    {
        "file": "native/pc_port/pc_p2_cave_generate.h",
        "symbol": "Manifest spawn emitter (P2_CAVE_GENERATE_SPAWN)",
        "line": 217,
        "role": "emits id/count only; no route binding marker",
        "status": "integrated",
    },
    {
        "file": "native/pc_port/pc_p2_cave_generate.cpp",
        "symbol": "kP2CaveGenerateModule",
        "line": 8,
        "role": "membership/version stub; wired into PC_PORT_SOURCES",
        "status": "integrated",
    },
]

# Route-group loader / binding callsite: engine-side, not in the generator TU.
ROUTE_LOADER = {
    "file": "engine src (route manager)",
    "symbol": "route-group loader (audit: group 'test' = 64 points)",
    "status": "engine-side",
    "note": "The generator emits spawn intents only; no generated actor is "
            "bound to a walking route. The binding callsite is not present in "
            "the generator line; bind after the grammar carries the route.",
}

# Build membership and first executable slice.
FIRST_SLICE = {
    "callsite_files": ["native/pc_port/pc_p2_cave_generate.h"],
    "build_membership_files": ["native/pc_port/pc_p2_cave_generate.cpp"],
    "membership_status": "already wired (CMakeLists.txt PC_PORT_SOURCES)",
    "reserve": ["native/pc_port/pc_p2_cave_generate.h",
                "native/pc_port/pc_p2_cave_generate.cpp"],
    "owner_lane": OWNER_LINE,
    "provider_shard": PROVIDER_SHARD,
}

# Required grammar/loader extension.
EXTENSION = {
    "grammar": "spawn <enemy-id> <count> <route-group>   (route required)",
    "struct": "add std::string route to struct Spawn",
    "parser": "readManifest spawn loop reads the trailing route token and "
              "refuses unknown/empty route groups",
    "loader": "runner binds each spawned actor to the named route group so it "
              "walks; emit a P2_CAVE_GENERATE_SPAWN route=<group> ack",
    "compat": "old two-field spawn lines must be refused (fail-closed) rather "
              "than silently unbound",
}

_SPAWN_RE = re.compile(r"^spawn\s+(\S+)\s+(\d+)(?:\s+(\S+))?\s*$")
_HEADER = "P2_CAVE_GENERATE_1"


def parse_spawns(text):
    """Parse the spawn section of a generate manifest.

    Returns list of dicts(id, count, route) or raises ValueError on
    malformed input (missing header, bad counts, missing spawns block).
    Refuses nothing that is merely unbound; binding is adjudicated
    separately so the defect is reportable.
    """
    if not isinstance(text, str) or _HEADER not in text:
        raise ValueError("missing " + _HEADER + " header")
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines)
                     if ln.split()[:1] == ["spawns"])
    except StopIteration:
        raise ValueError("missing spawns block")
    head = lines[start].split()
    if len(head) >= 2:
        count_token, body_from = head[1], start + 1
    else:
        if start + 1 >= len(lines):
            raise ValueError("spawns block truncated")
        count_token, body_from = lines[start + 1].strip(), start + 2
    if not count_token.isdigit():
        raise ValueError("missing spawn count")
    nspawns = int(count_token)
    spawns = []
    seen = 0
    for ln in lines[body_from:]:
        s = ln.strip()
        if not s:
            continue
        if s.split()[:1] == ["anchor"]:
            break
        m = _SPAWN_RE.match(s)
        if not m:
            raise ValueError("malformed spawn line: " + s)
        ident, count, route = m.group(1), int(m.group(2)), m.group(3)
        if count < 1:
            raise ValueError("bad count on: " + s)
        spawns.append({"id": ident, "count": count, "route": route})
        seen += 1
    if seen != nspawns:
        raise ValueError("spawn count %d != declared %d" % (seen, nspawns))
    return spawns


def adjudicate(text):
    """Fail-closed verdict on a generate manifest's route binding.

    BINDING_MISSING: at least one spawn line lacks a route field.
    BOUND: every spawn line carries a route. MALFORMED: unparseable.
    """
    try:
        spawns = parse_spawns(text)
    except ValueError as exc:
        return {"verdict": "MALFORMED", "detail": str(exc),
                "unbound": [], "bound": []}
    unbound = [s for s in spawns if not s["route"]]
    bound = [s for s in spawns if s["route"]]
    return {
        "verdict": "BOUND" if not unbound else DEFECT,
        "detail": "unbound spawns: " + ", ".join(s["id"] for s in unbound)
                  if unbound else "all spawns carry a route",
        "unbound": [s["id"] for s in unbound],
        "bound": [s["id"] for s in bound],
    }


def resume_disposition(verdict):
    """Downstream #773/#154 resume gate: only a BOUND manifest permits a run."""
    if verdict == "BOUND":
        return {"resume": True,
                "gate": "route-bound manifest; run one fresh guarded "
                        "observation and require >=1 P2_FOREST1_TRAVERSE/moved>0"}
    return {"resume": False,
            "gate": "no-resume until a route-bound manifest (or generator ack) "
                    "exists; re-running reproduces 1 birth / 0 traverse"}


def packet():
    """Machine-readable pin-discovery packet."""
    return {
        "schema": PACKET,
        "consumer_issue": CONSUMER_ISSUE,
        "downstream_issue": DOWNSTREAM_ISSUE,
        "audit_handoff_sha256": AUDIT_HANDOFF_SHA256,
        "defect": DEFECT,
        "callsites": CALLSITES,
        "route_loader": ROUTE_LOADER,
        "first_slice": FIRST_SLICE,
        "extension": EXTENSION,
        "pins": {
            "content_root_head": "f2803e423b9f30ee6fcaf79004be02b2770a5a98",
            "native_head": "b944db033a3eef7aabb135372c4656d04e47bd7d",
            "manifest_sha256": "86691d1c59fbc4e2fc325bf3e5de49e752bc882bedb81f604d18068950346bdb",
            "run_log_sha256": "de7812cce5a59c20650a59f0cbae7f13e8cde146988dcd59547072b525fe40b7",
        },
        "runtime_claim": False,
    }


def main(argv=None):
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("packet", "adjudicate", "resume"))
    parser.add_argument("path", nargs="?", help="manifest path")
    args = parser.parse_args(argv)
    if args.command == "packet":
        print(json.dumps(packet(), indent=2, sort_keys=True))
        return 0
    if not args.path:
        parser.error(args.command + " requires a manifest path")
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    if args.command == "adjudicate":
        result = adjudicate(text)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    verdict = adjudicate(text)["verdict"]
    print(json.dumps(resume_disposition(verdict), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()