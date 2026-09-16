"""Independent adversarial regression runner for generated identities 41/57/58/78.

Muse lane l66 (#506), child of #440, wave #491. This module audits candidate
contracts produced by muse-placement (l52/#492) and muse-packaging (l53/#493)
without editing their files or the four consumer observers (l57-l60). It is a
verification harness supporting the closest-to-ADMIT families, not an
admission path: it can only report FAIL findings or a correlated-log verdict,
never a natural gameplay PASS on its own.

Covered adversarial classes (all fail closed):

1. Swapped source IDs: a ``P2_SEED_RESOLVE``/``P2_GENERATED_PLACEMENT`` leg
   naming another source id, or a binding marker for another family, on the
   same slot/generator.
2. Mismatched generator/slot: resolve target vs placement target/slot vs
   binding generator disagreement, or ``bound=0`` refusal.
3. Missing assets: a packaging manifest entry absent (or hash-mismatched) for
   the audited identity.
4. Stale replay: plan-digest / cache-generation disagreement between the
   staged candidate record and the observed run.
5. Unsupported terrain: placement terrain other than an allowed class for the
   identity (ground; mixed shore allowed only for Kurage57), unmapped slot
   (``slot=0``), or missing carry-route evidence.

Injected-birth taint (``injected``/``health_zero`` tokens on a birth marker or
on the correlated slot/generator) always fails the verdict and is labelled
explicitly; it can never close a natural gate.

Marker contract (read-only; owned by other lanes):

- ``P2_SEED_RESOLVE source_id=<id> target=<uid>`` (genteki.cpp birth bridge).
- ``P2_GENERATED_PLACEMENT source_id=<id> target=<uid> bound=<0|1>``
  (muse-placement bind claim).
- ``P2_PLACEMENT_SLOT generator=<gen> slot=<uid> ... terrain=<t> xyz=<0|1>
  route=<0|1>`` (placement probe).
- Family bindings: Fuefuki ``P2_HARDLANES_READY family=Fuefuki`` /
  ``P2_FUEFUKI_TEKI_*``; Kurage ``P2_KURAGE_TEKI_READY`` /
  ``P2_KURAGE_CORPSE_READY``; BombSarai ``P2_HARDLANES_READY
  family=BombSarai`` / ``P2_BOMBSARAI_*``; MiniHoudai ``P2_GROINK_*`` /
  ``P2_MINIHOUDAI_*``. Any binding names its engine generator file id via
  ``generator=``/``gen=``/``generator_id=``.

Stdlib only. Pure functions over log text and small manifest/replay dicts.
"""

import json
import re
import sys

CANDIDATES = {
    41: "Fuefuki",
    57: "Kurage",
    58: "BombSarai",
    78: "MiniHoudai",
}

# Family binding marker prefixes (upper-cased line match) per source id.
BINDING_MARKERS = {
    41: ("P2_FUEFUKI_TEKI_", "FAMILY=FUEFUKI"),
    57: ("P2_KURAGE_TEKI_READY", "P2_KURAGE_CORPSE_READY"),
    58: ("P2_BOMBSARAI_", "FAMILY=BOMBSARAI"),
    78: ("P2_GROINK_", "P2_MINIHOUDAI_"),
}

# Allowed placement terrain classes per source id. Kurage57 rides the
# l52 frog-cohort slot (mixed shore); the rest require open ground.
ALLOWED_TERRAINS = {
    41: ("ground",),
    57: ("ground", "mixed"),
    58: ("ground",),
    78: ("ground",),
}

LEGACY_AUTO_BIND_GENERATOR = "201001"

_RE_RESOLVE = re.compile(
    r"P2_SEED_RESOLVE\s+source_id=(?P<source>\d+)\s+target=(?P<target>\d+)")
_RE_RESOLVE_ALT = re.compile(
    r"P2_SEED_RESOLVE\S*\s+source_id=(?P<source>\d+)\s+target_id=(?P<target>\d+)")
_RE_PLACEMENT = re.compile(
    r"P2_GENERATED_PLACEMENT\s+source_id=(?P<source>\d+)\s+"
    r"target=(?P<target>\d+)(?:\s+generator=\d+)?\s+bound=(?P<bound>[01])\b")
_RE_SLOT = re.compile(
    r"P2_PLACEMENT_SLOT\s+generator=(?P<generator>\d+)\s+slot=(?P<slot>\d+)")
_RE_GENERATOR = re.compile(r"(?:generator|gen|generator_id)=(\d+)")
_RE_TERRAIN = re.compile(r"terrain=([A-Za-z]+)")
_RE_XYZ = re.compile(r"xyz=([01])\b")
_RE_ROUTE = re.compile(r"route=([01])\b")

_TAINT_TOKENS = ("injected", "health_zero")


def _tainted(line):
    lowered = line.lower()
    return any(token in lowered for token in _TAINT_TOKENS)


def _binding_family(line):
    """Return the candidate source id whose binding marker this line names."""
    upper = line.upper()
    for source_id, markers in BINDING_MARKERS.items():
        if any(marker in upper for marker in markers):
            return source_id
    return None


def audit_log(text, source_id):
    """Audit one run log for one candidate identity.

    Returns a dict with ``gate1_ok`` (True only for a fully correlated,
    untainted, terrain-legal triple), ``slot``/``generator`` of the agreed
    spawn (or -1), and ``findings`` — a list of ``<class>: <detail>``
    strings, one per detected adversarial condition. Empty findings with
    ``gate1_ok`` False means markers are simply absent (dependencies not
    landed yet), which is reported, not hidden.
    """
    expected_family = CANDIDATES.get(source_id, "?")
    findings = []
    resolve_targets = []
    resolve_other = []
    placement_targets = []
    placement_refused = []
    slots = []  # (generator, slot, terrain_ok, route_ok, line_no)
    bindings = []  # (family_source_id, generator)
    taint_lines = []

    for line_no, line in enumerate((text or "").splitlines(), start=1):
        if not line.strip():
            continue
        taint = _tainted(line)
        match = _RE_RESOLVE.search(line) or _RE_RESOLVE_ALT.search(line)
        if match and "P2_SEED_RESOLVE" in line:
            if taint:
                taint_lines.append(line_no)
            elif match.group("source") == str(source_id):
                resolve_targets.append(match.group("target"))
            else:
                resolve_other.append(
                    (match.group("source"), match.group("target")))
        match = _RE_PLACEMENT.search(line)
        if match:
            if taint:
                taint_lines.append(line_no)
            elif match.group("source") == str(source_id):
                if match.group("bound") == "1":
                    placement_targets.append(match.group("target"))
                else:
                    placement_refused.append(match.group("target"))
            else:
                resolve_other.append(
                    (match.group("source"), match.group("target")))
        match = _RE_SLOT.search(line)
        if match and "P2_PLACEMENT_SLOT" in line:
            terrain = _RE_TERRAIN.search(line)
            xyz = _RE_XYZ.search(line)
            route = _RE_ROUTE.search(line)
            terrain_name = terrain.group(1) if terrain else None
            slots.append({
                "generator": match.group("generator"),
                "slot": match.group("slot"),
                "terrain": terrain_name,
                "terrain_ok": (
                    terrain_name in ALLOWED_TERRAINS.get(source_id, ())
                    and xyz is not None and xyz.group(1) == "1"),
                "route_ok": route is not None and route.group(1) == "1",
                "line": line_no,
            })
            if taint:
                taint_lines.append(line_no)
        family = _binding_family(line)
        if family is not None:
            gen = _RE_GENERATOR.search(line)
            if taint:
                taint_lines.append(line_no)
            elif gen is not None:
                bindings.append((family, gen.group(1)))

    verdict = {
        "source_id": source_id,
        "family": expected_family,
        "gate1_ok": False,
        "slot": -1,
        "generator": -1,
        "findings": findings,
    }

    if not (text or "").strip():
        findings.append("absent-markers: empty log")
        return verdict

    # Class 1: swapped source ids / cross-family bindings.
    for other_source, target in resolve_other:
        findings.append(
            "swapped-source: resolve/placement names source_id=%s target=%s, "
            "expected source_id=%d (%s)"
            % (other_source, target, source_id, expected_family))
    own_binding_gens = sorted({gen for fam, gen in bindings
                               if fam == source_id}, key=int)
    foreign_bindings = sorted({str(fam) for fam, _ in bindings
                               if fam != source_id}, key=int)
    if foreign_bindings:
        findings.append(
            "swapped-source: binding marker for family source_id=%s present, "
            "expected %d (%s)"
            % (",".join(foreign_bindings), source_id, expected_family))

    # Class 2: refused / missing legs.
    if placement_refused:
        findings.append(
            "generator-slot: generated placement refused source_id=%d "
            "target=%s (bound=0)" % (source_id, placement_refused[0]))
    if not resolve_targets:
        if own_binding_gens or slots:
            findings.append(
                "absent-markers: binding/placement present without "
                "P2_SEED_RESOLVE source_id=%d; proxy/auto-bind "
                "(e.g. generator %s) is not a generated identity"
                % (source_id, LEGACY_AUTO_BIND_GENERATOR))
        else:
            findings.append(
                "absent-markers: missing P2_SEED_RESOLVE source_id=%d "
                "(placement/packaging candidates not landed yet)" % source_id)
    if not placement_targets and not slots:
        findings.append(
            "absent-markers: missing placement leg for source_id=%d "
            "(no P2_GENERATED_PLACEMENT bound=1, no P2_PLACEMENT_SLOT)"
            % source_id)
    if resolve_targets and not own_binding_gens:
        findings.append(
            "absent-markers: missing %s actor binding for source_id=%d"
            % (expected_family, source_id))

    # Class 2b: slot disagreement between resolve and placement legs.
    agreed_slots = set(resolve_targets) & (
        set(placement_targets) | {s["slot"] for s in slots})
    if (resolve_targets and (placement_targets or slots)
            and not agreed_slots):
        findings.append(
            "generator-slot: resolve/placement slot disagreement: "
            "resolve=%s placement=%s"
            % (sorted(set(resolve_targets), key=int),
               sorted(set(placement_targets) |
                      {s["slot"] for s in slots}, key=int)))

    # Correlate one triple: agreed slot + agreed generator + legal terrain.
    # A bound=0 refusal for the same target vetoes the verdict even when
    # placement-slot/resolve/binding legs are otherwise consistent: the
    # native registry rejected this exact spawn.
    match = None
    refused_slots = set(placement_refused)
    vetoed = set()
    for slot in slots:
        if slot["slot"] == "0":
            findings.append(
                "unsupported-terrain: unmapped slot=0 on placement line %d; "
                "no legal-slot profile" % slot["line"])
            continue
        if slot["slot"] not in resolve_targets:
            continue
        if slot["slot"] in refused_slots and slot["slot"] not in vetoed:
            findings.append(
                "generator-slot: native refusal (bound=0) for source_id=%d "
                "target=%s vetoes the correlated triple on placement line %d"
                % (source_id, slot["slot"], slot["line"]))
            vetoed.add(slot["slot"])
        if slot["slot"] in refused_slots:
            continue
        if (placement_targets and slot["slot"] not in placement_targets
                and slot["slot"] in set(resolve_targets)):
            # P2_GENERATED_PLACEMENT names another target: mismatch, not a
            # missing leg (already reported above when disjoint).
            continue
        if slot["terrain"] not in ALLOWED_TERRAINS.get(source_id, ()):
            findings.append(
                "unsupported-terrain: placement line %d terrain=%s not in %s "
                "for source_id=%d" % (
                    slot["line"], slot["terrain"],
                    list(ALLOWED_TERRAINS.get(source_id, ())), source_id))
            continue
        if not slot["terrain_ok"]:
            findings.append(
                "unsupported-terrain: placement line %d lacks xyz=1 ground "
                "fix (terrain=%s)" % (slot["line"], slot["terrain"]))
            continue
        if not slot["route_ok"]:
            findings.append(
                "unsupported-terrain: placement line %d missing carry-route "
                "evidence (route=1 required)" % slot["line"])
            continue
        if slot["generator"] not in own_binding_gens:
            findings.append(
                "generator-slot: no %s binding for placement generator=%s "
                "(bindings=%s)" % (
                    expected_family, slot["generator"], own_binding_gens))
            continue
        match = slot
        break

    # Placement-leg-free correlation (resolve + generated-placement + binding
    # agree on one slot when no P2_PLACEMENT_SLOT line names it): still FAIL
    # for gate1 because terrain/route evidence is missing, but report why.
    # Refused slots are excluded: their veto finding above already explains
    # why the gate stays closed.
    free_slots = [s for s in agreed_slots if s not in refused_slots]
    if match is None and free_slots and own_binding_gens:
        findings.append(
            "unsupported-terrain: slot=%s correlates resolve+placement+"
            "binding but no P2_PLACEMENT_SLOT line proves terrain/route; "
            "gate1 stays closed" % sorted(free_slots, key=int)[0])

    # Injected taint always fails and is labelled.
    if taint_lines:
        findings.append(
            "injected-taint: tainted birth/correlated marker on line(s) %s; "
            "injected state/HP/transport cannot close a natural gate"
            % sorted(set(taint_lines)))

    if match is not None and not taint_lines and not resolve_other \
            and not foreign_bindings:
        verdict["gate1_ok"] = True
        verdict["slot"] = int(match["slot"])
        verdict["generator"] = int(match["generator"])
    return verdict


def audit_assets(manifest, expected):
    """Audit a packaging manifest for missing/stale identity assets.

    ``manifest`` maps source id (int or str) to ``{"staged": bool,
    "sha256": str}``; ``expected`` maps source id to the required hex
    digest. Returns a findings list; empty means all four staged and fresh.
    """
    findings = []
    for source_id in sorted(CANDIDATES):
        record = (manifest or {}).get(source_id,
                                      (manifest or {}).get(str(source_id)))
        if not record or not record.get("staged"):
            findings.append(
                "missing-assets: source_id=%d (%s) has no staged candidate "
                "asset record" % (source_id, CANDIDATES[source_id]))
            continue
        want = (expected or {}).get(source_id,
                                    (expected or {}).get(str(source_id)))
        got = record.get("sha256")
        if want and got != want:
            findings.append(
                "missing-assets: source_id=%d (%s) staged hash %s disagrees "
                "with required %s" % (
                    source_id, CANDIDATES[source_id], got, want))
    return findings


def audit_replay(staged, observed):
    """Audit plan-digest / cache-generation agreement (stale replay check).

    ``staged`` and ``observed`` are dicts with ``plan_digest`` and
    ``cache_generation`` keys. Returns a findings list; empty means fresh.
    """
    findings = []
    for key in ("plan_digest", "cache_generation"):
        want = (staged or {}).get(key)
        got = (observed or {}).get(key)
        if want is None or got is None:
            findings.append(
                "stale-replay: %s not recorded (staged=%s observed=%s)" % (
                    key, want, got))
        elif want != got:
            findings.append(
                "stale-replay: %s disagreement: staged=%s observed=%s; "
                "cached run is not fresh evidence" % (key, want, got))
    return findings


def run_adversarial(cases):
    """Run a list of adversarial cases and return a reproducible summary.

    Each case is a dict with ``name``, ``source_id``, ``log`` (str),
    optional ``manifest``/``expected`` and ``staged``/``observed`` replay
    dicts, and ``expect_ok`` (bool). Returns ``{"cases": [...], "passed": n,
    "failed": n}`` where a case passes when the audit outcome (log verdict
    plus asset/replay findings) matches ``expect_ok``.
    """
    results = []
    for case in cases or []:
        source_id = case.get("source_id")
        verdict = audit_log(case.get("log", ""), source_id)
        extra = []
        if "manifest" in case or "expected" in case:
            extra.extend(
                audit_assets(case.get("manifest"), case.get("expected")))
        if "staged" in case or "observed" in case:
            extra.extend(
                audit_replay(case.get("staged"), case.get("observed")))
        ok = verdict["gate1_ok"] and not extra
        expected = bool(case.get("expect_ok"))
        results.append({
            "name": case.get("name", "?"),
            "source_id": source_id,
            "gate1_ok": verdict["gate1_ok"],
            "findings": verdict["findings"] + extra,
            "expected_ok": expected,
            "case_pass": ok == expected,
        })
    return {
        "cases": results,
        "passed": sum(1 for r in results if r["case_pass"]),
        "failed": sum(1 for r in results if not r["case_pass"]),
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?",
                        help="Run-log path (defaults to stdin)")
    parser.add_argument("--source-id", type=int, default=41,
                        help="Candidate source id to audit (default: 41)")
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    print(json.dumps(audit_log(text, args.source_id), indent=2))


if __name__ == "__main__":
    main()
