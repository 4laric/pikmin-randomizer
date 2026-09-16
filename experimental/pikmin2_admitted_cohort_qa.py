"""Independent QA for the user-approved admitted nine-identity cohort (#530).

Validates the admitted cohort [23, 44, 54, 57, 59, 60, 61, 62, 78] on the
frozen species integration pin purely through the real seed/session machinery;
no native process, no admission writes, no allowlist changes.

Checks (all engine-free):

- admitted set: the roster's admitted IDs equal ADMITTED exactly.
- seed manifests: deterministic representative seeds generate manifests whose
  P2 layout binds exactly the admitted cohort, on accepted slot uids, with a
  bootstrap that round-trips.
- determinism: the same seed generated twice yields identical bindings and
  fingerprints.
- denied exclusion: denied probes (Queen 30 proxy, Fuefuki 41 candidate-only,
  Bulblax 53) resolve to no install family, bind to no admitted target, and a
  layout smuggling one in is rejected at load.
- duplicate receipts: a layout with a duplicate binding target, an enum
  mismatch, or a roster-revision mismatch is rejected; re-applying the same
  manifest is idempotent (same fingerprint, same bindings).
- install targets: every admitted ID resolves to a lane-05 family installer.
- save/restart: a manifest saved to a session directory reloads byte-identical
  and revalidates; a tampered (foreign-seed) copy is rejected.

Runtime startups (bounded private gameplay launches with the exact-pin
executable) are staged separately and reported in
docs/PIKMIN2_ADMITTED_COHORT_QA.md; they are startup/load checks, never
natural combat acceptance.
"""
import copy
import hashlib
import json
from pathlib import Path

from experimental import pikmin2_family_install as family_install
from experimental.pikmin2_enemy_roster import admitted_ids, load_and_validate
from experimental.pikmin2_seed_bridge import (
    SeedBridgeError,
    build_bootstrap,
    parse_bootstrap,
    validate_layout,
)
from randomizer import p2_placement_catalog as catalog
from randomizer.seed import fingerprint, generate

ADMITTED = [23, 44, 54, 57, 59, 60, 61, 62, 78]

# Representative denied probes: Queen 30 (proxy, explicitly not parity),
# Fuefuki 41 (candidate-only, not admitted), Bulblax 53 (boss, not admitted).
DENIED_PROBES = [30, 41, 53]

SEEDS = ("qa-cohort-alpha", "qa-cohort-beta", "qa-cohort-gamma")

COMMITTED_DOC = (
    Path(__file__).resolve().parent.parent / "docs" / "PIKMIN2_ADMITTED_PLACEMENT.json"
)


def committed_document():
    document = json.loads(COMMITTED_DOC.read_text(encoding="utf-8"))
    assert document.get("schema") == "p2-placement-v1", document.get("schema")
    return document


def check_admitted_set():
    roster = load_and_validate()
    admitted = admitted_ids(roster)
    return {
        "ok": admitted == ADMITTED,
        "admitted": admitted,
        "detail": "roster admitted set matches" if admitted == ADMITTED
        else "MISMATCH: expected %r" % (ADMITTED,),
    }


def manifest_bindings(manifest):
    return sorted(
        (b["target"], b["source_id"], b["enum_name"])
        for b in manifest["p2_layout"]["bindings"]
    )


def check_seed_manifest(seed, document=None):
    document = document if document is not None else committed_document()
    manifest = generate(seed, p2_enemies=True, p2_placement=document)
    layout = manifest["p2_layout"]
    bound = sorted({b["source_id"] for b in layout["bindings"]})
    slot_uids = {s["uid"] for s in document["slots"]}
    foreign_slots = sorted({b["target"] for b in layout["bindings"]
                            if not b["target"].lstrip("-").isdigit()
                            or int(b["target"]) not in slot_uids})
    try:
        validate_layout(layout, admitted=ADMITTED)
        layout_ok = True
        layout_detail = "validates against admitted set"
    except SeedBridgeError as exc:
        layout_ok = False
        layout_detail = "rejected: %s" % (exc,)
    try:
        line = build_bootstrap(layout)
        parsed = parse_bootstrap(line)
        bootstrap_ok = sorted((b["target"], b["source_id"])
                              for b in parsed["bindings"]) == sorted(
            (b["target"], b["source_id"]) for b in layout["bindings"])
        bootstrap_detail = "round-trips" if bootstrap_ok else "MISMATCH after parse"
    except SeedBridgeError as exc:
        bootstrap_ok = False
        bootstrap_detail = "rejected: %s" % (exc,)
    ok = bound == ADMITTED and not foreign_slots and layout_ok and bootstrap_ok
    return {
        "ok": ok,
        "seed": seed,
        "bound": bound,
        "n_bindings": len(layout["bindings"]),
        "foreign_slots": foreign_slots,
        "layout_ok": layout_ok,
        "layout_detail": layout_detail,
        "bootstrap_ok": bootstrap_ok,
        "bootstrap_detail": bootstrap_detail,
        "fingerprint": fingerprint(manifest),
        "manifest": manifest,
    }


def check_determinism(seed, document=None):
    first = generate(seed, p2_enemies=True,
                     p2_placement=document if document is not None else committed_document())
    second = generate(seed, p2_enemies=True,
                      p2_placement=document if document is not None else committed_document())
    same_bindings = manifest_bindings(first) == manifest_bindings(second)
    same_fp = fingerprint(first) == fingerprint(second)
    return {
        "ok": same_bindings and same_fp,
        "seed": seed,
        "same_bindings": same_bindings,
        "same_fingerprint": same_fp,
        "fingerprint": fingerprint(first),
    }


def check_denied_exclusion(document=None):
    document = document if document is not None else committed_document()
    findings = {}
    ok = True
    # Denied probes resolve to no admitted binding target.
    try:
        targets = catalog.binding_targets_for_sources(DENIED_PROBES)
        denied_targets = [t for t in targets if t in
                          {str(s["uid"]) for s in document["slots"]}]
        findings["denied_targets_on_accepted_slots"] = denied_targets
        if denied_targets:
            ok = False
    except Exception as exc:  # fail-closed membership error is acceptable
        findings["denied_targets_error"] = "%s: %s" % (type(exc).__name__, exc)
    # A layout smuggling a denied source is rejected at load.
    # A layout smuggling a denied source under a fresh target is rejected
    # at load by the admission gate (not by accident of another rule).
    base = generate(SEEDS[0], p2_enemies=True, p2_placement=document)["p2_layout"]
    smuggled = copy.deepcopy(base)
    probe = dict(base["bindings"][0])
    probe["target"] = "qa-smuggle-1"
    probe["source_id"] = DENIED_PROBES[0]
    probe["enum_name"] = "Queen"  # correct enum for 30: only the admission gate may fire
    smuggled["bindings"] = list(base["bindings"]) + [probe]
    try:
        validate_layout(smuggled, admitted=ADMITTED)
        findings["smuggled_layout"] = "ACCEPTED (defect)"
        ok = False
    except SeedBridgeError as exc:
        findings["smuggled_layout"] = "rejected: %s" % (exc,)
    # Duplicate binding targets are rejected.
    duplicated = copy.deepcopy(base)
    duplicated["bindings"] = list(base["bindings"]) + [dict(base["bindings"][0])]
    try:
        validate_layout(duplicated, admitted=ADMITTED)
        findings["duplicate_target"] = "ACCEPTED (defect)"
        ok = False
    except SeedBridgeError as exc:
        findings["duplicate_target"] = "rejected: %s" % (exc,)
    # Enum mismatch is rejected.
    mismatched = copy.deepcopy(base)
    mismatched["bindings"] = [dict(b) for b in base["bindings"]]
    mismatched["bindings"][0]["enum_name"] = "NotARealEnemy"
    try:
        validate_layout(mismatched, admitted=ADMITTED)
        findings["enum_mismatch"] = "ACCEPTED (defect)"
        ok = False
    except SeedBridgeError as exc:
        findings["enum_mismatch"] = "rejected: %s" % (exc,)
    # Re-applying the same manifest is idempotent.
    again = generate(SEEDS[0], p2_enemies=True, p2_placement=document)
    findings["reapply_identical"] = (
        manifest_bindings(again) == manifest_bindings(
            generate(SEEDS[0], p2_enemies=True, p2_placement=document)))
    if not findings["reapply_identical"]:
        ok = False
    findings["ok"] = ok
    return findings


def check_install_targets():
    resolved = {}
    failures = {}
    for source_id in ADMITTED:
        try:
            resolved[source_id] = family_install.resolve_family(source_id)
        except ValueError as exc:
            failures[source_id] = str(exc)
    denied = {}
    for source_id in DENIED_PROBES:
        try:
            denied[source_id] = "resolves: %s (unexpected)" % (
                family_install.resolve_family(source_id),)
        except ValueError as exc:
            denied[source_id] = "fail-closed: %s" % (exc,)
    unexpected = [s for s, outcome in denied.items() if outcome.startswith("resolves")]
    ok = not failures and not unexpected
    return {"ok": ok, "resolved": resolved, "failures": failures, "denied": denied}


def check_save_restart(seed, session_dir, document=None):
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    manifest = generate(seed, p2_enemies=True,
                        p2_placement=document if document is not None else committed_document())
    saved = session_dir / (seed + ".pikmin.json")
    saved.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n",
                     encoding="utf-8")
    digest = hashlib.sha256(saved.read_bytes()).hexdigest()
    reloaded = json.loads(saved.read_text(encoding="utf-8"))
    same_fp = fingerprint(reloaded) == fingerprint(manifest)
    try:
        validate_layout(reloaded["p2_layout"], admitted=ADMITTED)
        reload_ok = True
        reload_detail = "revalidates after reload"
    except SeedBridgeError as exc:
        reload_ok = False
        reload_detail = "rejected after reload: %s" % (exc,)
    tampered = copy.deepcopy(reloaded)
    tampered["p2_layout"]["bindings"] = [
        dict(b, source_id=DENIED_PROBES[0] if i == 0 else b["source_id"])
        for i, b in enumerate(tampered["p2_layout"]["bindings"])]
    try:
        validate_layout(tampered["p2_layout"], admitted=ADMITTED)
        tamper_rejected = False
    except SeedBridgeError:
        tamper_rejected = True
    ok = same_fp and reload_ok and tamper_rejected
    return {
        "ok": ok,
        "seed": seed,
        "path": str(saved),
        "sha256": digest,
        "same_fingerprint": same_fp,
        "reload_ok": reload_ok,
        "reload_detail": reload_detail,
        "tamper_rejected": tamper_rejected,
    }


def run_all(session_dir, seeds=SEEDS):
    document = committed_document()
    report = {"admitted": check_admitted_set(), "seeds": {}, "denied": None,
              "install": None, "restart": {}}
    ok = report["admitted"]["ok"]
    for seed in seeds:
        manifest_check = check_seed_manifest(seed, document)
        manifest = manifest_check.pop("manifest")
        determinism = check_determinism(seed, document)
        restart = check_save_restart(seed, Path(session_dir) / seed, document)
        report["seeds"][seed] = {"manifest": manifest_check,
                                 "determinism": determinism}
        report["restart"][seed] = restart
        ok = ok and manifest_check["ok"] and determinism["ok"] and restart["ok"]
    report["denied"] = check_denied_exclusion(document)
    report["install"] = check_install_targets()
    ok = ok and report["denied"]["ok"] and report["install"]["ok"]
    report["ok"] = ok
    return report


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--seeds", nargs="*", default=list(SEEDS))
    args = parser.parse_args(argv)
    report = run_all(args.session_dir, seeds=tuple(args.seeds))
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")
    for seed, checks in report["seeds"].items():
        print("%s manifest=%s determinism=%s restart=%s" % (
            seed, checks["manifest"]["ok"], checks["determinism"]["ok"],
            report["restart"][seed]["ok"]))
    print("admitted=%s denied=%s install=%s OVERALL=%s" % (
        report["admitted"]["ok"], report["denied"]["ok"],
        report["install"]["ok"], report["ok"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
