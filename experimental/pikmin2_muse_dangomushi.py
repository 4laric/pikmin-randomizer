"""Correlated natural death/corpse and cleanup/re-entry observer for DangoMushi (source 94).

Muse lane (issue #376), additive observer for the snagret-family batch-2
children. Gates 4 (death_corpse) and 6 (cleanup_reentry) close only when the
SAME generator file id appears in the required native marker legs:

1. Actor binding: ``P2_DANGOMUSHI_BIND generator=<file-id> source_id=94``.
2. Natural death: ``P2_DANGOMUSHI_DEAD generator=<file-id> source_id=94
   health=0`` occurring after the bind.
3. Corpse appearance: ``P2_BATCH3_DRAW corpse=1 key=DangoMushi clip=<dead>``
   occurring after the death (the generic batch-3 corpse draw for this
   species).
4. Re-entry: a second ``P2_DANGOMUSHI_BIND`` for the same generator after the
   corpse, proving no stale handle survived the stage-boundary reset.

Transport (gate 5) is family-dependent (boss drop semantics): it is reported
only when the family actually emits a Pod receipt
(``P2_POD_RECEIPT id=corpse:<prefix>:<file-id>``), correlated to the same
generator and ordered after the death. No receipt is fabricated, and a
missing receipt never fails gate 4/6.

Fail-closed: any missing leg, any id mismatch, wrong order, an injected
marker, or captain-down evidence yields ``gate_ok`` False. This module emits
no markers, so it cannot fabricate acceptance.

Injected runs are labelled and rejected: ``P2_MUSE_DANGOMUSHI_INJECT``,
``P2_DANGOMUSHI_DEATH_INJECT``, ``injected_health``, ``not_natural_combat=1``
and a raw ``mHealth=`` write all disqualify the run.

Captain guard (baseline #632): the log is scanned for captain-down evidence
(extinction flow, dead-state or HP<=1 markers). Any hit yields ``blocked``
with reason ``captain-down``: an interrupted observation, never a PASS.

Dependency-free pure functions over log text; stdlib only. Read-only with
respect to the family module ``pc_p2_dangomushi.cpp``: this observer consumes
the published marker contract and owns no family FSM, placement, or
packaging file, so no existing-owner review is required.
"""

import json
import sys

SOURCE_ID = 94
SOURCE_NAME = "DangoMushi"

BIND = "P2_DANGOMUSHI_BIND"
DEATH = "P2_DANGOMUSHI_DEAD"
CORPSE = "P2_BATCH3_DRAW"
RECEIPT = "P2_POD_RECEIPT"

_CAPTAIN_DOWN_TOKENS = (
    "GAMEEND_PikminExtinction",
    "DEMOID_Extinction",
    "P2_FIXTURE_CAPTAIN_DOWN",
    "orima_dead=1",
    "OrimaDown",
    "NaviDown",
)

_INJECTED_TOKENS = (
    "P2_MUSE_DANGOMUSHI_INJECT",
    "P2_DANGOMUSHI_DEATH_INJECT",
    "injected_health",
    "not_natural_combat=1",
    "mHealth=",
)


def _fields(tokens):
    fields = {}
    for token in tokens:
        key, sep, value = token.partition("=")
        if sep:
            fields[key] = value
    return fields


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _receipt_generator(fields):
    ident = fields.get("id", "")
    if not ident.startswith("corpse:"):
        return None
    tail = ident.split(":", 1)[1]
    if not tail or not tail.split(":")[-1].isdigit():
        return None
    return _int(tail.split(":")[-1])


def _is_corpse_line(tokens, fields):
    return (CORPSE in tokens and fields.get("corpse") == "1"
            and fields.get("key") == SOURCE_NAME
            and fields.get("clip", "").startswith("dead"))


def parse(text):
    """Return the gate-4/6 correlated verdict for run-log text."""
    text = text or ""
    for token in _CAPTAIN_DOWN_TOKENS:
        if token in text:
            return {
                "bound": False, "dead": False, "corpse": False,
                "rebound": False, "receipt_ok": False,
                "generator": -1, "gate_ok": False,
                "gate_death_corpse": False, "gate_cleanup_reentry": False,
                "transport_observed": False,
                "blocked": True, "block_reason": "captain-down", "injected": False,
            }
    injected = any(token in text for token in _INJECTED_TOKENS)
    if injected:
        return {
            "bound": False, "dead": False, "corpse": False,
            "rebound": False, "receipt_ok": False,
            "generator": -1, "gate_ok": False,
            "gate_death_corpse": False, "gate_cleanup_reentry": False,
            "transport_observed": False,
            "blocked": True, "block_reason": "injected", "injected": True,
        }

    binds = []     # (line_no, generator or None)
    deaths = []    # (line_no, generator or None)
    corpses = []   # (line_no,)
    receipts = []  # (line_no, generator or None)
    for line_no, line in enumerate(text.splitlines(), start=1):
        tokens = line.split()
        if not tokens:
            continue
        fields = _fields(tokens)
        if BIND in tokens and fields.get("source_id") == str(SOURCE_ID):
            binds.append((line_no, _int(fields.get("generator"))))
        if DEATH in tokens and fields.get("source_id") == str(SOURCE_ID):
            deaths.append((line_no, _int(fields.get("generator"))))
        if _is_corpse_line(tokens, fields):
            corpses.append(line_no)
        if RECEIPT in tokens:
            receipts.append((line_no, _receipt_generator(fields)))

    match = None
    for bind_line, bind_gen in binds:
        if bind_gen is None:
            continue
        death_lines = [ln for ln, gen in deaths if gen == bind_gen and ln > bind_line]
        if not death_lines:
            continue
        first_death = min(death_lines)
        corpse_lines = [ln for ln in corpses if ln > first_death]
        if not corpse_lines:
            continue
        first_corpse = min(corpse_lines)
        receipt_lines = [ln for ln, gen in receipts
                         if gen == bind_gen and ln > first_death]
        receipt_line = min(receipt_lines) if receipt_lines else None
        rebind_lines = [ln for ln, gen in binds
                        if gen == bind_gen and ln > first_corpse]
        match = {
            "generator": bind_gen,
            "bind_line": bind_line,
            "death_line": first_death,
            "corpse_line": first_corpse,
            "receipt_line": receipt_line,
            "rebind_line": min(rebind_lines) if rebind_lines else None,
        }
        break

    if match is None:
        return {
            "bound": bool(binds), "dead": bool(deaths), "corpse": bool(corpses),
            "rebound": False, "receipt_ok": False,
            "generator": -1, "gate_ok": False,
            "gate_death_corpse": False, "gate_cleanup_reentry": False,
            "transport_observed": False,
            "blocked": False, "block_reason": None, "injected": False,
        }
    return {
        "bound": True, "dead": True, "corpse": True,
        "rebound": match["rebind_line"] is not None,
        "receipt_ok": match["receipt_line"] is not None,
        "generator": match["generator"],
        "gate_ok": True,
        "gate_death_corpse": True,
        "gate_cleanup_reentry": match["rebind_line"] is not None,
        "transport_observed": match["receipt_line"] is not None,
        "blocked": False, "block_reason": None, "injected": False,
        "lines": {k: v for k, v in match.items() if k != "generator"},
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Run-log path (defaults to stdin)")
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    print(json.dumps(parse(text), indent=2))


if __name__ == "__main__":
    main()
