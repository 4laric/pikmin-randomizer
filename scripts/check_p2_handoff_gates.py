"""Check a family-lane six-gate handoff for the citation gap (#438, lane 02).

Lane 02 runs this on its own handoff before writing ``DONE``; lane 01 runs it
across every merged handoff. For each gate row it reports whether the row would
be ``accepted`` (a cited natural PASS), ``refused`` (``uncited`` / ``injected`` /
``shared table`` / ``bad status``) or ``ignored``, and prints the exact edit that
would make a refused PASS count. It exits non-zero when any PASS row is refused,
so a lane learns to fix citations before handoff instead of after ingestion.

    py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE<NN>_DEEPSEEK_HANDOFF.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_enemy_roster import (  # noqa: E402
    by_id,
    identity_role,
    load_and_validate,
)
from scripts.ingest_p2_handoff_gates import (  # noqa: E402
    GATE_BY_NUMBER,
    _STATUS_RE,
    _bound_tables,
    _gate_verdict,
    _status_token,
    _strip_md,
    parse_identities,
)

# A cited PASS must carry one of these in the Evidence cell (token boundary), or
# a path rooted at one of these directories. Mirrors the ingest script.
CITATION_HINT = (
    "cite an evidence file in the Evidence cell, e.g. "
    "`output/<lane-out>/<run>/native.log:NNN` or `docs/PIKMIN2_*.md`"
)
RECEIPT_HINT = (
    "cite a lane-06 receipt key (`onion:`/`corpse:`/`receipt:`) or an evidence "
    "file in the Evidence cell"
)


def _fix_for(reason: str, number: int) -> str:
    if reason == "injected":
        return ("report the gate as non-natural: an injected/proxy/fixture PASS "
                "never advances; mark `Injected vs natural = injected` and set the "
                "Result to `UNTESTED` (or supply a natural citation)")
    if number == 5:
        return RECEIPT_HINT
    return CITATION_HINT


def _row_verdict(number: int, row: dict) -> dict:
    result = _strip_md(row.get("result", ""))
    if result and _STATUS_RE.match(result.upper()) is None:
        return {"verdict": "refused:bad status", "status": "UNTESTED",
                "fix": "Result must begin with one of "
                       "PASS/PARTIAL/FAIL/BLOCKED/UNTESTED/N/A"}
    verdict = _gate_verdict(number, row)
    status = _status_token(result)
    if verdict["advance"]:
        return {"verdict": "accepted", "status": "PASS", "fix": None}
    if status == "PASS":
        reason = verdict["reason"] or "uncited"
        return {"verdict": f"refused:{reason}", "status": "PASS",
                "fix": _fix_for(reason, number)}
    return {"verdict": "ignored", "status": status, "fix": None}


def check_handoff(markdown: str, roster=None) -> dict:
    """Return ``{"rows": [...], "had_refusal": bool}`` for one handoff.

    Each row is one identity: an ``ignored`` role/unknown row, a
    ``refused:shared table`` row (no table bound), or a ``checked`` row carrying
    a per-gate ``gates`` list with ``verdict``/``status``/``fix`` per gate 1-6.
    """
    roster = roster if roster is not None else load_and_validate()
    base = by_id(roster)
    bound = _bound_tables(markdown, roster)
    rows: list[dict] = []
    had_refusal = False
    for source_id, name in parse_identities(markdown, roster):
        entry = base.get(source_id)
        if entry is None:
            rows.append({"source_id": source_id, "enum_name": name, "role": "unknown",
                         "verdict": "ignored:unknown",
                         "fix": "name a real roster source_id "
                                "(see docs/PIKMIN2_ENEMY_ROSTER.json)"})
            continue
        role = identity_role(entry)
        if role not in ("source", "variant"):
            rows.append({"source_id": source_id, "enum_name": entry.enum_name, "role": role,
                         "verdict": f"ignored:role", "fix": None})
            continue
        table = bound.get(source_id)
        if table is None:
            rows.append({"source_id": source_id, "enum_name": entry.enum_name, "role": role,
                         "verdict": "refused:shared table",
                         "fix": "give this identity its own `Source ID` line + "
                                "six-gate table (its PASS rows are attributed to "
                                "another identity)"})
            had_refusal = True
            continue
        gates = []
        for number in range(1, 7):
            gate = GATE_BY_NUMBER[number]
            table_row = table.get(number, {})
            verdict = _row_verdict(number, table_row)
            if verdict["verdict"].startswith("refused"):
                had_refusal = True
            gates.append({"number": number, "gate": gate,
                          "result_cell": table_row.get("result", ""),
                          "evidence_cell": table_row.get("evidence", ""),
                          **verdict})
        rows.append({"source_id": source_id, "enum_name": entry.enum_name, "role": role,
                     "verdict": "checked", "gates": gates})
    return {"rows": rows, "had_refusal": had_refusal}


def _print(check: dict, label: str) -> None:
    for row in check["rows"]:
        head = f"{row['source_id']} {row['enum_name']} (role={row['role']})"
        if row["verdict"].startswith("ignored"):
            print(f"{head}: ignored ({row['verdict'].split(':')[1]})")
            continue
        if row["verdict"] == "refused:shared table":
            print(f"{head}: refused (shared table) — {row['fix']}")
            continue
        print(f"{head}:")
        for gate in row["gates"]:
            note = f" [{gate['status']}]"
            if gate["verdict"] == "accepted":
                print(f"  {gate['number']}. {gate['gate']:<18} accepted{note}")
            elif gate["verdict"].startswith("refused"):
                print(f"  {gate['number']}. {gate['gate']:<18} {gate['verdict']}{note}")
                print(f"      fix: {gate['fix']}")
            else:
                print(f"  {gate['number']}. {gate['gate']:<18} ignored{note}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path, help="family-lane handoff markdown")
    args = parser.parse_args(argv)

    if not args.handoff.is_file():
        print(f"handoff not found: {args.handoff}", file=sys.stderr)
        return 2

    roster = load_and_validate()
    markdown = args.handoff.read_text(encoding="utf-8")
    check = check_handoff(markdown, roster)
    _print(check, args.handoff.name)
    if check["had_refusal"]:
        print(f"\n{args.handoff.name}: some PASS rows are refused (see fix lines above)",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
