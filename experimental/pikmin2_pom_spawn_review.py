"""Read-only adjudication of Candypop-bud natural-spawn evidence (#448, shard enemies-1).

Question: does the legacy lane-23 model (Candypop FSM bound to a batch-2
``TEKI_Chappy`` proxy vehicle at an engineered arena sidecar point, drawing a
converted Pom bank at a static bind pose) satisfy a source-correct *natural*
gate-1 spawn for the six colored buds (sources 3..8), or is a real spawned
and drawn ``Pom`` actor required?

Source facts this module encodes (projectPiki/pikmin2, read-only):

- ``include/Game/enemyInfo.h:141``  ``EnemyID_Pom = 82`` "Candypop Bud base (crashes)"
- ``include/Game/enemyInfo.h:34``   ``EFlag_UseOwnID = 1`` (use own ID instead of the parent ID)
- ``include/Game/enemyInfo.h:35``   ``EFlag_CanBeSpawned = 4`` ("...unless youre UmiMushiBase or Pom")
- ``include/Game/enemyInfo.h:204``  ``idx = (flags & UseOwnID) ? enemyID : parentID``
- ``src/plugProjectYamashitaU/enemyInfo.cpp:18``   Pom: parent ``-1``, flags ``(EFlag_UseOwnID)`` only
- ``src/plugProjectYamashitaU/enemyInfo.cpp:19-24`` Blue/Red/Yellow/Black/White/RandPom:
  parent ``EnemyID_Pom``, flags ``(EFlag_CanBeSpawned | 2)`` - no ``EFlag_UseOwnID``

Consequence: a generator record may name a colored bud, but because the
colored entries carry no ``UseOwnID`` the manager resolves to the *parent*
``EnemyID_Pom`` (line 204), so the actor is born through the Pom actor
manager; and the base ``Pom`` itself is explicitly not spawnable ("crashes").
A source-correct natural spawn therefore needs a real Pom-manager-born,
ordinarily-drawn actor whose colored identity comes from the generator's own
id - none of which the Chappy proxy vehicle provides.

This module never runs the engine: it audits a native log plus optionally the
read-only decomp source extract and returns a verdict with cited lines.
"""

import hashlib
import re
from pathlib import Path

POM_SOURCE_IDS = (3, 4, 5, 6, 7, 8)
POM_BASE_ID = 82
POM_NAMES = {3: "BluePom", 4: "RedPom", 5: "YellowPom",
             6: "BlackPom", 7: "WhitePom", 8: "RandPom"}
POM_PARENT_ID = POM_BASE_ID

BIND_RE = re.compile(
    r"P2_POM_BIND generator=(\d+) species=(\w+) source_id=(\d+) host=([^\s]+)"
    r"(?: type=(\d+))?")
RESOLVE_RE = re.compile(r"P2_SEED_RESOLVE source_id=(\d+)")
PLACEMENT_RE = re.compile(
    r"P2_GENERATED_PLACEMENT source_id=(\d+) target=(\d+) generator=(\d+) bound=([01])")
DRAW_RE = re.compile(
    r"P2_POM_DRAW generator=(\d+) source_id=(\d+) bank=(\w+) pose=(\w+)")

PROVIDER_SPEC = dict(
    id="pom-actor-manager",
    actor="Pom base actor born through the Pom family manager (EnemyID_Pom parent "
          "resolution at include/Game/enemyInfo.h:204); the colored id (3..8) "
          "comes from the generator record and selects the bud identity",
    must_not="spawn the base Pom (82) directly: EFlag_CanBeSpawned is absent "
             "(include/Game/enemyInfo.h:35 names Pom) and the id is documented "
             "'(crashes)' (include/Game/enemyInfo.h:141)",
    mesh="converted Pom bank (lane 23) plus the per-species colored identity, "
         "replacing the Chappy proxy vehicle and its static bind pose",
    markers=["P2_POM_BIND generator=<g> source_id=<3..8> host=pom",
             "P2_POM_DRAW generator=<g> source_id=<3..8> bank=pom pose=<clip>",
             "P2_SEED_RESOLVE source_id=<3..8>",
             "P2_GENERATED_PLACEMENT source_id=<3..8> target=<uid> generator=<g> bound=1"],
    scope="Pom actor/manager birth is family scope (flora/pom lane, issue #448); "
          "the generated-session placement binding is a shared generic provider "
          "(placement shards; coordinate through #570). Do not duplicate "
          "provider-shard work here.",
    current="port has no Pom manager/teki reference (read-only scan of "
            "pc_port/*.cpp: none), so lane 23 substituted the batch-2 Chappy "
            "vehicle (experimental/pikmin2_pom_runtime.py:32-35,280,334)")

def sha256_text(text):
    if not isinstance(text, str):
        raise ValueError("text required")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_binds(text):
    """Extract ``P2_POM_BIND`` rows; each row is a dict."""
    if not isinstance(text, str):
        raise ValueError("native log text required")
    rows = []
    for line in text.splitlines():
        m = BIND_RE.search(line)
        if not m:
            continue
        rows.append(dict(
            generator=int(m.group(1)), species=m.group(2),
            source_id=int(m.group(3)), host=m.group(4),
            host_type=int(m.group(5)) if m.group(5) is not None else None,
            line=line.strip()))
    return rows


def proxy_vehicle_binds(rows):
    """Binds whose host is NOT the real Pom actor (a proxy placement vehicle)."""
    if not isinstance(rows, list):
        raise ValueError("bind rows required")
    return [r for r in rows if r["host"] != "pom"]


def parse_placement_triple(text):
    """Return (resolved_ids, placement_rows, drawn_ids) for the shared triple."""
    if not isinstance(text, str):
        raise ValueError("native log text required")
    resolved = {int(m.group(1)) for m in RESOLVE_RE.finditer(text)}
    placements = [dict(source_id=int(m.group(1)), target=int(m.group(2)),
                       generator=int(m.group(3)), bound=int(m.group(4)))
                  for m in PLACEMENT_RE.finditer(text)]
    drawn = {int(m.group(2)) for m in DRAW_RE.finditer(text)}
    return resolved, placements, drawn


def check_source_facts(enemyinfo_h, enemyinfo_cpp):
    """Read-only check of the decomp flags/parent facts this verdict rests on.

    Returns a dict of booleans; any False means the source moved and the
    verdict must be re-derived rather than trusted.
    """
    facts = {}
    try:
        h = Path(enemyinfo_h).read_text(errors="replace")
        c = Path(enemyinfo_cpp).read_text(errors="replace")
    except OSError:
        return dict(available=False)
    facts["available"] = True
    facts["use_own_id_flag"] = bool(re.search(r"EFlag_UseOwnID\s*=\s*1\b", h))
    facts["can_be_spawned_flag"] = bool(re.search(r"EFlag_CanBeSpawned\s*=\s*4\b", h))
    facts["pom_base_id_82"] = bool(re.search(r"EnemyID_Pom\s*=\s*82\b", h))
    facts["pom_excluded_comment"] = bool(
        re.search(r"unless\s+youre\s+UmiMushiBase\s+or\s+Pom", h))
    facts["parent_resolution"] = bool(
        re.search(r"UseOwnID\)\s*\?\s*enemyID\s*:\s*.*mParentID", h))
    facts["base_use_own_id_only"] = bool(re.search(
        r'\{"Pom",\s*EnemyTypeID::EnemyID_Pom,\s*-1,.*?\(EFlag_UseOwnID\)', c))
    facts["colored_parent_pom_no_own_id"] = all(re.search(
        r'\{"%s",\s*EnemyTypeID::EnemyID_%s,\s*EnemyTypeID::EnemyID_Pom,.*?'
        r'\(EFlag_CanBeSpawned \| 2\)' % (name, name), c)
        for name in ("BluePom", "RedPom", "YellowPom", "BlackPom", "WhitePom", "RandPom"))
    return facts


def validate_source_facts(facts):
    """Raise ValueError when a required source fact is absent/false."""
    if not isinstance(facts, dict) or not facts.get("available"):
        raise ValueError("source facts unavailable")
    missing = [k for k, v in facts.items() if k != "available" and v is not True]
    if missing:
        raise ValueError("source facts not confirmed: " + ", ".join(sorted(missing)))
    return True

def adjudicate(text, facts=None):
    """Return the verdict for a native log.

    ``verdict`` is one of:
    - ``natural_spawn_observed``: a real Pom-manager actor, ordinarily drawn,
      with the colored generator id and the shared placement triple.
    - ``spawned_actor_required``: only proxy-vehicle binds exist, so gate 1
      stays UNTESTED and a real Pom actor provider is required.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("native log text required")
    rows = parse_binds(text)
    resolved, placements, drawn = parse_placement_triple(text)
    proxies = proxy_vehicle_binds(rows)
    real = [r for r in rows if r["host"] == "pom"]
    colored = [r for r in rows if r["source_id"] in POM_SOURCE_IDS]
    base_hits = [r for r in rows if r["source_id"] == POM_BASE_ID]
    reasons = []
    evidence = [r["line"] for r in rows]

    def triple_ok(source_id):
        if source_id not in resolved:
            return False
        return any(p["source_id"] == source_id and p["bound"] == 1
                   for p in placements) and source_id in drawn

    natural = [r for r in real if r["source_id"] in POM_SOURCE_IDS
               and triple_ok(r["source_id"])]
    if natural:
        return dict(
            verdict="natural_spawn_observed",
            reasons=["real Pom actor bind with colored source id and shared "
                     "placement triple"],
            evidence=evidence, binds=rows, resolved=sorted(resolved),
            placements=placements, drawn=sorted(drawn),
            provider=None, gate1="PASS-candidate")
    if base_hits:
        reasons.append("a base-Pom (82) bind was observed; the base is not "
                       "spawnable and is documented to crash")
    if proxies:
        reasons.append(
            "%d proxy-vehicle bind(s) (host != pom, e.g. host=teki type=%s): "
            "an engineered arena vehicle is not a spawned Pom actor"
            % (len(proxies), proxies[0].get("host_type")))
    if colored and not real:
        reasons.append("all colored-bud binds are on proxy vehicles; no "
                       "Pom-manager actor birth marker present")
    if not rows:
        reasons.append("no P2_POM_BIND marker found")
    missing = []
    for source_id in sorted({r["source_id"] for r in colored}):
        if source_id not in resolved:
            missing.append("P2_SEED_RESOLVE source_id=%d" % source_id)
        if not any(p["source_id"] == source_id and p["bound"] == 1 for p in placements):
            missing.append("P2_GENERATED_PLACEMENT source_id=%d bound=1" % source_id)
        if source_id not in drawn:
            missing.append("P2_POM_DRAW source_id=%d" % source_id)
    if missing:
        reasons.append("missing natural markers: " + ", ".join(missing[:6]))
    return dict(
        verdict="spawned_actor_required",
        reasons=reasons or ["no natural Pom spawn evidence"],
        evidence=evidence, binds=rows, resolved=sorted(resolved),
        placements=placements, drawn=sorted(drawn),
        provider=PROVIDER_SPEC, gate1="UNTESTED")


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--enemyinfo-h", type=Path, default=None)
    parser.add_argument("--enemyinfo-cpp", type=Path, default=None)
    args = parser.parse_args()
    facts = None
    if args.enemyinfo_h and args.enemyinfo_cpp:
        facts = check_source_facts(args.enemyinfo_h, args.enemyinfo_cpp)
        try:
            validate_source_facts(facts)
        except ValueError as error:
            raise SystemExit("source facts not confirmed: %s" % error)
    result = adjudicate(args.log.read_text(errors="replace"), facts)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("binds", "placements")}, indent=2))
    raise SystemExit(0 if result["verdict"] == "natural_spawn_observed" else 3)