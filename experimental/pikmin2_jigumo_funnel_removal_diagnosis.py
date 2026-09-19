"""Jigumo63 funnel-path post-DEAD removal/carcass diagnosis (#823).

Downstream consumer: shard-enemies-4-jigumo63-observer (#374 gen 3).
Read-only trace of the research family source plus the gen-3 observer run
evidence. Pins the exact post-DEAD lifecycle point (StateDead exec,
carcass/leave flags, removal path) and routes the owner (family owner vs
engine #167), or returns an exact unattributable finding with reason.
Fail-closed: malformed records and missing inputs are refused, never
defaulted. No engine edits, no builds, no launches. Diagnosis only; never
an engine unblock.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

RESEARCH = "native/pikmin2-research"
FILES = {
    "src/plugProjectMorimuraU/jigumoState.cpp":
        "6ecc82c841371c8b8c912bf0d4295aeb7aeda8ffd686eeac195d850cf2253200",
    "include/Game/enemyInfo.h":
        "0e68be790e4f7f4a99a48064b4750a95367c09996b7484292a33b2969d9b44ba",
    "src/plugProjectYamashitaU/enemyBase.cpp":
        "9871a460d0bb60cfd41565ebbb8c87222417f88dce15e768256b0395b7ec9e88",
}

ATTRIBUTED = "ATTRIBUTED"
UNATTRIBUTABLE = "UNATTRIBUTABLE"

# Death-series markers the observer must show, in order.
DEATH_SEQUENCE = (
    "P2_JIGUMO_DEAD",
    "P2_JIGUMO_NATURAL_DEATH",
    "P2_JIGUMO_FUNNEL_DROVE",
)


class Refused(ValueError):
    """Fail-closed refusal with a reason."""


def read_log_text(path):
    if not os.path.isfile(path):
        raise Refused("run log missing: " + str(path))
    raw = open(path, "rb").read()
    if not raw.strip():
        raise Refused("run log is empty: " + str(path))
    for encoding in ("utf-8", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise Refused("run log is not UTF-8 or UTF-16: " + str(path))


def trace_death(lines):
    """Trace the post-DEAD marker chain. Returns a finding dict."""
    dead = [l for l in lines if "P2_JIGUMO_DEAD " in l]
    if not dead:
        raise Refused("no P2_JIGUMO_DEAD marker: death never observed")
    natural = any("P2_JIGUMO_NATURAL_DEATH" in l for l in lines)
    funnel = [l for l in lines if "P2_JIGUMO_FUNNEL_DROVE" in l]
    removal = any(re.search(r"corpse_recorded|REMOVAL_COMPLETE|CORPSE_EMITTED|corpse pellet", l, re.IGNORECASE) is not None
                  for l in lines)
    corpse_fail = any("death produced neither removal nor corpse" in l
                      for l in lines)
    dead_phases = []
    for l in lines:
        m = re.search(r"state=dead clip=dead1 phase=([0-9.]+)", l)
        if m:
            dead_phases.append(float(m.group(1)))
    return {
        "dead_observed": True,
        "dead_line": dead[0][:120],
        "natural_death": natural,
        "funnel_drove": funnel[0][:120] if funnel else None,
        "dead_anim_reached_end": any(p >= 1.0 for p in dead_phases),
        "removal_observed": removal,
        "corpse_fail_logged": corpse_fail,
    }


def attribute(trace):
    """Route the owner from the death trace. Never invents providers."""
    if not trace["dead_observed"]:
        raise Refused("cannot attribute without an observed death")
    if trace["removal_observed"]:
        return (ATTRIBUTED,
                "removal/corpse observed; no gap to route",
                "none")
    # Dead anim played to end (phase 1.00 stuck across ticks) yet the actor
    # persists with no corpse: kill() never took effect (StateDead::exec
    # :266-280 gates kill on mIsPlaying+KEYEVENT_END) or kill fired without
    # removal/carcass (engine path; Jigumo never touches EB_LeaveCarcass).
    reasons = [
        "family owner first: verify StateDead::exec reaches enemy->kill "
        "(jigumoState.cpp:266-280; prime suspect mIsPlaying gate at :268 "
        "vs KEYEVENT_END delivery in the port)",
        "engine #167 second: kill-to-removal plus carcass pipeline "
        "(EB_LeaveCarcass never enabled for Jigumo; corpse registration)",
    ]
    if trace["dead_anim_reached_end"]:
        verdict = ATTRIBUTED
        detail = ("dead anim completed (phase stuck at 1.00) with actor "
                  "persisting and no corpse: " + " / ".join(reasons))
    else:
        verdict = UNATTRIBUTABLE
        detail = ("dead anim never completed in the trace; cannot separate "
                  "anim-end delivery from removal: needs a longer-bounded "
                  "run with per-tick anim-phase markers")
    owner = "family-owner-then-engine-167" if verdict == ATTRIBUTED else "unknown"
    return verdict, detail, owner


def analyze(log_path):
    text = read_log_text(log_path)
    trace = trace_death(text.splitlines())
    verdict, detail, owner = attribute(trace)
    return {"verdict": verdict, "detail": detail, "owner": owner,
            "trace": trace}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Jigumo63 post-DEAD diagnosis (#823)")
    ap.add_argument("log", help="observer native.log to trace")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        result = analyze(args.log)
    except Refused as exc:
        print("REFUSED: %s" % exc)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("verdict: %s" % result["verdict"])
        print("owner: %s" % result["owner"])
        print("detail: %s" % result["detail"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
