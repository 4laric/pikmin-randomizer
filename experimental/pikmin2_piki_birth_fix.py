"""Piki-birth challenge-setup fix contract + run-log verifier (issue #741).

Lane piki-birth-challenge-setup-fix. Cross-partition prerequisite unblocking
p1-challenge-trial-runtime-acceptance (#567): the chal4 boot panics with
`*** PIKI BIRTH FAILED !!!` before any squad birth. Diagnosis #721 (done)
attributes POOL_EMPTY by elimination and names the exact fix locations; this
module carries the machine-readable fix contract and validates headed-run
logs against the toggle-independent P2_PIKI_* diagnostics emitted by the
owned engine edits. It stages nothing, injects nothing, edits no engine
files, and emits no markers itself.
"""
import json
import re

PROVIDER = "p2-piki-birth-fix/1"
CONSUMER_ISSUE = 567
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

# Exact owned engine edits (read-only contract; #186 review before landing).
ENGINE_EDITS = (
    "native/src/plugPikiKando/gameCoreSection.cpp",
    "native/src/plugPikiColin/newPikiGame.cpp",
    "native/src/plugPikiKando/objectMgr.cpp",
    "native/src/plugPikiKando/pikiMgr.cpp",
    "native/src/plugPikiKando/goalItem.cpp",
)

_CREATE_RE = re.compile(r"P2_PIKI_CREATE requested=(\d+) challenge=([01])")
_CREATED_RE = re.compile(r"P2_PIKI_CREATE_DONE max=(\d+) size=(\d+)")
_INITSTAGE_RE = re.compile(r"P2_PIKI_INITSTAGE challenge=([01])")
_FINASETUP_RE = re.compile(r"P2_PIKI_FINASETUP pool_max=(-?\d+) pool_size=(-?\d+)")
_POOL_FULL_RE = re.compile(r"P2_PIKI_POOL_FULL num=(\d+) max=(\d+)")
_POOL_NO_SLOT_RE = re.compile(r"P2_PIKI_POOL_NO_SLOT num=(\d+) max=(\d+)")
_BIRTH_CAP_RE = re.compile(r"P2_PIKI_BIRTH_CAP total=(\d+) cap=(\d+) mode=(\S+)")
_BIRTH_POOL_NULL_RE = re.compile(
    r"P2_PIKI_BIRTH_POOL_NULL total=(\d+) pool_max=(-?\d+) pool_size=(-?\d+)")
_BIRTH_HALT_RE = re.compile(
    r"P2_PIKI_BIRTH_HALT pikiMgr=([01]) mapPikis=(-?\d+) container=(-?\d+) "
    r"pool_max=(-?\d+) pool_size=(-?\d+)")
_PANIC_RE = re.compile(r"PIKI BIRTH FAILED")
_SQUAD_RE = re.compile(r"squad_alive=(\d+)")
_CAPTAIN_DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN")
_CAPSTOP_RE = re.compile(r"P2_PIKI_BIRTH_CAPSTOP queued=(\d+)")
_DISPENSE_CAPSTOP_RE = re.compile(r"P2_PIKI_DISPENSE_CAPSTOP queued=(\d+)")
_BASEINF_RE = re.compile(r"P2_PIKI_BASEINF free=(\d+) active=(\d+) challenge=([01])")
_COUNTERS_RE = re.compile(
    r"P2_PIKI_COUNTERS formation=(\d+) free=(\d+) me=(\d+) work=(\d+) "
    r"born=(\d+) all=(\d+)")

_INJECTED_MARKERS = (
    "P2_PIKI_INJECT",
    "p2-piki-inject",
    "injection=1",
)


def provider_contract():
    """Machine-readable fix contract for the #567 consumer."""
    return {
        "schema": PROVIDER,
        "consumer_issue": CONSUMER_ISSUE,
        "depends": [721, 186, 52],
        "engine_edits": list(ENGINE_EDITS),
        "diagnostics": [
            "P2_PIKI_CREATE requested=<n> challenge=<0|1>",
            "P2_PIKI_CREATE_DONE max=<n> size=<n>",
            "P2_PIKI_INITSTAGE challenge=<0|1>",
            "P2_PIKI_FINASETUP pool_max=<n> pool_size=<n>",
            "P2_PIKI_POOL_FULL / P2_PIKI_POOL_NO_SLOT",
            "P2_PIKI_BIRTH_CAP / P2_PIKI_BIRTH_POOL_NULL",
            "P2_PIKI_BIRTH_HALT",
        ],
        "guard_sha256": GUARD_SHA256,
        "integration": "Engine edits need #186 shared-owner review before "
                       "landing; no ADMIT here.",
        "runtime_claim": False,
    }


def _find(pattern, lines):
    return [m.groups() for line in lines for m in [pattern.search(line)] if m]


def parse_run_markers(log_text):
    """Parse toggle-independent birth diagnostics from a headed run log."""
    lines = (log_text or "").splitlines()
    creates = [(int(n), int(c)) for n, c in _find(_CREATE_RE, lines)]
    return {
        "initstage": [int(c[0]) for c in _find(_INITSTAGE_RE, lines)],
        "create_requested": creates,
        "create_done": [(int(a), int(b)) for a, b in _find(_CREATED_RE, lines)],
        "finalsetup": [(int(a), int(b)) for a, b in _find(_FINASETUP_RE, lines)],
        "pool_full": _find(_POOL_FULL_RE, lines),
        "pool_no_slot": _find(_POOL_NO_SLOT_RE, lines),
        "birth_cap": _find(_BIRTH_CAP_RE, lines),
        "birth_pool_null": _find(_BIRTH_POOL_NULL_RE, lines),
        "birth_halt": _find(_BIRTH_HALT_RE, lines),
        "panic": any(_PANIC_RE.search(l) for l in lines),
        "capstop": [int(m[0]) for m in _find(_CAPSTOP_RE, lines)],
        "dispense_capstop": [int(m[0]) for m in _find(_DISPENSE_CAPSTOP_RE, lines)],
        "baseinf": [(int(a), int(b), int(c))
                    for a, b, c in _find(_BASEINF_RE, lines)],
        "counters": [tuple(int(v) for v in m)
                     for m in _find(_COUNTERS_RE, lines)],
        "squads": [int(m[0]) for m in _find(_SQUAD_RE, lines)],
        "captain_down": any(_CAPTAIN_DOWN_RE.search(l) for l in lines),
        "injected": any(m in l for l in lines for m in _INJECTED_MARKERS),
        "lines": len(lines),
    }


def verify_boot(markers):
    """Fail-closed verdict: pool created on the challenge path, ordered
    setup, live squad born, no panic/abort/captain-down, no injected lines."""
    problems = []
    if markers["injected"]:
        problems.append("injected-markers-present")
    if markers["captain_down"]:
        problems.append("captain-down-cannot-substantiate")
    if markers["panic"]:
        problems.append("piki-birth-panic-present")
    creates = [n for n, c in markers["create_requested"]]
    challenge_flags = sorted({c for _, c in markers["create_requested"]})
    if not creates:
        problems.append("no-create-at-all")
    elif creates[0] <= 0:
        problems.append("create-requested-%d" % creates[0])
    if 1 not in challenge_flags:
        # Informational, not fatal: the BBFT direct boot reaches chal4
        # (CHALLENGE_LAYOUT_READY) while playerState->isChallengeMode()
        # stays false; creation itself is path-independent and proven.
        problems.append("create-challenge-flag-%s" % (challenge_flags or "none"))
    if not markers["create_done"]:
        problems.append("no-create-done")
    else:
        max_n, size_n = markers["create_done"][0]
        if max_n <= 0:
            problems.append("pool-max-%d" % max_n)
    if not markers["initstage"]:
        problems.append("no-initstage-marker")
    if not markers["finalsetup"]:
        problems.append("no-finalsetup-marker")
    if markers["birth_halt"] or markers["birth_pool_null"]:
        problems.append("birth-null-path-hit")
    if markers["pool_full"] or markers["pool_no_slot"] or markers["birth_cap"]:
        problems.append("pool-or-cap-refusal-hit")
    best = max(markers["squads"]) if markers["squads"] else 0
    if best < 1:
        problems.append("no-live-squad")
    drained = (not markers["panic"] and not markers["captain_down"]
               and bool(markers["capstop"]) and bool(markers["dispense_capstop"]))
    return {
        "problems": problems,
        "verdict": not problems,
        "create_requested": creates[0] if creates else None,
        "create_challenge_flags": challenge_flags,
        "pool_max": markers["create_done"][0][0] if markers["create_done"] else None,
        "squad_alive_max": best,
        "drained_quietly": drained,
        "capstop_ticks": len(markers["capstop"]),
        "baseinf": markers["baseinf"][0] if markers["baseinf"] else None,
        "counters": markers["counters"][0] if markers["counters"] else None,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("contract", "verify"))
    parser.add_argument("path", nargs="?", help="Run-log path for verify")
    args = parser.parse_args(argv)
    if args.command == "contract":
        print(json.dumps(provider_contract(), indent=2, sort_keys=True))
        return 0
    if not args.path:
        parser.error("verify requires a run-log path")
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        result = verify_boot(parse_run_markers(handle.read()))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] else 1


if __name__ == "__main__":
    main()
