"""Payload acceptance observer for BombOtakara93 provider seam (#573).

Pure log classifier (launches/stages/touches nothing). It independently
re-derives the provider-driven natural chain from a fixture native.log:

  PROVIDER_REQUEST -> PROVIDER_ABSENT (blocked today) or, once a Bomb-manager
  provider exists, BORN(provider=1) -> CAPTURED(joint=otakara, attached=1) ->
  BLAST(shared_primitive=1, receivers/hits/pikmin_hits >= 1) ->
  BOMB_HIT(interaction=InteractBomb, accepted=1, natural=1), with exactly-once
  detonation and interruption-clean (Gone tokens stay Gone) enforcement.

Honesty rules (independent of, but consistent with, the l61 observer):
- A BLAST/BOMB_HIT counts as natural ONLY for a generator with a
  provider-linked born+captured chain. Stub-flow markers
  (P2_BOMBOTAKARA_CARRY/ARM/DETONATE, unlinked BLAST) prove the sidecar ran,
  never natural combat.
- Any l61 injection marker fails the natural checks for that log.
- Stale-token events (after CARRIER_GONE) and second accepted detonations
  are reported as violations, not passes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Adopted prerequisite (#577, integrated via the #614 wave pin root 268494fb):
# the accepted provider owns the consumer log grammar
# BIRTH/ATTACH/DETACH/DETONATE/BLAST. Delegate to it instead of keeping a
# second divergent grammar here.
try:
    from experimental import pikmin2_bomb_payload_provider as accepted_provider
except ImportError:  # pragma: no cover - provider absent in a bare checkout
    accepted_provider = None

ACCEPTED_PROVIDER_SCHEMA = "p2-bomb-payload-actor/1"


def accepted_provider_verdict(text: str) -> dict:
    """Run the accepted provider's consumer-grammar validator."""
    if accepted_provider is None:
        return {"available": False, "verdict": False, "problems": ["provider-absent"]}
    result = accepted_provider.validate_log(text)
    return {
        "available": True,
        "schema": ACCEPTED_PROVIDER_SCHEMA,
        "verdict": bool(result["verdict"]),
        "problems": list(result["problems"]),
        "carriers": len(result["carriers"]),
    }

INJECTED_MARKERS = (
    "P2_BOMBOTAKARA_INJECT",
    "p2-bombotakara-inject",
    "injection=1",
    "P2_BOMBOTAKARA_FIXTURE_GUARD_PIKMIN",
    "P2_BOMBOTAKARA_DEATH_INJECT",
    "P2_OTAKARA_DEATH_INJECT",
)

# Stub-flow markers: sidecar ran, never natural evidence.
STUB_MARKERS = (
    "P2_BOMBOTAKARA_CARRY ",
    "P2_BOMBOTAKARA_ARM ",
    "P2_BOMBOTAKARA_DETONATE ",
    "P2_BOMBOTAKARA_DETONATE_SUPPRESSED ",
)

REQUEST_RE = re.compile(
    r"P2_BOMBOTAKARA_PROVIDER_REQUEST contract=(\S+) generator=(\d+) missing=(\S+)")
ABSENT_RE = re.compile(r"P2_BOMBOTAKARA_PROVIDER_ABSENT generator=(\d+) state=(\S+)")
BORN_RE = re.compile(
    r"P2_BOMBOTAKARA_PAYLOAD_BORN generator=(\d+) payload=(\d+) accepted=(\d) stale=(\d) state=(\S+) provider=1")
CAPTURED_RE = re.compile(
    r"P2_BOMBOTAKARA_PAYLOAD_CAPTURED generator=(\d+) payload=(\d+) joint=(\S+) attached=(\d) state=(\S+) provider=1")
DETONATED_RE = re.compile(
    r"P2_BOMBOTAKARA_PAYLOAD_DETONATED generator=(\d+) payload=(\d+) accepted=(\d) stale=(\d) already_done=(\d) detonations=(\d+) provider=1")
RELEASED_RE = re.compile(
    r"P2_BOMBOTAKARA_PAYLOAD_RELEASED generator=(\d+) payload=(\d+) accepted=(\d) stale=(\d) already_done=(\d) state=(\S+) provider=1")
GONE_RE = re.compile(
    r"P2_BOMBOTAKARA_PAYLOAD_CARRIER_GONE generator=(\d+) accepted=(\d) stale=(\d) state=(\S+)")
BLAST_RE = re.compile(
    r"P2_BOMBOTAKARA_BLAST generator=(\d+) payload=(\d+) .*receivers=(\d+) hits=(\d+) pikmin_hits=(\d+).*shared_primitive=1")
HIT_RE = re.compile(
    r"P2_BOMBOTAKARA_BOMB_HIT generator=(\d+) payload=(\d+) .*accepted=(\d+) .*interaction=InteractBomb natural=1")
ATTACH_L61_RE = re.compile(
    r"P2_BOMBOTAKARA_ATTACH generator=(\d+) payload=(\d+) joint=otakara natural=1")


def validate(path: str | Path) -> dict:
    """Classify a native.log; returns a JSON-serializable verdict dict."""
    verdict: dict = {
        "provider_request": False,
        "request_generator": 0,
        "missing_reason": "",
        "provider_absent": False,
        "born": {},
        "captured_attached": {},
        "blast_natural": {},
        "hit_natural": {},
        "attach_observed_carrier_side": {},
        "exactly_once_violations": [],
        "stale_violations": [],
        "stub_present": False,
        "injected": [],
        "gate1_attach_provider_linked": False,
        "gate3_blast_provider_linked": False,
        "accepted_provider": {},
    }
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        verdict["error"] = "unreadable log: %s" % exc
        return verdict
    gone: set = set()
    detonated_accepted: dict = {}
    for i, line in enumerate(lines, start=1):
        for marker in INJECTED_MARKERS:
            if marker in line:
                verdict["injected"].append("%d:%s" % (i, marker))
        for marker in STUB_MARKERS:
            if marker in line:
                verdict["stub_present"] = True
        m = REQUEST_RE.search(line)
        if m:
            verdict["provider_request"] = True
            verdict["request_generator"] = int(m.group(2))
            verdict["missing_reason"] = m.group(3)
        if ABSENT_RE.search(line):
            verdict["provider_absent"] = True
        m = BORN_RE.search(line)
        if m and m.group(3) == "1":
            verdict["born"][m.group(1)] = m.group(2)
        m = CAPTURED_RE.search(line)
        if m and m.group(4) == "1" and m.group(1) in verdict["born"]:
            verdict["captured_attached"][m.group(1)] = m.group(2)
        m = ATTACH_L61_RE.search(line)
        if m:
            verdict["attach_observed_carrier_side"][m.group(1)] = m.group(2)
        m = DETONATED_RE.search(line)
        if m:
            gen = m.group(1)
            if m.group(4) == "1":
                verdict["stale_violations"].append("%d:detonated-stale gen=%s" % (i, gen))
            elif m.group(3) == "1":
                detonated_accepted[gen] = detonated_accepted.get(gen, 0) + 1
                if detonated_accepted[gen] > 1:
                    verdict["exactly_once_violations"].append(
                        "%d:second-accepted-detonation gen=%s" % (i, gen))
        m = RELEASED_RE.search(line)
        if m and m.group(4) == "1":
            verdict["stale_violations"].append("%d:released-stale gen=%s" % (i, m.group(1)))
        m = GONE_RE.search(line)
        if m and m.group(2) == "1":
            gone.add(m.group(1))
        m = BLAST_RE.search(line)
        if m and int(m.group(3)) >= 1 and int(m.group(4)) >= 1 and int(m.group(5)) >= 1:
            if m.group(1) in verdict["captured_attached"]:
                verdict["blast_natural"][m.group(1)] = i
        m = HIT_RE.search(line)
        if m and m.group(3) == "1" and m.group(1) in verdict["captured_attached"]:
            verdict["hit_natural"][m.group(1)] = i
    # Post-pass: events after Gone are stale violations.
    if gone:
        for i, line in enumerate(lines, start=1):
            for gen in gone:
                if ("generator=%s " % gen) in line and ("PAYLOAD_DETONATED" in line
                        or "PAYLOAD_RELEASED" in line or "PAYLOAD_BORN" in line):
                    tag = "%d:post-gone-event gen=%s" % (i, gen)
                    if tag not in verdict["stale_violations"]:
                        verdict["stale_violations"].append(tag)
    verdict["accepted_provider"] = accepted_provider_verdict("\n".join(lines))
    verdict["gate1_attach_provider_linked"] = bool(
        verdict["captured_attached"]) and not verdict["injected"]
    verdict["gate3_blast_provider_linked"] = bool(
        verdict["blast_natural"] and verdict["hit_natural"]
        and not verdict["exactly_once_violations"]
        and not verdict["stale_violations"] and not verdict["injected"])
    return verdict


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="BombOtakara573 payload log review")
    parser.add_argument("--log", required=True)
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)
    verdict = validate(args.log)
    print("provider_request=%s absent=%s stub=%s injected=%d" % (
        verdict["provider_request"], verdict["provider_absent"],
        verdict["stub_present"], len(verdict["injected"])))
    print("gate1_provider_linked=%s gate3_provider_linked=%s" % (
        verdict["gate1_attach_provider_linked"],
        verdict["gate3_blast_provider_linked"]))
    ap = verdict.get("accepted_provider", {})
    print("accepted_provider available=%s schema=%s verdict=%s carriers=%d problems=%s"
          % (ap.get("available"), ap.get("schema"), ap.get("verdict"),
             ap.get("carriers", 0), ",".join(ap.get("problems", [])) or "-"))
    for key in ("exactly_once_violations", "stale_violations"):
        for item in verdict[key]:
            print("VIOLATION %s" % item)
    if args.json:
        Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    blocked = (verdict["provider_request"] and verdict["provider_absent"]
               and not verdict["born"])
    if blocked:
        print("VERDICT BLOCKED no_bomb_mgr_birth (honest provider gap)")
        return 2
    if verdict["gate1_attach_provider_linked"] and verdict["gate3_blast_provider_linked"]:
        print("VERDICT PASS provider-driven natural attach+blast")
        return 0
    print("VERDICT FAIL chain incomplete")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
