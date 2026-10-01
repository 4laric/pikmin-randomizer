"""Read-only route/spawn binding audit for the forest1 staged arena (issue #796).

Lane forest1-route-binding-audit, prerequisite recovery request
75aa5e3a0ed0ecc2ca0cd180c6fce13ccc2ddae224dd397bf2741ca196e9b62f.

Consumes, read-only: the blocked collision-obs staged generate manifest and
run log, plus the forest1-p1 arena manifest, and adjudicates the exact
binding defect between the requested spawn set and the engine-observed
actor behaviour. It never builds, stages, launches or edits anything; no
actor-manager birth internals are touched.

Observed facts (hashes pinned in the lane report):
  - The staged manifest requests `spawns 2` (UjiA 6, UjiB 4 = 10 actors)
    with no route/group field on any spawn line.
  - The engine emits exactly ONE P2_FOREST1_BIRTH and one CONTACT, then 0
    movement and 0 traversal over ~20k ticks with live_actors=1.
  - Route group `test` is loaded with 64 points, yet no spawned actor is
    bound to any route group.

Conclusion encoded: the defect is a missing spawn-to-route binding at
generator/staging level (the generate manifest has no per-spawn route
reference and the engine's generate reader spawns actors without attaching
a walking route), not a collision/locomotion engine fault. The owning scope
is the generator/actor staging line (#129) plus the criterion disposition
(#154); this lane records the defect and a resume/no-resume disposition
without claiming either.
"""
import re

LANE = "forest1-route-binding-audit"
ISSUE = 796
REQUEST_ID = ("75aa5e3a0ed0ecc2ca0cd180c6fce13ccc2ddae224dd397bf274"
              "1ca196e9b62f")
DOWNSTREAM_ISSUE = 154
OWNING_ISSUES = (129, 154)

GENERATE_REL = ("output/workflow/autofill/planning-shards/caves-forest/"
                "prepared/forest1-collision-obs-out/run-forest1-collision/"
                "p2-cave-generate.txt")
RUNLOG_REL = ("output/workflow/autofill/planning-shards/caves-forest/"
              "prepared/forest1-collision-obs-out/run-collision2.log")
# Byte hash of the staged file; consumers must hash bytes, not text,
# because Windows text-mode reads normalise CRLF and change the digest.
GENERATE_SHA256 = ("86691d1c59fbc4e2fc325bf3e5de49e752bc882bedb81f604d1"
                   "8068950346bdb")
RUNLOG_SHA256 = ("de7812cce5a59c20650a59f0cbae7f13e8cde146988dcd595"
                 "47072b525fe40b7")

_SPAWN_RE = re.compile(r"^spawn (\S+) (\d+)$", re.MULTILINE)
_ROUTE_GROUP_RE = re.compile(r"\[PC Route\] group (\d+): id='([^']*)' points=(\d+)")
_BIRTH_RE = re.compile(r"P2_FOREST1_BIRTH id=(\d+)")
_TRAVERSE_RE = re.compile(r"P2_FOREST1_TRAVERSE")
_GROUND_RE = re.compile(r"\[Pikipelago\] P2_ROOM_GROUND x=([-\d.]+) z=([-\d.]+)")
_READY_RE = re.compile(r"P2_CAVE_READY floor=(\d+) survivors=(\d+)")
_ENTRY_RE = re.compile(r"P2_FOREST1_COLLISION_ENTRY_READY floor=(\d+)")

SPAWN_BINDING_GRAMMAR = ("spawn <name> <count>", "no route/group field")


def parse_generate(text):
    """Parse the requested spawn set from a staged generate manifest."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Missing generate manifest text")
    if "P2_CAVE_GENERATE_1" not in text:
        raise ValueError("Unsupported generate manifest version")
    spawns = [(name, int(count)) for name, count in _SPAWN_RE.findall(text)]
    if not spawns:
        raise ValueError("Generate manifest requests no spawns")
    anchor = re.search(r"^anchor (\S+)$", text, re.MULTILINE)
    return {
        "spawns": spawns,
        "requested_actors": sum(count for _, count in spawns),
        "spawn_lines": len(spawns),
        "anchor": anchor.group(1) if anchor else None,
        "carries_route_group": bool(re.search(
            r"^spawn \S+ \d+ \S+$", text, re.MULTILINE)),
    }


def parse_runlog(text):
    """Extract the engine-observed binding facts from a collision run log."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Missing run log text")
    births = [int(m) for m in _BIRTH_RE.findall(text)]
    groups = [(int(index), ident, int(points))
              for index, ident, points in _ROUTE_GROUP_RE.findall(text)]
    ready = [(int(f), int(s)) for f, s in _READY_RE.findall(text)]
    entry = [int(f) for f in _ENTRY_RE.findall(text)]
    observes = re.findall(
        r"P2_FOREST1_COLLISION_OBSERVE observed=(\d+) squad=(\d+) "
        r"births=(\d+) grounded=(\d+) moved=(\d+) live_actors=(\d+)", text)
    last = tuple(int(v) for v in observes[-1]) if observes else None
    return {
        "births": births,
        "birth_count": len(births),
        "route_groups": groups,
        "route_points": sum(points for _, _, points in groups),
        "cave_ready": ready,
        "entry_floors": entry,
        "traverses": len(_TRAVERSE_RE.findall(text)),
        "ground_probes": len(_GROUND_RE.findall(text)),
        "final_observe": last,
        "tick_budget": last[0] if last else 0,
    }


def adjudicate(generate, runlog):
    """Name the exact binding defect or the owning lane.

    Fail-closed: contradictory or absent facts produce UNDETERMINED, never a
    guess. Returns a machine-readable verdict with the owning scope.
    """
    requested = generate["requested_actors"]
    observed = runlog["birth_count"]
    moved = runlog["final_observe"][4] if runlog["final_observe"] else 0
    traverses = runlog["traverses"]
    groups = runlog["route_points"]
    problems = []
    if requested < 1:
        problems.append("requested-actors-%d" % requested)
    if generate["carries_route_group"]:
        problems.append("manifest-carries-unexpected-route-field")
    if observed < 1:
        problems.append("no-actor-birth")
    if groups < 1:
        problems.append("no-route-group-loaded")
    if problems:
        return {"verdict": "UNDETERMINED", "defect": None, "owner": None,
                "problems": problems}

    if observed < requested and moved == 0 and traverses == 0:
        defect = "SPAWN_ROUTE_BINDING_MISSING"
        detail = ("staged manifest requests %d actors across %d spawn lines "
                  "with no route/group field; engine births %d and never "
                  "moves or traverses despite %d loaded route points"
                  % (requested, generate["spawn_lines"], observed, groups))
        owner = ("generator/actor staging line (#129) with criterion "
                 "disposition in #154")
    elif observed >= requested and traverses == 0:
        defect = "TRAVERSAL_NOT_OBSERVED"
        detail = ("all requested actors birthed (%d) but no traversal marker "
                  "appeared; route binding may exist yet walking is not "
                  "observable" % observed)
        owner = "criterion 3 observer (#154) with generator ack (#129)"
    elif traverses > 0:
        defect = None
        detail = "route traversal observed; binding not defective in this run"
        owner = None
    else:
        defect = "PARTIAL_SPAWN_SET"
        detail = ("%d of %d requested actors birthed with movement=%d; "
                  "spawn-count or admission gap" % (observed, requested, moved))
        owner = "generator/actor staging line (#129)"
    return {
        "verdict": "DEFECT" if defect else "HEALTHY",
        "defect": defect,
        "detail": detail,
        "owner": owner,
        "requested_actors": requested,
        "observed_births": observed,
        "traverses": traverses,
        "route_points_loaded": groups,
    }


def resume_disposition(verdict):
    """Downstream #154 resume/no-resume disposition for this finding."""
    if verdict["verdict"] != "DEFECT":
        return {"resume": False, "reason":
                "no generator-side defect named; criterion 3 remains "
                "unobserved and #154 stays with its runtime owner"}
    return {
        "resume": False,
        "reason": (
            "NO-RESUME for #154 runtime re-observation until the named "
            "owner (%s) lands a spawn-to-route binding; re-running the same "
            "staged arena would reproduce the identical 1-birth/0-traverse "
            "outcome. Resume gate: a staged manifest whose spawns carry a "
            "route/group binding (or a generator ack that binds them), then "
            "one fresh guarded run." % (verdict.get("owner") or "generator line")),
    }


def audit(generate_text, runlog_text):
    """Full audit: parse, adjudicate and dispose. Fail-closed throughout."""
    generate = parse_generate(generate_text)
    runlog = parse_runlog(runlog_text)
    verdict = adjudicate(generate, runlog)
    return {
        "schema": 1,
        "lane": LANE,
        "issue": ISSUE,
        "request_id": REQUEST_ID,
        "downstream_issue": DOWNSTREAM_ISSUE,
        "owning_issues": list(OWNING_ISSUES),
        "generate": generate,
        "runlog": runlog,
        "verdict": verdict,
        "disposition": resume_disposition(verdict),
        "spawn_binding_grammar": list(SPAWN_BINDING_GRAMMAR),
        "generated": False,
        "limitations": [
            "Read-only audit of existing staged evidence; no build, run or "
            "engine edit is performed here.",
            "No actor-manager birth internals are inspected; the defect is "
            "named at the manifest/route-binding boundary.",
            "No gameplay acceptance is claimed; all six gates stay UNTESTED.",
        ],
    }
