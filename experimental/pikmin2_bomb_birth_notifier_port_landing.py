"""Landing registry for the committed #715 hook-notifier port (issue #719).

Lane bomb-birth-notifier-port-landing, generation 2. Root-only tooling: the
#715 port is consumed READ-ONLY (no re-derivation, no duplication of its nine
files); no family/shared/native edits, no runtime, no ADMIT. Stdlib only.
"""
import argparse
import hashlib
import json
import sys

SCHEMA = "p2-bomb-birth-notifier-port-landing-1"
LANE = "bomb-birth-notifier-port-landing"
ISSUE = 719
GENERATION = 2
PARENT_ISSUE = 586
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

PORT_715 = {
    "lane": "bomb-birth-hook-notifier-port-native",
    "issue": 715,
    "generation": 2,
    "root_base": "ecf5f53a601a3c563bb44339ec7abf4665795451",
    "root_commit": "f807392feef43a145559350406e467136d49de06",
    "native_base": "5d03a79053baa888f8edac380b58ecf65669d3e7",
    "native_commit": "a6ca7bc6842a24bb8c2321f446fcfb8ec94f1b65",
    "native_base_identity": "bomb-birth-engine-hook-native (#677) head",
    "files": [
        {"repo": "root", "path": "docs/PIKMIN2_BOMB_BIRTH_NOTIFIER_PORT.md",
         "blob": "54aa5184575f3b1cf52bd9364c6494e12528d832"},
        {"repo": "root", "path": "experimental/pikmin2_bomb_birth_notifier_port.py",
         "blob": "cbf25b66e01bfa0a6cb32f193e7c5f5e24600e34"},
        {"repo": "root", "path": "scripts/build_p2_bomb_birth_notifier.py",
         "blob": "5dfa8deabf676144cb696da75af0c673968da25b"},
        {"repo": "root", "path": "tests/test_pikmin2_bomb_birth_notifier_port.py",
         "blob": "3cfb013ad5acb01b28491d0edd9183539ad2ea9c"},
        {"repo": "native", "path": "pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp",
         "blob": "c73605f19294f6282c4d56813a008720a9034610", "changed": False},
        {"repo": "native", "path": "pc_port/pc_p2_bomb_notifier.h",
         "blob": "1e92f96f20a0b5483ca9b01e9dbc2ac2e19b013f", "changed": True},
        {"repo": "native", "path": "pc_port/pc_p2_bomb_notifier.cpp",
         "blob": "23cefec68782757bd5af802abaafdfdcc7b05039", "changed": True},
        {"repo": "native", "path": "CMakeLists.txt",
         "blob": "881d5bc7cf0b7f789c03c9d7d87c359e47341781", "changed": True},
        {"repo": "native", "path": "tools/p2_bomb_birth_notifier_fixture.cpp",
         "blob": "6e43e8a2b501ae1bdec7171debe420f9d8997c48", "changed": True},
    ],
}

PACKET_186 = {
    "name": "provider-bomb-birth-186-review-packet",
    "issue": 186,
    "items": [
        "engine-bomb-birth-path: additive pc_p2_bomb_birth_hook_notify hook (extern + notify) plus a defined notifier TU",
        "provider-cmake-membership: pc_port/pc_p2_bomb_mgr_birth.cpp in the pikmin_pc target + provider test",
        "dynamic-bridge-source-93: approved but unlanded integrator work (out of scope)",
    ],
}

INTEGRATED = {
    "691": {
        "lane": "bomb-engine-birth-real-native",
        "issue": 691,
        "root_commit": "1fcaf074d6c0c6e83f1a681e2503cacba9b8ad76",
        "native_commit": "95172ea40ea27c436f3117bca97794bfb3b60ebc",
        "validation_sha256": "97113e0233619da524c73d081eb2447a6fdfd6766ae9f07c8afb650dea249169",
    },
    "700": {
        "lane": "bomb-joint-matrix-capture-native",
        "issue": 700,
        "root_commit": "347526301a4a91df673a631c7d7ab0579e5823a9",
        "native_commit": "58df488eb1d9582b0ef625d46874f3427c18628d",
        "validation_sha256": "68cf75cedb061e5c0d81670f7858ee85025bec783d28462fb1b30740d40a9ed8",
    },
    "703": {
        "lane": "provider-bomb-mgr-birth-landing",
        "issue": 703,
        "root_commit": "f985d17cb6da301c073923c57cd283c5ebe78c32",
        "native_commit": None,
        "validation_sha256": "6c40b5365760c175c616ab28b09f3e5b60046f155df9f98c74c752d2449b4f10",
    },
}

EVIDENCE_715 = {
    "pytest": {
        "path": "output/workflow/autofill/prerequisites/bomb-birth-hook-notifier-port-native/out/pytest.log",
        "sha256": "c599650c41614e5ddd3dfc1f0d95516046b6d20a638a21e1cfadc2a796ad4eea"},
    "verify": {
        "path": "output/workflow/autofill/prerequisites/bomb-birth-hook-notifier-port-native/out/verify.log",
        "sha256": "a2fadd724ed14de1cc1f286999cfb587c746b476b48ddc65fdb586f4fe7bd64e"},
    "providerlog": {
        "path": "output/workflow/autofill/prerequisites/bomb-birth-hook-notifier-port-native/out/ctest-provider.log",
        "sha256": "55cc31544bb93d4f1365979ebcfff2396e4bff30dddd26070895f4b990325e21"},
    "buildlog": {
        "path": "output/workflow/autofill/prerequisites/bomb-birth-hook-notifier-port-native/out/leased-build-1789650056543684.log",
        "sha256": "0a58ba23b71af2e7c2720db7973dd3dc77d01f5de1c6b799dbb7d581af14ba69"},
    "buildrecord": {
        "path": "output/workflow/autofill/prerequisites/bomb-birth-hook-notifier-port-native/out/build-record-1789650056543684.json",
        "sha256": "af514a90b92416959559a97551523e32b125b80f94dd4e337860557da8cf3b6c"},
    "buildrecord_on": {
        "path": "output/workflow/autofill/prerequisites/bomb-birth-hook-notifier-port-native/out/build-record-1789651245875095.json",
        "sha256": "860de17de10de8836a4391691df6f4cb790c7e133fd7099b39d0064a27aa37ae"},
    "guard": {
        "path": "scripts/p2_fixture_captain_guard.h",
        "sha256": GUARD_SHA256},
    "doc": {
        "path": "output/workflow/autofill/prerequisites/bomb-birth-hook-notifier-port-native-root/docs/PIKMIN2_BOMB_BIRTH_NOTIFIER_PORT.md",
        "sha256": "974f3feacc376f8026b5dd4833a2ac80353bf63c95b5e9de70cf8064da99b18d"},
}

DOWNSTREAM = {
    "lane": "enemy-bombotakara93-payload",
    "issue": 573,
    "consumer_evidence": {
        "path": "output/workflow/autofill/enemy-bombotakara93-payload/gen15-note.md",
        "sha256": "77e54c1944028997d97e2733e957f9060d1d93a589ffa8e55ae0a82f81b254df"},
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
        "port_715": {
            "lane": PORT_715["lane"],
            "issue": PORT_715["issue"],
            "generation": PORT_715["generation"],
            "root_base": PORT_715["root_base"],
            "root_commit": PORT_715["root_commit"],
            "native_base": PORT_715["native_base"],
            "native_commit": PORT_715["native_commit"],
            "native_base_identity": PORT_715["native_base_identity"],
            "files": [dict(f) for f in PORT_715["files"]],
        },
        "packet_186": {
            "name": PACKET_186["name"],
            "issue": PACKET_186["issue"],
            "items": list(PACKET_186["items"]),
        },
        "integrated": {k: dict(v) for k, v in INTEGRATED.items()},
        "evidence_715": {k: dict(v) for k, v in EVIDENCE_715.items()},
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
        "port_commits": {
            "root": registry["port_715"]["root_commit"],
            "native": registry["port_715"]["native_commit"],
        },
        "port_file_blobs": [
            {"repo": f["repo"], "path": f["path"], "blob": f["blob"],
             "changed": f.get("changed", True)}
            for f in registry["port_715"]["files"]
        ],
        "packet_186": dict(registry["packet_186"]),
        "integration_pins": {
            key: {"root": value["root_commit"], "native": value["native_commit"]}
            for key, value in registry["integrated"].items()
        },
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
    port = registry.get("port_715")
    if not isinstance(port, dict):
        problems.append("bad-port-715")
    else:
        for key in ("root_base", "root_commit", "native_base", "native_commit",
                    "native_base_identity"):
            if port.get(key) != PORT_715[key]:
                problems.append("port-pin-changed-" + key)
        files = port.get("files")
        if not isinstance(files, list) or len(files) != 9:
            problems.append("bad-port-files")
        else:
            for want, got in zip(PORT_715["files"], files):
                if got != want:
                    problems.append("port-blob-changed-" + want["path"])
                    break
    packet = registry.get("packet_186")
    if (not isinstance(packet, dict) or packet.get("issue") != 186
            or packet.get("items") != PACKET_186["items"]):
        problems.append("bad-packet-186")
    integrated = registry.get("integrated")
    if not isinstance(integrated, dict) or set(integrated) != {"691", "700", "703"}:
        problems.append("bad-integrated")
    else:
        for key in ("691", "700", "703"):
            for field in ("root_commit", "native_commit", "validation_sha256"):
                if integrated[key].get(field) != INTEGRATED[key][field]:
                    problems.append("integration-pin-changed-" + key + "-" + field)
    evidence = registry.get("evidence_715")
    if not isinstance(evidence, dict) or set(evidence) != set(EVIDENCE_715):
        problems.append("bad-evidence-715")
    else:
        for key, want in EVIDENCE_715.items():
            if evidence[key] != want:
                problems.append("evidence-changed-" + key)
                break
    downstream = registry.get("downstream")
    if (not isinstance(downstream, dict) or downstream.get("issue") != 573
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
    parser = argparse.ArgumentParser(description="Bomb birth notifier port landing registry")
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
        print("NOTIFIER_LANDING_PASS files=%d evidence=%d integrated=%d" % (
            len(registry["port_715"]["files"]), len(registry["evidence_715"]),
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
