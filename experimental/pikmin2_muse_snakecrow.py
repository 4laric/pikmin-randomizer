"""Correlated natural death/carry/receipt observer for SnakeCrow (source 34).

Muse lane (issue #376), child of the snagret family work. Gates 4
(death_corpse), 5 (transport_reward) and 6 (cleanup_reentry) close only
when the SAME generator file id appears in all three native marker legs:

1. Actor binding/death: ``P2_SNAKEJOINT_BIND generator=<file-id>
   species=SnakeCrow source_id=34`` and ``P2_SNAKEJOINT_DEAD
   generator=<file-id> source_id=34`` (pc_port/pc_p2_snakejoint.cpp,
   driven from production ``BTeki::update``; no fixture code).
2. Pod receipt: ``[Pikipelago] P2_POD_RECEIPT id=corpse:<prefix><file-id>``
   for the same file id. The generic preview corpse path emits no family
   infix, so correlation is by exact generator id plus a death-before-
   receipt order check, never by name.
3. Re-entry: a second ``P2_SNAKEJOINT_BIND`` for the same generator after
   a stage-boundary reset, proving no stale handle survived.

Fail-closed: any missing leg, any id mismatch, death-after-receipt order,
or an unmapped receipt yields False. A staged P1 ``TEKI_Chappy`` proxy
birth without the seed/family legs can never pass; synthetic markers are
not generated here, so nothing in this module can fabricate acceptance.

Captain guard (baseline #632): the log is scanned for captain-down
evidence (extinction flow, dead-state or HP<=1 markers). Any hit yields
``blocked`` with reason ``captain-down``: an interrupted observation,
never a PASS. Protected observation is labelled and can never prove
captain damage.

Dependency-free pure functions over log text; stdlib only. Read-only with
respect to the legacy lane-25 family claim: this observer consumes the
same marker contract but owns no family FSM, placement, or packaging file.
"""

import json
import sys

SOURCE_ID = 34
SOURCE_NAME = "SnakeCrow"

BIND = "P2_SNAKEJOINT_BIND"
DEATH = "P2_SNAKEJOINT_DEAD"
RECEIPT = "P2_POD_RECEIPT"

_CAPTAIN_DOWN_TOKENS = (
    "GAMEEND_PikminExtinction",
    "DEMOID_Extinction",
    "P2_FIXTURE_CAPTAIN_DOWN",
    "orima_dead=1",
    "OrimaDown",
    "NaviDown",
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
    # The whole tail past "corpse:" (optional lane prefix segments, then
    # the generator id) must end at the numeric generator; a non-numeric
    # tail never resolves instead of misreading a suffix.
    tail = ident.split(":", 1)[1]
    if not tail or not tail.split(":")[-1].isdigit():
        return None
    return _int(tail.split(":")[-1])


def parse(text):
    """Return the gate-4/5/6 correlated verdict for run-log text."""
    text = text or ""
    for token in _CAPTAIN_DOWN_TOKENS:
        if token in text:
            return {
                "bound": False,
                "dead": False,
                "receipt_ok": False,
                "rebound": False,
                "generator": -1,
                "gate_ok": False,
                "blocked": True,
                "block_reason": "captain-down",
            }

    binds = []      # (line_no, generator or None)
    deaths = []     # (line_no, generator or None)
    receipts = []   # (line_no, generator or None)
    for line_no, line in enumerate(text.splitlines(), start=1):
        tokens = line.split()
        if not tokens:
            continue
        fields = _fields(tokens)
        if BIND in tokens and fields.get("species") == "SnakeCrow":
            binds.append((line_no, _int(fields.get("generator"))))
        if DEATH in tokens and fields.get("source_id") == str(SOURCE_ID):
            deaths.append((line_no, _int(fields.get("generator"))))
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
        receipt_lines = [ln for ln, gen in receipts
                         if gen == bind_gen and ln > first_death]
        if not receipt_lines:
            continue
        rebind_lines = [ln for ln, gen in binds
                        if gen == bind_gen and ln > min(receipt_lines)]
        match = {
            "generator": bind_gen,
            "bind_line": bind_line,
            "death_line": first_death,
            "receipt_line": min(receipt_lines),
            "rebind_line": min(rebind_lines) if rebind_lines else None,
        }
        break

    if match is None:
        return {
            "bound": bool(binds),
            "dead": bool(deaths),
            "receipt_ok": False,
            "rebound": False,
            "generator": -1,
            "gate_ok": False,
            "blocked": False,
            "block_reason": None,
        }
    return {
        "bound": True,
        "dead": True,
        "receipt_ok": True,
        "rebound": match["rebind_line"] is not None,
        "generator": match["generator"],
        "gate_ok": True,
        "blocked": False,
        "block_reason": None,
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
