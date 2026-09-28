"""Reusable evidence checker for the Catfish26 receiver review (#641).

Lane enemies-5-catfish26-receiver-review. Implementation owner: Codex
through shared GitHub account 4laric; contributor Muse Spark 1.3 via OpenCode.

Read-only log audit over native run logs. It reports which Catfish26
(source 26) receiver legs are observable and whether the corpse/receipt
registration exists, and names the exact additive registration when it is
missing. It changes nothing, binds nothing, and emits no markers.

Marker contract (read-only; owned by the family/native lanes):

- Binding: ``P2_CATFISH_BIND generator=<gen> source_id=26`` and
  ``P2_ENEMY_READY species=Catfish ... generator=<gen>``.
- Attack legs: ``P2_CATFISH_BITE``, ``P2_CATFISH_EAT ... slot=<n>``,
  ``P2_CATFISH_FLICK``, ``P2_CATFISH_ATTACK_NAVI ... damage=<x>``.
- Death: ``P2_CATFISH_DEAD generator=<gen> source_id=26 health=0``.
- Missing registration: no ``P2_CATFISH_CORPSE*`` marker and no
  ``receipt=corpse:catfish:<gen>`` token anywhere in the log. Completed
  families emit e.g. ``P2_SARAI_CORPSE_READY ... receipt=corpse:sarai:<gen>``
  or ``P2_KURAGE_CORPSE_READY ... receipt=corpse:kurage:<gen>``; Catfish
  has no equivalent, so a natural Catfish death can never reach the Pod
  receipt ledger today.

Finding (mirrors the TEKI_Mar missing-receipt pattern: receiver present in
source but unregistered in the routing table):

- In the death path that emits ``P2_CATFISH_DEAD`` (next to
  ``transition(s, CATFISH_DEAD, ...)`` in ``pc_p2_catfish.cpp``), emit once
  per natural death::

      P2_CATFISH_CORPSE_READY generator=<gen> source_id=26 receipt=corpse:catfish:<gen>

- Track corpse registrations (actor -> generator) with cleanup in
  ``pc_p2_catfish_forget`` and the module reset, mirroring the sarai
  ``corpses`` set, so a forgotten/recreated actor cannot double-report.
- Family-owner review is REQUIRED before any shared edit: the
  ``corpse:catfish:`` receipt namespace touches the shared Pod ledger
  contract owned elsewhere.

Stdlib only. Pure functions over log text.
"""

import json
import re
import sys

SOURCE_ID = 26
FAMILY = "Catfish"

RE_BIND = re.compile(r"P2_CATFISH_BIND\s+generator=(\d+)\s+source_id=26\b")
RE_READY = re.compile(r"P2_ENEMY_READY\s+species=Catfish\b.*?generator=(\d+)")
RE_BITE = re.compile(r"P2_CATFISH_BITE\b")
RE_EAT = re.compile(r"P2_CATFISH_EAT\b.*?slot=(\d+)")
RE_FLICK = re.compile(r"P2_CATFISH_FLICK\b")
RE_ATTACK_NAVI = re.compile(r"P2_CATFISH_ATTACK_NAVI\b.*?damage=([0-9.]+)")
RE_DEAD = re.compile(r"P2_CATFISH_DEAD\s+generator=(\d+)\s+source_id=26\b")
RE_CORPSE = re.compile(r"P2_CATFISH_CORPSE[A-Z_]*\b")
RE_CORPSE_RECEIPT = re.compile(r"receipt=corpse:catfish:(\d+)")

TAINT_TOKENS = ("injected", "health_zero")


def _tainted(line):
    lowered = line.lower()
    return any(token in lowered for token in TAINT_TOKENS)


def review_log(text):
    """Audit one native run log for Catfish26 receiver evidence.

    Returns a dict with per-leg presence, generator sets, the
    corpse-registration verdict, and ``findings``. Never passes a gate:
    ``gate_claim`` is always ``none: review only``.
    """
    verdict = {
        "source_id": SOURCE_ID,
        "family": FAMILY,
        "binding_generators": [],
        "attack_legs": {"bite": False, "eat": False, "flick": False,
                        "attack_navi": False},
        "death_generators": [],
        "corpse_registration": False,
        "corpse_receipt_generators": [],
        "tainted_lines": [],
        "findings": [],
        "gate_claim": "none: review only",
    }
    if not (text or "").strip():
        verdict["findings"].append("absent-markers: empty log")
        return verdict

    bindings, deaths, receipts = set(), set(), set()
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _tainted(line) and "P2_CATFISH_" in line:
            verdict["tainted_lines"].append(line_no)
        match = RE_BIND.search(line) or RE_READY.search(line)
        if match:
            bindings.add(match.group(1))
        if RE_BITE.search(line):
            verdict["attack_legs"]["bite"] = True
        if RE_EAT.search(line):
            verdict["attack_legs"]["eat"] = True
        if RE_FLICK.search(line):
            verdict["attack_legs"]["flick"] = True
        if RE_ATTACK_NAVI.search(line):
            verdict["attack_legs"]["attack_navi"] = True
        match = RE_DEAD.search(line)
        if match:
            deaths.add(match.group(1))
        if RE_CORPSE.search(line):
            verdict["corpse_registration"] = True
        for receipt in RE_CORPSE_RECEIPT.finditer(line):
            verdict["corpse_registration"] = True
            receipts.add(receipt.group(1))

    verdict["binding_generators"] = sorted(bindings, key=int)
    verdict["death_generators"] = sorted(deaths, key=int)
    verdict["corpse_receipt_generators"] = sorted(receipts, key=int)

    if not bindings:
        verdict["findings"].append(
            "absent-markers: no P2_CATFISH_BIND / P2_ENEMY_READY species=Catfish; "
            "no actor bound, receiver legs cannot be attributed")
    if bindings and not any(verdict["attack_legs"].values()):
        verdict["findings"].append(
            "absent-markers: Catfish bound but no attack leg "
            "(BITE/EAT/FLICK/ATTACK_NAVI) observed")
    if deaths and not verdict["corpse_registration"]:
        verdict["findings"].append(
            "missing-registration: natural death observed for "
            "generator(s) %s but no P2_CATFISH_CORPSE* marker and no "
            "receipt=corpse:catfish:<gen>; add one P2_CATFISH_CORPSE_READY "
            "emission per natural death beside the P2_CATFISH_DEAD site in "
            "pc_p2_catfish.cpp plus actor->generator corpse tracking cleared "
            "in pc_p2_catfish_forget/reset; family-owner review required "
            "before any shared edit (Pod ledger namespace)" % sorted(deaths, key=int))
    if verdict["tainted_lines"]:
        verdict["findings"].append(
            "injected-taint: Catfish markers on line(s) %s carry "
            "injected/health_zero tokens; labelled, never natural evidence"
            % sorted(set(verdict["tainted_lines"])))
    return verdict


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?",
                        help="Run-log path (defaults to stdin)")
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    print(json.dumps(review_log(text), indent=2))


if __name__ == "__main__":
    main()