"""#186 shared-hook review packet for the integrated Bomb birth candidates (#186).

Produces the machine-readable review packet the single-writer integrator
consumes to land (or refuse with exact required changes) the Bomb birth
provider for the stranded consumer `enemy-bombotakara93-payload` (#573).

It verifies, read-only, the integrated bomb-birth candidates
(#666/#677/#684/#691/#700/#703) and emits the three #186-gated items:

  1. engine Bomb birth path (retail manager creation switch + additive hook)
  2. provider CMake membership (maintained registration)
  3. dynamic-bridge source 93 (BombOtakara93 payload binding)

Each item carries exact file paths and SHA-256 pins for the verified candidate
artifacts plus a code-derived verdict: APPROVED when the maintained line
already carries the integration, otherwise CHANGES_REQUIRED with the exact
missing change. An approval is never invented and nothing is simulated.

Fail-closed: a missing or hash-mismatched candidate artifact raises DriftError;
a packet whose recorded verdicts do not match a fresh code review is rejected.
No shared/native/CMake/provider edits, no runtime, no ADMIT.
"""
import hashlib
import json
from pathlib import Path

SCHEMA = "p2-bomb-birth-186-review-packet-v1"

# Integrated candidates, verified fresh from the canonical registry
# (all integrated_at set except the #616 provider, which #703 validates).
CANDIDATES = {
    666: {"lane": "bomb-birth-shared-hook-candidate",
          "root_commit": "9cfb154aed1afc990a10bb015b291a87cd231c1e", "native_commit": None},
    677: {"lane": "bomb-birth-engine-hook-native",
          "root_commit": "1fa6c05dfd6b31ffc109fe5cc89dcebe1ccf445e",
          "native_commit": "5d03a79053baa888f8edac380b58ecf65669d3e7"},
    684: {"lane": "bomb-birth-manager-arm-native",
          "root_commit": "12578a875ef34aedb27079518ed7c4e39ac7dbe9",
          "native_commit": "deb8bb8bdaccb8a468e57bed4eb707e5fa823a5c"},
    691: {"lane": "bomb-engine-birth-real-native",
          "root_commit": "d348acddf575259282006aded9e74be403bbbc79",
          "native_commit": "552657a30d2e77a795c3ccc0514b53bc03a3cb0a"},
    700: {"lane": "bomb-joint-matrix-capture-native",
          "root_commit": "8ba9ad685ee1abbf9af02ccc498e447e018e8a2b",
          "native_commit": "0a7017c14d71acfaf4bf0cb2f20667ab58bbf36b"},
    703: {"lane": "provider-bomb-mgr-birth-landing",
          "root_commit": "fe03f39ced667ef1184838aee2018dcbc1c67138", "native_commit": None},
}
PROVIDER = {"issue": 616, "lane": "provider-bomb-mgr-birth",
            "native_commit": "6d4cbc4afc112c02b7166ef30d8a1f684c7f3ba5"}
DOWNSTREAM = {
    "573": {"lane": "enemy-bombotakara93-payload", "state": "stranded/blocked"},
    "616": {"lane": "provider-bomb-mgr-birth", "state": "provider"},
    "703": {"lane": "provider-bomb-mgr-birth-landing", "state": "landing packet"},
}
CONSUMER = "enemy-bombotakara93-payload (#573)"

CANONICAL_ROOT = "C:/Users/alari/pikmin-randomizer"
_CAND = CANONICAL_ROOT + "/output/workflow/autofill"
_PROV = _CAND + "/planning-shards/provider-actor-birth-projectiles/prepared/bomb-mgr-birth-native"

# Hard-required inputs: must exist and hash-match the pin, else DriftError.
INPUTS = {
    "maintained_cmake": {
        "path": "native/CMakeLists.txt",
        "sha256": "077809d202211aeb97eb136f6d4269b2098607b9a7a4d81d2b067c86e04a86d0"},
    "maintained_research": {
        "path": "native/pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp",
        "sha256": "a01db128fe4cddaa6ac5baac19db6f90a201aee616bf184ce77e6930dde60d77"},
    "candidate_engine_hook": {
        "path": _CAND + "/prerequisites/bomb-birth-engine-hook-native-native/"
                "pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp",
        "sha256": "301503f26fa7b149fb99043ce304418ba7178ea098f5b9e3eb269e89dc46b234",
        "commit": "5d03a79053baa888f8edac380b58ecf65669d3e7"},
    "candidate_provider_h": {
        "path": _PROV + "/pc_port/pc_p2_bomb_mgr_birth.h",
        "sha256": "94b09e5510413bc9ee8daee502598f746bc45328c539c27e6ff840e08340a1f0"},
    "candidate_provider_cpp": {
        "path": _PROV + "/pc_port/pc_p2_bomb_mgr_birth.cpp",
        "sha256": "ec36bf049c785e1028b7a0f0248754bd1b8867f76d9f035e14469fc7de68c081"},
    "candidate_payload_h": {
        "path": _PROV + "/pc_port/pc_p2_bomb_payload_actor.h",
        "sha256": "9c831a3715b23ea84b7cfefac4a5d6b0662e192d17387b46af2c1bd079368a46"},
    "candidate_payload_cpp": {
        "path": _PROV + "/pc_port/pc_p2_bomb_payload_actor.cpp",
        "sha256": "6b1a0bd29181287f3292b95c914a68548bf68e3d370574294ca904b72c28cca2"},
    "candidate_joint_h": {
        "path": _CAND + "/prerequisites/bomb-joint-matrix-capture-native-native/"
                "pc_port/pc_p2_otakara_joint_capture.h",
        "sha256": "0865c525d35ddbdca33fbd3de1e779a520e63a052db6558e69e1bb174c5a0b13",
        "commit": "0a7017c14d71acfaf4bf0cb2f20667ab58bbf36b"},
    "candidate_joint_cpp": {
        "path": _CAND + "/prerequisites/bomb-joint-matrix-capture-native-native/"
                "pc_port/pc_p2_otakara_joint_capture.cpp",
        "sha256": "9d919d7272a7c41efbe65df23b54cd909a584a12b92d9f8a797454a50dfee86c",
        "commit": "0a7017c14d71acfaf4bf0cb2f20667ab58bbf36b"},
}

# The dynamic-bridge maintained inputs are expected absent; absence is a
# CHANGES_REQUIRED finding, not a hard input error.
ABSENT_OKINPUTS = {
    "maintained_payload_h": "native/pc_port/pc_p2_bomb_payload_actor.h",
    "maintained_payload_cpp": "native/pc_port/pc_p2_bomb_payload_actor.cpp",
    "maintained_joint_h": "native/pc_port/pc_p2_otakara_joint_capture.h",
    "maintained_joint_cpp": "native/pc_port/pc_p2_otakara_joint_capture.cpp",
}

REVIEW_ITEMS = (
    {
        "id": "engine-bomb-birth-path",
        "gate": "engine Bomb birth path",
        "maintained_input": "maintained_research",
        "maintained_required_tokens": ("EnemyTypeID::EnemyID_Bomb",
                                       "EnemyTypeID::EnemyID_BombOtakara"),
        "integration_tokens": ("pc_p2_bomb_birth_hook_notify",),
        "candidate_inputs": ("candidate_engine_hook",),
        "candidate_commit": "5d03a79053baa888f8edac380b58ecf65669d3e7",
        "candidate_required_tokens": ("pc_p2_bomb_birth_hook_notify",
                                      "EnemyTypeID::EnemyID_Bomb",
                                      "EnemyTypeID::EnemyID_BombOtakara"),
        "missing_change": (
            "Land the additive birth hook from candidate #677 commit 5d03a790 into "
            "the maintained research tree: emit pc_p2_bomb_birth_hook_notify(enemyID) "
            "on the EnemyTypeID::EnemyID_Bomb (line 549) and EnemyTypeID::EnemyID_BombOtakara "
            "(line 649) manager arms, and define the notifier in a port provider TU. The "
            "maintained tree keeps the retail arms but has no hook and no landed notifier "
            "definition (only the candidate fixture defines it)."),
        "downstream": ("573", "616"),
    },
    {
        "id": "provider-cmake-membership",
        "gate": "provider CMake membership",
        "maintained_input": "maintained_cmake",
        "maintained_required_tokens": ("enable_testing",),
        "integration_tokens": ("pc_p2_bomb_mgr_birth",),
        "candidate_inputs": ("candidate_provider_h", "candidate_provider_cpp"),
        "candidate_commit": "6d4cbc4afc112c02b7166ef30d8a1f684c7f3ba5",
        "candidate_required_tokens": ("P2_BOMB_MGR_SOURCE_ID",),
        "missing_change": (
            "Add pc_port/pc_p2_bomb_mgr_birth.cpp to the maintained pikmin_pc target "
            "sources and register the provider test (add_executable + add_test) mirroring "
            "pc_generator_cache_validation_test at native/CMakeLists.txt:557/561. The "
            "maintained CMakeLists.txt has no pc_p2_bomb_mgr_birth membership."),
        "downstream": ("616", "703"),
    },
    {
        "id": "dynamic-bridge-source-93",
        "gate": "dynamic-bridge source 93",
        "maintained_input": None,
        "maintained_absent_inputs": ("maintained_payload_h", "maintained_payload_cpp",
                                     "maintained_joint_h", "maintained_joint_cpp"),
        "maintained_required_tokens": (),
        "integration_tokens": ("P2BombPayloadConfig", "pc_p2_otakara_joint_capture"),
        "candidate_inputs": ("candidate_payload_h", "candidate_payload_cpp",
                             "candidate_joint_h", "candidate_joint_cpp"),
        "candidate_commit": "0a7017c14d71acfaf4bf0cb2f20667ab58bbf36b",
        "candidate_required_tokens": ("P2BombPayloadConfig",
                                      "pc_p2_otakara_joint_capture_poll"),
        "missing_change": (
            "Land the #577 payload API (pc_port/pc_p2_bomb_payload_actor.{h,cpp}) and the "
            "#700 otakara joint capture (pc_port/pc_p2_otakara_joint_capture.{h,cpp}, commit "
            "0a7017c1), then bind source 93 (BombOtakara) through pc_p2_bomb_birth_hook_notify. "
            "None of these files exist on the maintained native line."),
        "downstream": ("573",),
    },
)

GATES = ("identity_spawn", "movement_animation", "attacks_receivers",
         "death_corpse", "transport_reward", "cleanup_reentry")


class DriftError(ValueError):
    """Fail-closed refusal: missing or mismatched review input."""


def sha256_bytes(data):
    return hashlib.sha256(bytes(data)).hexdigest()


def default_read(key):
    """Read a logical input path from disk; return None when absent."""
    if key in INPUTS:
        raw = INPUTS[key]["path"]
    elif key in ABSENT_OKINPUTS:
        raw = ABSENT_OKINPUTS[key]
    else:
        raise DriftError("Unknown input key: " + key)
    path = Path(raw)
    if not path.is_absolute():
        path = Path(CANONICAL_ROOT) / raw
    if not path.is_file():
        return None
    return path.read_bytes()


def _require_input(read, key):
    """Fail closed unless a hard-required input exists and matches its pin."""
    pin = INPUTS[key]
    data = read(key)
    if data is None:
        raise DriftError("Missing required input: %s (%s)" % (key, pin["path"]))
    actual = sha256_bytes(data)
    if actual != pin["sha256"]:
        raise DriftError("Input hash mismatch for %s: %s" % (key, actual))
    return data


def verify_candidate_artifacts(read):
    """Hash-verify every candidate artifact named by the review items."""
    evidence = {}
    for item in REVIEW_ITEMS:
        for key in item["candidate_inputs"]:
            data = _require_input(read, key)
            evidence[key] = {"path": INPUTS[key]["path"], "sha256": sha256_bytes(data),
                             "commit": INPUTS[key].get("commit", item["candidate_commit"]),
                             "match": True}
    return evidence


def _text(data):
    return None if data is None else bytes(data).decode("utf-8", errors="replace")


def _contains_all(text, tokens):
    return bool(text) and all(token in text for token in tokens)


def item_verdict(item, read):
    """Derive one item's verdict from a fresh code review of the inputs."""
    problems = []
    # Candidate artifacts must exist, hash-match, and together carry the
    # contract tokens (each token anywhere in the item's artifact set).
    candidate_text = []
    for key in item["candidate_inputs"]:
        candidate_text.append(_text(_require_input(read, key)) or "")
    joined = "\n".join(candidate_text)
    for token in item.get("candidate_required_tokens", ()):
        if token not in joined:
            problems.append("candidate artifacts missing token %r" % token)
    # Maintained side: the integration must already be present for APPROVED.
    if item.get("maintained_input"):
        key = item["maintained_input"]
        data = _require_input(read, key)
        text = _text(data)
        for token in item.get("maintained_required_tokens", ()):
            if token not in text:
                problems.append("maintained %s missing token %r" % (key, token))
    integrated = bool(item.get("integration_tokens"))
    integration_evidence = []
    sources = []
    if item.get("maintained_input"):
        sources.append(item["maintained_input"])
    for key in item.get("maintained_absent_inputs", ()):
        text = _text(read(key))
        if text is not None:
            sources.append(key)
    maintained_text = "\n".join(_text(read(key)) or "" for key in sources)
    if not _contains_all(maintained_text, item.get("integration_tokens", ())):
        integrated = False
    for token in item.get("integration_tokens", ()):
        integration_evidence.append({"token": token,
                                     "present_on_maintained": token in maintained_text})
    status = "APPROVED" if (integrated and not problems) else "CHANGES_REQUIRED"
    return {
        "id": item["id"],
        "gate": item["gate"],
        "status": status,
        "candidate_commit": item["candidate_commit"],
        "candidate_artifacts": {
            key: {"path": INPUTS[key]["path"], "sha256": INPUTS[key]["sha256"]}
            for key in item["candidate_inputs"]},
        "integration_evidence": integration_evidence,
        "problems": problems,
        "missing_change": None if status == "APPROVED" else item["missing_change"],
        "downstream": list(item["downstream"]),
    }


def validate_packet(packet, read):
    """Reject a packet whose recorded verdicts do not match a fresh review."""
    if not isinstance(packet, dict) or packet.get("schema") != SCHEMA:
        raise DriftError("Packet schema must be %s" % SCHEMA)
    recorded = {item.get("id"): item for item in packet.get("gated_items", [])}
    fresh = {item["id"]: item_verdict(item, read) for item in REVIEW_ITEMS}
    if set(recorded) != set(fresh):
        raise DriftError("Packet item set does not match the review items")
    for item_id, verdict in fresh.items():
        record = recorded[item_id]
        if record.get("status") != verdict["status"]:
            raise DriftError("Tampered/undated verdict for %s: packet=%r fresh=%r"
                             % (item_id, record.get("status"), verdict["status"]))
        recorded_evidence = {e.get("token"): bool(e.get("present_on_maintained"))
                             for e in record.get("integration_evidence", [])}
        fresh_evidence = {e["token"]: bool(e["present_on_maintained"])
                          for e in verdict["integration_evidence"]}
        if recorded_evidence != fresh_evidence:
            raise DriftError("Tampered integration evidence for " + item_id)
        if verdict["status"] == "APPROVED":
            for evidence in verdict["integration_evidence"]:
                if not evidence["present_on_maintained"]:
                    raise DriftError("Unsubstantiated APPROVED for " + item_id)
    return True


def review(read=default_read):
    """Produce the #186 review packet from a fresh, hash-verified review."""
    candidate_evidence = verify_candidate_artifacts(read)
    items = [item_verdict(item, read) for item in REVIEW_ITEMS]
    any_changes = any(item["status"] == "CHANGES_REQUIRED" for item in items)
    return {
        "schema": SCHEMA,
        "issue": 186,
        "kind": "tooling",
        "candidates": {str(k): dict(v) for k, v in CANDIDATES.items()},
        "provider": dict(PROVIDER),
        "consumer": CONSUMER,
        "downstream": {k: dict(v) for k, v in DOWNSTREAM.items()},
        "candidate_artifacts": candidate_evidence,
        "gated_items": items,
        "decision": "CHANGES_REQUIRED" if any_changes else "APPROVED",
        "gates": {name: {"status": "UNTESTED", "method": "unobserved",
                             "detail": "Tooling review packet; no runtime, no observed ticks."}
                  for name in GATES},
        "integrator_steps": [
            "Refuse to land while any gated item is CHANGES_REQUIRED; the exact "
            "missing change is recorded per item.",
            "On APPROVED: land the candidate commits listed per item onto the "
            "maintained root/native line in order (#666/#677/#684/#691/#700), then "
            "#703 landing validation, then provider CMake membership.",
            "Re-run this packet against the maintained line; only a fresh APPROVED "
            "decision unblocks the #561/#573 consumers.",
        ],
        "limitations": [
            "This packet approves or refuses the #186 shared-hook decision only; it "
            "does not land, build, run or accept gameplay.",
            "Verdicts are code-derived from hash-pinned inputs; an absent maintained "
            "integration is CHANGES_REQUIRED, never an invented approval.",
        ],
        "generated": False,
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    packet = review()
    text = json.dumps(packet, indent=1, sort_keys=True)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print("decision=%s items=%d" % (packet["decision"], len(packet["gated_items"])))
    for item in packet["gated_items"]:
        print("  %-26s %s" % (item["id"], item["status"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
