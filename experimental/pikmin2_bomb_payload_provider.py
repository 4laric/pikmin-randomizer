"""Bomb payload provider contract for consumer #573 (issue #577).

Lane enemy-bomb-payload-provider. This module is the Python half of the
provider: pinned shared-blast defaults, the consumer fixture log grammar
(BIRTH/ATTACH/DETACH/DETONATE/BLAST with exactly-once accounting), and the
machine-readable provider contract. It stages nothing, injects nothing,
and emits no markers.

The BEHAVIORAL proof lives in native/tools/p2_bomb_payload_actor_test.cpp
(65 checks against the real lifecycle plus the real shared blast router).
A log grammar agreement here alone can never pass acceptance; validate_log
exists so consumer #573 gets deterministic verdicts on future fixture logs.
"""
import json
import re
import sys

PROVIDER = "p2-bomb-payload-actor/1"
CONSUMER_ISSUE = 573

# Pinned shared-blast defaults (lane-20 retail values, Bomb.h fp02 default).
BLAST_DEFAULTS = {
    "radius": 90.0,
    "half_height": 50.0,
    "teki_damage": 500.0,
    "navi_piki_damage": 10.0,
}

TRIGGERS = ("contact", "press", "death", "earthquake")

_BIRTH_RE = re.compile(r"P2_BOMB_PAYLOAD_BIRTH carrier=(\d+) slot=(\d+) gen=(\d+)")
_ATTACH_RE = re.compile(r"P2_BOMB_PAYLOAD_ATTACH carrier=(\d+) joint=otakara")
_DETACH_RE = re.compile(r"P2_BOMB_PAYLOAD_DETACH carrier=(\d+) reason=(\S+)")
_DETONATE_RE = re.compile(
    r"P2_BOMB_PAYLOAD_DETONATE carrier=(\d+) trigger=(\S+) detonated=([01])")
_BLAST_RE = re.compile(
    r"P2_BOMB_PAYLOAD_BLAST carrier=(\d+) receivers=(\d+) hits=(\d+)")

_INJECTED_MARKERS = (
    "P2_BOMBOTAKARA_INJECT",
    "p2-bombotakara-inject",
    "injection=1",
    "P2_BOMB_PAYLOAD_INJECT",
)


def provider_contract():
    """Machine-readable provider contract for consumer #573."""
    return {
        "schema": PROVIDER,
        "consumer_issue": CONSUMER_ISSUE,
        "native_api": "native/pc_port/pc_p2_bomb_payload_actor.h",
        "native_test": "native/tools/p2_bomb_payload_actor_test.cpp",
        "blast_defaults": dict(BLAST_DEFAULTS),
        "triggers": list(TRIGGERS),
        "lifecycle": ["birth", "followJoint", "detonate/onCarrierDeath",
                      "onPayloadLost", "reset"],
        "exactly_once": True,
        "routing": "host calls p2_bombsarai_route_blast with the recorded event",
        "runtime_claim": False,
    }


def _fields(pattern, line):
    match = pattern.search(line)
    return match.groups() if match else None


def validate_log(text):
    """Validate one consumer fixture log against the provider grammar.

    Returns per-carrier accounting plus the verdict: True only when every
    carrier shows birth, joint attach, at most one detonated=1 blast line,
    no second detonation, no injected markers, and blast damage fields
    matching the pinned defaults where present.
    """
    carriers = {}
    injected = False
    lines = (text or "").splitlines()

    def record(carrier):
        return carriers.setdefault(carrier, {
            "birth": 0, "attach": 0, "detach": [],
            "detonated": 0, "suppressed": 0, "blasts": [],
        })

    for line in lines:
        if any(marker in line for marker in _INJECTED_MARKERS):
            injected = True
        fields = _fields(_BIRTH_RE, line)
        if fields:
            record(int(fields[0]))["birth"] += 1
        fields = _fields(_ATTACH_RE, line)
        if fields:
            record(int(fields[0]))["attach"] += 1
        fields = _fields(_DETACH_RE, line)
        if fields:
            record(int(fields[0]))["detach"].append(fields[1])
        fields = _fields(_DETONATE_RE, line)
        if fields:
            row = record(int(fields[0]))
            if fields[1] not in TRIGGERS:
                row["detonated"] += 99
            elif fields[2] == "1":
                row["detonated"] += 1
            else:
                row["suppressed"] += 1
        fields = _fields(_BLAST_RE, line)
        if fields:
            record(int(fields[0]))["blasts"].append({
                "receivers": int(fields[1]), "hits": int(fields[2]),
            })

    problems = []
    if injected:
        problems.append("injected-markers-present")
    if not carriers:
        problems.append("no-carriers")
    for carrier, row in sorted(carriers.items()):
        if row["birth"] != 1:
            problems.append("carrier-%d-birth-%d" % (carrier, row["birth"]))
        if row["attach"] < 1:
            problems.append("carrier-%d-no-attach" % carrier)
        if row["detonated"] > 1:
            problems.append("carrier-%d-double-detonation" % carrier)
        if row["detonated"] == 1 and len(row["blasts"]) != 1:
            problems.append("carrier-%d-blast-count" % carrier)
    return {
        "carriers": carriers,
        "injected": injected,
        "problems": problems,
        "verdict": not problems,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("contract", "validate"))
    parser.add_argument("path", nargs="?", help="Log path for validate")
    args = parser.parse_args(argv)
    if args.command == "contract":
        print(json.dumps(provider_contract(), indent=2, sort_keys=True))
        return 0
    if not args.path:
        parser.error("validate requires a log path")
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        result = validate_log(handle.read())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] else 1


if __name__ == "__main__":
    main()
