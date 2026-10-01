"""Reusable evidence checker for the UmiMushi71 receiver review (#662).

Lane enemies-6-umimushi71-receiver-review. Implementation owner: Codex
through shared account 4laric; executing contributor Muse Spark 1.3.

Read-only log audit over native run logs. It reports which UmiMushi71 and
UmiMushiBlind101 (sources 71/101) receiver legs are observable and whether
the corpse/receipt registration exists, and names the exact additive
registration when it is missing. It changes nothing, binds nothing, and
emits no markers.

Marker contract (read-only; owned by the family/native lanes):

- Latch legs: ``P2_UMIMUSHI_BITE``-class tongue contact, ``P2_UMIMUSHI_EAT
  generator=<gen> pikmin=1`` (exactly one InteractKill per captured Pikmin
  at the swallowed event), flick/Navi attack legs.
- Death: ``P2_UMIMUSHI_DEAD generator=<gen> source_id=<71|101> health=0``.
- Missing registration: no ``P2_UMIMUSHI_CORPSE*`` marker and no
  ``receipt=corpse:umimushi:<gen>`` token anywhere in the log. Completed
  families emit e.g. ``P2_SARAI_CORPSE_READY ...
  receipt=corpse:sarai:<gen>`` or ``P2_KURAGE_CORPSE_READY ...
  receipt=corpse:kurage:<gen>``; UmiMushi has no equivalent, so a natural
  UmiMushi death can never reach the Pod receipt ledger today.

Source anchors (retail, read-only): ``umiMushiState.cpp:510``
``StateAttack::exec`` (tongue latch), ``umiMushiState.cpp:606``
``StateEat::exec`` (swallow at animation end), ``umiMushi.cpp:467``
``Obj::damageCallBack`` (receiver entry), ``umiMushi.cpp:843``
``Obj::isChangeNavi`` (captain-change routing; checks
``EnemyID_UmiMushiBlind``).
"""

import argparse
import json
import sys

SOURCES = (71, 101)

DEAD_MARK = "P2_UMIMUSHI_DEAD"
EAT_MARK = "P2_UMIMUSHI_EAT"
CORPSE_PREFIX = "P2_UMIMUSHI_CORPSE"
RECEIPT_PREFIX = "receipt=corpse:umimushi:"


def _tainted(line):
    """True for injected-state markers this checker must never credit."""
    upper = line.upper()
    return "INJECT" in upper or "FORCE" in upper or "SETHP" in upper


def review_log(text):
    """Audit one native log; return legs observed plus the exact gap."""
    bindings = {}
    deaths = {}
    eats = 0
    corpse_markers = []
    receipt_tokens = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or _tainted(line):
            continue
        fields = dict(tok.split("=", 1) for tok in line.split() if "=" in tok)
        if DEAD_MARK in line:
            try:
                source = int(fields.get("source_id", "-1"))
            except ValueError:
                continue
            if source in SOURCES:
                deaths.setdefault(source, []).append(line)
        if line.startswith(EAT_MARK):
            eats += 1
        if CORPSE_PREFIX in line:
            corpse_markers.append(line)
        if RECEIPT_PREFIX in line:
            receipt_tokens.append(line)
        if "generator" in fields and "source_id" in fields:
            try:
                source = int(fields["source_id"])
            except ValueError:
                continue
            if source in SOURCES:
                bindings.setdefault(source, set()).add(fields["generator"])

    registration_present = bool(corpse_markers) and bool(receipt_tokens)
    return {
        "sources": sorted(bindings),
        "bindings": {s: sorted(g) for s, g in bindings.items()},
        "deaths": {s: len(v) for s, v in deaths.items()},
        "eats": eats,
        "corpse_markers": len(corpse_markers),
        "receipt_tokens": len(receipt_tokens),
        "registration_present": registration_present,
        "gap": None if registration_present else (
            "Additive receiver registration missing: in the death path that "
            "emits P2_UMIMUSHI_DEAD (beside the UMI_DEAD transition in "
            "pc_p2_umimushi.cpp), emit once per natural death "
            "P2_UMIMUSHI_CORPSE_READY generator=<gen> source_id=<71|101> "
            "receipt=corpse:umimushi:<gen>; track corpse registrations "
            "(actor -> generator) with cleanup in pc_p2_umimushi_forget and "
            "the module reset, mirroring the sarai corpses set, so a "
            "forgotten/recreated actor cannot double-report. Family-owner "
            "review REQUIRED before any shared edit."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Run-log path (defaults to stdin)")
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    print(json.dumps(review_log(text), indent=2))


if __name__ == "__main__":
    main()
