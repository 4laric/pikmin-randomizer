"""Landing registry for the committed #710 host-mode engine hook (issue #714).

Lane challenge-hostmode-hook-landing, generation 2. Root-only tooling: the
#710 hook is consumed READ-ONLY (no re-derivation, no duplication of its nine
files); no family/shared/native edits, no runtime, no ADMIT. Stdlib only.
"""
import argparse
import hashlib
import json
import sys

SCHEMA = "p2-challenge-hostmode-hook-landing-1"
LANE = "challenge-hostmode-hook-landing"
ISSUE = 714
GENERATION = 2
PARENT_ISSUE = 586
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

HOOK_710 = {
    "lane": "challenge-hostmode-engine-hook-native",
    "issue": 710,
    "generation": 2,
    "root_base": "ecf5f53a601a3c563bb44339ec7abf4665795451",
    "root_commit": "3e3cdd1d93a3b0196cdd19202ab9eb922a80e9d8",
    "native_base": "78b67349b50a729a53caec0006d2ebbc70aa5308",
    "native_commit": "db245877a090d017a09e28ac1c144e6497857227",
    "files": [
        {"repo": "root", "path": "docs/PIKMIN2_CHALLENGE_HOST_RUNTIME.md",
         "blob": "fa94ec9ad642892716a566cbb9e3ac3939339f61"},
        {"repo": "root", "path": "experimental/pikmin2_challenge_host_runtime.py",
         "blob": "189cc19becf1fa5dc67a288080bab3ac90433ec3"},
        {"repo": "root", "path": "scripts/build_p2_challenge_host_runtime.py",
         "blob": "fa5e348bf68657cbc78ffd92c306979aa418e520"},
        {"repo": "root", "path": "tests/test_pikmin2_challenge_host_runtime.py",
         "blob": "a114f88a3255190337fd7e116a039bc55ec096f7"},
        {"repo": "native", "path": "pc_port/pc_p2_challenge_runtime.h",
         "blob": "d391d1173cc28255614c08ccfa31afcc8aec78d1"},
        {"repo": "native", "path": "pc_port/pc_p2_challenge_runtime.cpp",
         "blob": "06a25bd1a0a7b4520b52c71d348a9a1a4b094591"},
        {"repo": "native", "path": "pc_port/pc_bbft.cpp",
         "blob": "0deeb0b5ef87656317dcedfeccb376f7d760660f"},
        {"repo": "native", "path": "CMakeLists.txt",
         "blob": "8f299d3b9b1aed6e1dc9dcc59968ece03e6a45e9"},
        {"repo": "native", "path": "tools/p2_challenge_host_runtime_fixture.cpp",
         "blob": "488aa620ae99bf657869e08037915ab4b98a4170"},
    ],
}

INTEGRATED = {
    "701": {
        "lane": "challenge-content-loading-validate-land-native",
        "issue": 701,
        "root_commit": "806952dbe60e11f5bb10e957b5c5898066957cd7",
        "native_commit": "f91c21438163e3fa21862074fb2eec62a19c0e32",
        "validation_sha256": "23fbf31d8325fb5edb48fb91c95a77752164c4ecff812a7bc9cf6284b3d2d8aa01e7",
    },
    "702": {
        "lane": "host-mode-runtime-wiring-native",
        "issue": 702,
        "root_commit": "75dddcd2fa96ea4e52ba4c899e7a21f8a7d2a499",
        "native_commit": "78b67349b50a729a53caec0006d2ebbc70aa5308",
        "validation_sha256": "7bf92818fc10df8a346c86ef19e7bd34f07c8375b799f7faa3a48b91fa80def8",
    },
}

EVIDENCE_710 = {
    "pytest": {
        "path": "output/workflow/autofill/prerequisites/challenge-hostmode-engine-hook-native/out/pytest.log",
        "sha256": "7379ba0a9a6a7be06985483276380bcaf0885d9e259874cb7eca98269a84e348"},
    "verify": {
        "path": "output/workflow/autofill/prerequisites/challenge-hostmode-engine-hook-native/out/verify.log",
        "sha256": "d5d797f75e6abaad42d9b07b8363c0322f642dd8d4d2a80e613a812a6863eccd"},
    "fixturecompile": {
        "path": "output/workflow/autofill/prerequisites/challenge-hostmode-engine-hook-native/out/fixture-compile.log",
        "sha256": "85a3588cef1facfefee408eb3e2171778aee55a97c1115968aec7880d4a30b67"},
    "buildlog": {
        "path": "output/workflow/autofill/prerequisites/challenge-hostmode-engine-hook-native/out/leased-build-1789647583584557.log",
        "sha256": "9d89a5fc1b2d995c526c10ebe1a6d7fd4be3fda6b557dcdce2f8d5125807cbb4"},
    "buildrecord": {
        "path": "output/workflow/autofill/prerequisites/challenge-hostmode-engine-hook-native/out/build-record-1789647583584557.json",
        "sha256": "bacfe9ae678db92636da129efc9899b3b7cd9ee658f886ea4cb18ef67ab8e27d"},
    "buildrecord_on": {
        "path": "output/workflow/autofill/prerequisites/challenge-hostmode-engine-hook-native/out/build-record-1789647778252280.json",
        "sha256": "182f5d6c0660da4914bb06787cf12dcdd490080a0155e72327c599ac22435343"},
    "headedrun": {
        "path": "output/workflow/autofill/prerequisites/challenge-hostmode-engine-hook-native/out/headed-run.log",
        "sha256": "e11ed17a2bdca022ab9a4abca4c74406715c68ead2f292612cf6e8c5503fc504"},
    "guard": {
        "path": "scripts/p2_fixture_captain_guard.h",
        "sha256": GUARD_SHA256},
    "doc": {
        "path": "output/workflow/autofill/prerequisites/challenge-hostmode-engine-hook-native-root/docs/PIKMIN2_CHALLENGE_HOST_RUNTIME.md",
        "sha256": "b0815c8c399f2192d9ba98a05f3aa577f882c8211d3c23f5e4521fedabfe01b0"},
}

HOOK_186 = {
    "status": "review pending",
    "items": [
        "Shared per-tick hook: null-by-default engine bridge invoked from pc_bbft_update()",
        "CMake first-class target: pc_p2_challenge_runtime.cpp + pc_p2_challenge_mode.cpp in pikmin_pc",
    ],
}

DOWNSTREAM = {
    "lane": "p2-challenge-ch-abem-leafchappy-p1",
    "issue": 550,
    "consumer_evidence": {
        "path": "output/workflow/autofill/planning-shards/challenge-2/prepared/p1-leafchappy-output/consumer-verification-90e1a0a5.md",
        "sha256": "9ceb1571c8fbbcb2f2beea33cf8f02bdc039b33ffb8d1529c01f10901bc89a93"},
}

GATES = ("identity_spawn", "movement_animation", "attacks_receivers",
         "death_corpse", "transport_reward", "cleanup_reentry")


def build_registry():
    """The validated machine-readable landing registry."""
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "generation": GENERATION,
        "hook_710": {
            "lane": HOOK_710["lane"],
            "issue": HOOK_710["issue"],
            "generation": HOOK_710["generation"],
            "root_base": HOOK_710["root_base"],
            "root_commit": HOOK_710["root_commit"],
            "native_base": HOOK_710["native_base"],
            "native_commit": HOOK_710["native_commit"],
            "files": [dict(f) for f in HOOK_710["files"]],
        },
        "integrated": {k: dict(v) for k, v in INTEGRATED.items()},
        "evidence_710": {k: dict(v) for k, v in EVIDENCE_710.items()},
        "hook_186": {
            "status": HOOK_186["status"],
            "items": list(HOOK_186["items"]),
        },
        "downstream": {
            "lane": DOWNSTREAM["lane"],
            "issue": DOWNSTREAM["issue"],
            "consumer_evidence": dict(DOWNSTREAM["consumer_evidence"]),
        },
        "guard_sha256": GUARD_SHA256,
        "runtime_claim": False,
        "gates": {g: "UNTESTED" for g in GATES},
    }


def build_packet(registry):
    """The hashed integration-ready packet for the single-writer integrator + #186 reviewer."""
    return {
        "schema": SCHEMA,
        "kind": "integration-ready",
        "lane": registry["lane"],
        "issue": registry["issue"],
        "hook_commits": {
            "root": registry["hook_710"]["root_commit"],
            "native": registry["hook_710"]["native_commit"],
        },
        "hook_file_blobs": [
            {"repo": f["repo"], "path": f["path"], "blob": f["blob"]}
            for f in registry["hook_710"]["files"]
        ],
        "integration_pins": {
            "701": {"root": registry["integrated"]["701"]["root_commit"],
                    "native": registry["integrated"]["701"]["native_commit"]},
            "702": {"root": registry["integrated"]["702"]["root_commit"],
                    "native": registry["integrated"]["702"]["native_commit"]},
        },
        "hook_186": dict(registry["hook_186"]),
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
    hook = registry.get("hook_710")
    if not isinstance(hook, dict):
        problems.append("bad-hook-710")
    else:
        for key in ("root_base", "root_commit", "native_base", "native_commit"):
            if hook.get(key) != HOOK_710[key]:
                problems.append("hook-pin-changed-" + key)
        files = hook.get("files")
        if not isinstance(files, list) or len(files) != 9:
            problems.append("bad-hook-files")
        else:
            for want, got in zip(HOOK_710["files"], files):
                if got != want:
                    problems.append("hook-blob-changed-" + want["path"])
                    break
    integrated = registry.get("integrated")
    if not isinstance(integrated, dict) or set(integrated) != {"701", "702"}:
        problems.append("bad-integrated")
    else:
        for key in ("701", "702"):
            for field in ("root_commit", "native_commit", "validation_sha256"):
                if integrated[key].get(field) != INTEGRATED[key][field]:
                    problems.append("integration-pin-changed-" + key + "-" + field)
    evidence = registry.get("evidence_710")
    if not isinstance(evidence, dict) or set(evidence) != set(EVIDENCE_710):
        problems.append("bad-evidence-710")
    else:
        for key, want in EVIDENCE_710.items():
            if evidence[key] != want:
                problems.append("evidence-changed-" + key)
                break
    review = registry.get("hook_186")
    if (not isinstance(review, dict) or review.get("status") != "review pending"
            or review.get("items") != HOOK_186["items"]):
        problems.append("bad-hook-186")
    downstream = registry.get("downstream")
    if (not isinstance(downstream, dict) or downstream.get("issue") != 550
            or downstream.get("lane") != DOWNSTREAM["lane"]
            or downstream.get("consumer_evidence") != DOWNSTREAM["consumer_evidence"]):
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
    parser = argparse.ArgumentParser(description="Challenge host-mode hook landing registry")
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
        print("HOOK_LANDING_PASS files=%d evidence=%d integrated=%d" % (
            len(registry["hook_710"]["files"]), len(registry["evidence_710"]),
            len(registry["integrated"])))
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
