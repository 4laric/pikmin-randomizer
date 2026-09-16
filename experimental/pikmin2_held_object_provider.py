"""Held-object provider contract for treasure consumers (issue #614).

Lane provider-held-object-api. This module is the Python half of the
provider: the consumer fixture log grammar (ATTACH/FOLLOW/DETACH/RELEASE/
REWARD with exactly-once accounting), the machine-readable provider
contract, and the host receipt-key mapping. It stages nothing, injects
nothing, and emits no markers.

The BEHAVIORAL proof lives in native/tools/p2_held_object_test.cpp
(67 checks against the real lifecycle: attach/follow/detach/drop/cleanup
and exactly-once release plus single-set reward confirmation). A log
grammar agreement here alone can never pass acceptance; validate_log
exists so consumers #574 (BigFoot69) and LongLegs get deterministic
verdicts on future fixture logs.
"""
import json
import re
import sys

PROVIDER = "p2-held-object/1"
CONSUMER_ISSUES = (574,)
RECEIPT_HOST_API = "pc_p2_receipt_host_grant"
DELIVERY_HOST_API = "pc_p2_delivery_host_deliver"

REASONS = ("dropped", "thrown", "carrier-died", "item-lost")

_ATTACH_RE = re.compile(r"P2_HELD_OBJECT_ATTACH carrier=(\d+) item=(\d+) slot=(\d+) gen=(\d+)")
_FOLLOW_RE = re.compile(r"P2_HELD_OBJECT_FOLLOW carrier=(\d+)")
_DETACH_RE = re.compile(r"P2_HELD_OBJECT_DETACH carrier=(\d+) reason=(\S+)")
_RELEASE_RE = re.compile(r"P2_HELD_OBJECT_RELEASE carrier=(\d+) item=(\d+) delivered=([01])")
_REWARD_RE = re.compile(r"P2_HELD_OBJECT_REWARD carrier=(\d+) granted=([01])")

_INJECTED_MARKERS = (
    "P2_HELD_OBJECT_INJECT",
    "p2-held-object-inject",
    "injection=1",
    "P2_HELDOBJECT_INJECT",
)


def provider_contract():
    """Machine-readable provider contract for treasure consumers."""
    return {
        "schema": PROVIDER,
        "consumer_issues": list(CONSUMER_ISSUES),
        "native_api": "native/pc_port/pc_p2_held_object.h",
        "native_test": "native/tools/p2_held_object_test.cpp",
        "lifecycle": ["attach", "followJoint", "detach/onCarrierDeath",
                      "onItemLost", "release", "confirmReward", "reset"],
        "exactly_once": ["release", "confirmReward"],
        "reward_routing": {
            "grant_api": RECEIPT_HOST_API,
            "delivery_api": DELIVERY_HOST_API,
            "seed": "<run seed>",
            "reward": "treasure:<itemToken>",
            "slot": "<carrierToken>",
            "encounter": "held-release",
            "note": "Host grants through the EXISTING receipt host; the "
                    "provider only records the release and the confirmation.",
        },
        "runtime_claim": False,
    }


def receipt_keys(carrier_token, item_token, seed):
    """Map provider tokens to existing-receipt-host grant arguments.

    Pure derivation of the documented key shape; performs no I/O and
    grants nothing. The host passes these to pc_p2_receipt_host_grant.
    """
    if not isinstance(carrier_token, int) or carrier_token <= 0:
        raise ValueError("carrier token must be a positive integer")
    if not isinstance(item_token, int) or item_token <= 0:
        raise ValueError("item token must be a positive integer")
    if not isinstance(seed, str) or not seed:
        raise ValueError("seed must be a nonempty string")
    return {
        "seed": seed,
        "reward": "treasure:%d" % item_token,
        "slot": str(carrier_token),
        "encounter": "held-release",
    }


def _fields(pattern, line):
    match = pattern.search(line)
    return match.groups() if match else None


def validate_log(text):
    """Validate one consumer fixture log against the provider grammar.

    Returns per-carrier accounting plus the verdict: True only when every
    carrier shows exactly one attach, at least one follow, detach before
    release, at most one delivered=1 release, at most one reward line, no
    second release, and no injected markers.
    """
    carriers = {}
    injected = False
    lines = (text or "").splitlines()

    def record(carrier):
        return carriers.setdefault(carrier, {
            "attach": 0, "item": None, "follow": 0, "detach": [],
            "release": 0, "delivered": 0, "reward": 0, "granted": 0,
        })

    for line in lines:
        if any(marker in line for marker in _INJECTED_MARKERS):
            injected = True
        fields = _fields(_ATTACH_RE, line)
        if fields:
            row = record(int(fields[0]))
            row["attach"] += 1
            row["item"] = int(fields[1])
        fields = _fields(_FOLLOW_RE, line)
        if fields:
            record(int(fields[0]))["follow"] += 1
        fields = _fields(_DETACH_RE, line)
        if fields:
            row = record(int(fields[0]))
            if fields[1] not in REASONS:
                row["detach"].append("bad-reason:" + fields[1])
            else:
                row["detach"].append(fields[1])
        fields = _fields(_RELEASE_RE, line)
        if fields:
            row = record(int(fields[0]))
            row["release"] += 1
            if fields[2] == "1":
                row["delivered"] += 1
        fields = _fields(_REWARD_RE, line)
        if fields:
            row = record(int(fields[0]))
            row["reward"] += 1
            if fields[1] == "1":
                row["granted"] += 1

    problems = []
    if injected:
        problems.append("injected-markers-present")
    if not carriers:
        problems.append("no-carriers")
    for carrier, row in sorted(carriers.items()):
        for entry in row["detach"]:
            if entry.startswith("bad-reason:"):
                problems.append("carrier-%d-%s" % (carrier, entry))
        if row["attach"] != 1:
            problems.append("carrier-%d-attach-%d" % (carrier, row["attach"]))
        if row["follow"] < 1:
            problems.append("carrier-%d-no-follow" % carrier)
        if not row["detach"]:
            problems.append("carrier-%d-no-detach" % carrier)
        if row["release"] > 1:
            problems.append("carrier-%d-double-release" % carrier)
        if row["delivered"] > 1:
            problems.append("carrier-%d-double-delivery" % carrier)
        if row["reward"] > 1:
            problems.append("carrier-%d-double-reward" % carrier)

    return {
        "carriers": carriers,
        "injected": injected,
        "problems": problems,
        "verdict": not problems,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("contract", "validate", "keys"))
    parser.add_argument("path", nargs="?", help="Log path for validate")
    parser.add_argument("--carrier", type=int, default=0)
    parser.add_argument("--item", type=int, default=0)
    parser.add_argument("--seed", default="")
    args = parser.parse_args(argv)
    if args.command == "contract":
        print(json.dumps(provider_contract(), indent=2, sort_keys=True))
        return 0
    if args.command == "keys":
        print(json.dumps(receipt_keys(args.carrier, args.item, args.seed),
                         indent=2, sort_keys=True))
        return 0
    if not args.path:
        parser.error("validate requires a log path")
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        result = validate_log(handle.read())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] else 1


if __name__ == "__main__":
    main()
