"""Diagnosis registry for the PIKI BIRTH FAILED panic in the #567 trial boot (issue #721).

Lane piki-birth-panic-diagnosis, generation 2. Root-only tooling: the engine
sources and the #567 logs are consumed READ-ONLY (no duplication, no
family/shared/native edits); no runtime, no ADMIT. Stdlib only.

Method: adjudicate the null-birth cause from pinned log + code facts.
birth() (pikiMgr.cpp:33-53) has exactly two silent-or-diagnosed null sources:
the field cap (silent) and the object pool (MonoObjectMgr::birth,
objectMgr.cpp:331-353, PRINT diagnostics gated by gsys->mTogglePrint, default
FALSE). Onion counts are checked first; a missing field-cap pin forces
UNDETERMINED rather than a guess.
"""
import argparse
import hashlib
import json
import sys

SCHEMA = "p2-piki-birth-panic-diagnosis-1"
LANE = "piki-birth-panic-diagnosis"
ISSUE = 721
GENERATION = 2
PARENT_ISSUE = 586
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

NATIVE_COMMIT = "c549997e7bdf66fb09c0f0756c56e65fdad55861"
TRIAL_EXE_SHA256 = "ea20973846b43afaa199b28c48f95558fcf29d1c98a436a2bebbcab2f19bf4fc"

CODE_PINS = [
    {"path": "src/plugPikiKando/goalItem.cpp", "lines": "424-441",
     "blob": "7e4a4fee20bb13720d6ee8fe16bc1e9fce28d349",
     "role": "null-birth site: pikiMgr->birth() null -> ERROR PIKI BIRTH FAILED"},
    {"path": "src/plugPikiKando/pikiMgr.cpp", "lines": "33-53",
     "blob": "173cc627be61179fc4d2e41658a0c8e95aa1eacb",
     "role": "birth(): silent field-cap gate then pool birth"},
    {"path": "src/plugPikiKando/objectMgr.cpp", "lines": "209-231,331-353",
     "blob": "357ab263dc5ab41940d26dd0fa190b01b42f1306",
     "role": "pool birth: null iff pool empty/full; diagnostics PRINT-gated"},
    {"path": "src/plugPikiKando/gameCoreSection.cpp", "lines": "1009-1027,1460-1470",
     "blob": "63d7c24efad2889bf687035992d281e6ae35fa74",
     "role": "sole pool creation site pikiMgr->create(limit+2); field-cap write"},
    {"path": "src/plugPikiColin/newPikiGame.cpp", "lines": "2021,2271-2276",
     "blob": "c234034a12e830dcfb785bd16124ed58a539d328",
     "role": "stage setup calls initStage; first update runs finalSetup"},
    {"path": "src/plugPikiColin/gameSetup.cpp", "lines": "250,309,316-324",
     "blob": "81fa203fb6d24d2d09afe75db769172c687cf2f0",
     "role": "challenge boot writes 20 Leaf x 3 colors into Onion counts"},
    {"path": "src/plugPikiKando/itemMgr.cpp", "lines": "1384-1395",
     "blob": "cbfd6ee47cdd0ba37519793945d54e0d0f8b01c4",
     "role": "container exit count sums queued dispenses only"},
    {"path": "src/sysDolphin/system.cpp", "lines": "787",
     "blob": "6f90a1df51eee219bc22491bd31a50c19eb0697f",
     "role": "mTogglePrint defaults FALSE: PRINT diagnostics suppressed"},
    {"path": "src/plugPikiColin/moviePlayer.cpp", "lines": "716-727",
     "blob": "1207e079436eb604352473a13c616b41451fbdf2",
     "role": "documents that PRINT obeys gsys->mTogglePrint"},
    {"path": "src/sysDolphin/sysNew.cpp", "lines": "104-155",
     "blob": "cc26956be5d58b690e3e22d0d366e38c4b6a5073",
     "role": "plain new bypasses memStat: pool state unreadable from memStat"},
    {"path": "src/plugPikiKando/aiConstants.cpp", "lines": "22-35",
     "blob": "91419377f690c685a4a864d8869568331584c2e1",
     "role": "field-cap constant loads from bin; written once per setup"},
    {"path": "pc_port/settings/pc_settings.cpp", "lines": "95,133,2724-2728",
     "blob": "d9ba012bc7665c77fe156edafadc1e500702601f",
     "role": "piki limit defaults to 100 in every path"},
]

LOG_FACTS = {
    "runlog": {
        "path": "output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-trial-runtime-acceptance-output/run-chal4/native.log",
        "sha256": "26f5cec70c9975abd4cbf9e6f518061806df8c47f4177c81549754fa7a0e0d80"},
    "report": {
        "path": "output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-trial-runtime-acceptance-output/report.md",
        "sha256": "8a53721829131431b599bd26ca2ea7e8d33dd3f6e7364a1cce64461ec9b1fdf4"},
    "provenance": {
        "path": "output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-trial-runtime-acceptance-output/build-provenance.json",
        "sha256": "b65687625a113260c43531b8d5d2ed20715853594495b3d2c35a56e110faff77"},
    "acceptance": {
        "path": "output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-trial-runtime-acceptance-output/acceptance-chal4.json",
        "sha256": "4064dfa7a3352b878aa3ed30f7c23977b7ec3c17c313183d0abea35c1c9a48fa"},
    "lines": {
        "layout_ready": 236,
        "generators_spawned": [635, 636],
        "teki_heap": 679,
        "movie_reset": [766, 767],
        "panic": 769,
    },
    "absent_markers": ["2d err", "CONTAINER", "numObjects", "no empty slot"],
}

TRIAL_FACTS = {
    "first_birth_null": True,
    "onion_counts_wired": True,
    "onion_leaf_total": 60,
    "max_pikis": 100,
    "total_pikis_estimate": 19,
    "generators_spawned": True,
    "squad_observed": False,
}

CAUSE_POOL_EMPTY = "POOL_EMPTY"
CAUSE_FIELD_CAP = "FIELD_CAP"
CAUSE_ONION_COUNTS = "ONION_COUNTS"
CAUSE_UNDETERMINED = "UNDETERMINED"

DIAGNOSIS = {
    "cause": CAUSE_POOL_EMPTY,
    "statement": ("First-dispense birth() null from the object-pool path: the "
                  "field cap (100) cannot fire on a first-dispense total near "
                  "19, and the Onion counts are wired (60 Leaf). The pool "
                  "diagnostics are PRINT-gated off, and memStat cannot show "
                  "pool state (plain new bypasses it), so the pool path is "
                  "identified by elimination over pinned facts, not by a log line."),
    "fix_owner": ("Shared piki-birth owner via #186 hook review (piki birth "
                  "path, newPikiGame.cpp) + #52 campaign contract"),
    "fix_files": [
        "src/plugPikiKando/gameCoreSection.cpp:1009-1027 (ensure pikiMgr->create runs on the challenge path)",
        "src/plugPikiColin/newPikiGame.cpp:2021,2271-2276 (initStage/finalSetup order on challenge setup)",
        "src/plugPikiKando/objectMgr.cpp:331-353 + src/plugPikiKando/pikiMgr.cpp:33-53 (toggle-independent birth-failure diagnostics)",
        "src/plugPikiKando/goalItem.cpp:424-441 (halt-site pool/cap context)",
    ],
}

DOWNSTREAM = {
    "lane": "p1-challenge-trial-runtime-acceptance",
    "issue": 567,
}

GATES = ("identity_spawn", "movement_animation", "attacks_receivers",
         "death_corpse", "transport_reward", "cleanup_reentry")


def adjudicate(facts):
    """Return the null-birth cause for observed facts; UNDETERMINED unless pinned."""
    if not isinstance(facts, dict) or facts.get("first_birth_null") is not True:
        return CAUSE_UNDETERMINED
    if facts.get("onion_counts_wired") is not True:
        return CAUSE_ONION_COUNTS
    maximum = facts.get("max_pikis")
    total = facts.get("total_pikis_estimate")
    if not isinstance(maximum, int) or not isinstance(total, int):
        return CAUSE_UNDETERMINED
    if total >= maximum:
        return CAUSE_FIELD_CAP
    return CAUSE_POOL_EMPTY


def build_registry():
    """The validated machine-readable diagnosis registry."""
    cause = adjudicate(dict(TRIAL_FACTS))
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "generation": GENERATION,
        "native_commit": NATIVE_COMMIT,
        "trial_exe_sha256": TRIAL_EXE_SHA256,
        "code_pins": [dict(pin) for pin in CODE_PINS],
        "log_facts": {
            "runlog": dict(LOG_FACTS["runlog"]),
            "report": dict(LOG_FACTS["report"]),
            "provenance": dict(LOG_FACTS["provenance"]),
            "acceptance": dict(LOG_FACTS["acceptance"]),
            "lines": {"layout_ready": LOG_FACTS["lines"]["layout_ready"],
                      "generators_spawned": list(LOG_FACTS["lines"]["generators_spawned"]),
                      "teki_heap": LOG_FACTS["lines"]["teki_heap"],
                      "movie_reset": list(LOG_FACTS["lines"]["movie_reset"]),
                      "panic": LOG_FACTS["lines"]["panic"]},
            "absent_markers": list(LOG_FACTS["absent_markers"]),
        },
        "trial_facts": dict(TRIAL_FACTS),
        "diagnosis": {
            "cause": cause,
            "statement": DIAGNOSIS["statement"],
            "fix_owner": DIAGNOSIS["fix_owner"],
            "fix_files": list(DIAGNOSIS["fix_files"]),
        },
        "downstream": dict(DOWNSTREAM),
        "guard_sha256": GUARD_SHA256,
        "runtime_claim": False,
        "gates": {g: "UNTESTED" for g in GATES},
    }


def build_packet(registry):
    """The hashed packet naming exact pins and downstream consumer #567."""
    return {
        "schema": SCHEMA,
        "kind": "diagnosis",
        "lane": registry["lane"],
        "issue": registry["issue"],
        "native_commit": registry["native_commit"],
        "trial_exe_sha256": registry["trial_exe_sha256"],
        "cause": registry["diagnosis"]["cause"],
        "statement": registry["diagnosis"]["statement"],
        "fix_owner": registry["diagnosis"]["fix_owner"],
        "fix_files": list(registry["diagnosis"]["fix_files"]),
        "downstream": dict(registry["downstream"]),
        "gates": dict(registry["gates"]),
        "guard_sha256": registry["guard_sha256"],
    }


def validate_registry(registry):
    """Return a list of refusal reasons; empty means the registry is valid."""
    problems = []
    if not isinstance(registry, dict):
        return ["registry-must-be-dict"]
    if registry.get("schema") != SCHEMA:
        problems.append("bad-schema")
    if (registry.get("lane"), registry.get("issue"), registry.get("generation")) != (LANE, ISSUE, GENERATION):
        problems.append("bad-identity")
    if registry.get("native_commit") != NATIVE_COMMIT:
        problems.append("bad-native-commit")
    if registry.get("trial_exe_sha256") != TRIAL_EXE_SHA256:
        problems.append("bad-trial-exe")
    pins = registry.get("code_pins")
    if not isinstance(pins, list) or len(pins) != len(CODE_PINS):
        problems.append("bad-code-pins")
    else:
        for want, got in zip(CODE_PINS, pins):
            if got != want:
                problems.append("code-pin-changed-" + want["path"])
                break
    facts = registry.get("log_facts")
    if not isinstance(facts, dict):
        problems.append("bad-log-facts")
    else:
        for key in ("runlog", "report", "provenance", "acceptance"):
            if facts.get(key) != LOG_FACTS[key]:
                problems.append("log-fact-changed-" + key)
                break
        else:
            if facts.get("lines", {}).get("panic") != 769:
                problems.append("bad-panic-line")
    if registry.get("trial_facts") != TRIAL_FACTS:
        problems.append("bad-trial-facts")
    diagnosis = registry.get("diagnosis")
    expected_cause = adjudicate(dict(TRIAL_FACTS))
    if not isinstance(diagnosis, dict) or diagnosis.get("cause") != expected_cause:
        problems.append("diagnosis-mismatch-cause")
    elif diagnosis.get("cause") != CAUSE_POOL_EMPTY:
        problems.append("diagnosis-not-pinpointed")
    else:
        for key in ("statement", "fix_owner"):
            if diagnosis.get(key) != DIAGNOSIS[key]:
                problems.append("diagnosis-changed-" + key)
                break
        else:
            if diagnosis.get("fix_files") != DIAGNOSIS["fix_files"]:
                problems.append("diagnosis-changed-fix-files")
    if registry.get("downstream") != DOWNSTREAM:
        problems.append("bad-downstream")
    if registry.get("guard_sha256") != GUARD_SHA256:
        problems.append("bad-guard")
    if registry.get("runtime_claim") is not False:
        problems.append("no-runtime-claims")
    gates = registry.get("gates")
    if not isinstance(gates, dict) or set(gates) != set(GATES):
        problems.append("bad-gates")
    return problems


def registry_sha256(registry):
    return hashlib.sha256(
        json.dumps(registry, indent=1, sort_keys=True).encode("utf-8")).hexdigest()


def dump(obj):
    return json.dumps(obj, indent=1, sort_keys=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="PIKI BIRTH panic diagnosis registry")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--registry-out", default=None)
    parser.add_argument("--packet-out", default=None)
    args = parser.parse_args(argv)
    registry = build_registry()
    problems = validate_registry(registry)
    if problems:
        for problem in problems:
            print("REFUSED reason=%s" % problem)
        return 1
    packet = build_packet(registry)
    if args.check or (args.registry_out is None and args.packet_out is None):
        print("PANIC_DIAGNOSIS cause=%s pins=%d" % (
            registry["diagnosis"]["cause"], len(registry["code_pins"])))
    if args.registry_out:
        with open(args.registry_out, "w", encoding="utf-8") as f:
            f.write(dump(registry))
        print("registry=%s sha256=%s" % (args.registry_out, registry_sha256(registry)))
    if args.packet_out:
        with open(args.packet_out, "w", encoding="utf-8") as f:
            f.write(dump(packet))
        print("packet=%s sha256=%s" % (
            args.packet_out,
            hashlib.sha256(dump(packet).encode("utf-8")).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
