"""Ingest family-lane six-gate handoff tables into lane-02 candidate rows (#438).

Family lanes publish a six-gate evidence table in their handoff
(``docs/PIKMIN2_LANE<NN>_DEEPSEEK_HANDOFF.md``). This script parses that table,
normalizes each gate to the lane-02 status vocabulary, and runs the result
through ``admission_requirements`` so lane 02 can answer, per identity, which
gates a handoff *would advance* and which remain *blocking*.

It is the ingest counterpart to ``scripts/audit_pikmin2_roster.py`` and shares
its deny-by-default posture:

* Nothing is written to the evidence ledger unless ``--apply`` is given, and even
  then only the advanced gate ``PASS`` values are merged into existing rows — the
  ``delivery_receipt`` and ``eligibility`` are never touched, so a handoff cannot
  admit an identity on its own (transport/reward stays lane 06 review).
* A ``PASS`` only advances a gate when it is *not* labelled injected/proxy (the
  row's result/label is checked against ``NONNATURAL_MARKERS``) and is *backed by
  a citation* (the evidence carries a ``docs/PIKMIN2_*.md``/``.log``/``.txt``/
  ``.json`` filename or a file path, reusing ``RECEIPT_CITATION_MARKERS``; a
  slash/backslash only counts between non-space segments). The
  ``transport_reward`` gate is gated by ``RECEIPT_KEY_PREFIXES`` /
  ``RECEIPT_CITATION_MARKERS`` exactly as ``admission_requirements`` does.

Table format (the parser is the contract; see docs/PIKMIN2_ENEMY_ROSTER.md):

    | Gate | Result | Evidence [| Injected vs natural] |
    |---|---|---:|
    | 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_*.md ... |

* Rows are matched by their leading gate number (1..6 -> ``GATE_IDS``) so the
  spelled-out name may vary. ``Result`` may be bolded and carry a parenthetical.
* An identity is named as ``<source_id> EnumName``, ``EnumName (<source_id>)`` or
  the literal ``source_id``/``EnemyID`` token; each is cross-referenced against the
  roster, and only ``source``/``variant`` identities get candidate rows.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_enemy_roster import (  # noqa: E402
    EVIDENCE_PATH,
    GATE_IDS,
    NONNATURAL_MARKERS,
    RECEIPT_CITATION_MARKERS,
    RECEIPT_KEY_PREFIXES,
    admission_requirements,
    by_id,
    identity_role,
    load_and_validate,
)

# Gate number (1..6 in the handoff table) -> lane-02 gate id.
GATE_BY_NUMBER = {index + 1: gate for index, gate in enumerate(GATE_IDS)}

# Statuses we normalize table results into. PARTIAL is a family-lane rendering of
# a not-yet-natural gate and is treated as non-PASS (blocking).
_STATUS_ORDER = ("PASS", "PARTIAL", "FAIL", "BLOCKED", "UNTESTED", "N/A")

_SOURCE_ID_RE = re.compile(r"(?:source_id|EnemyID)\s*[`\"']?\s*(\d+)")
_ID_ENUM_RE = re.compile(r"\b(\d{1,3})\s*`([A-Za-z][A-Za-z0-9_]*)`")
_NAME_PAREN_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*\(\s*(\d+)")


def _strip_md(text: str) -> str:
    return re.sub(r"`|\*|_", "", text or "").strip()


def _split_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    stripped = stripped.strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _iter_tables(markdown: str):
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        block = []
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            cells = _split_row(lines[i])
            if cells:
                block.append(cells)
            i += 1
        if block:
            yield block


def parse_gate_table(markdown: str) -> dict[int, dict]:
    """Return ``{gate_number: {'result','evidence','label'}}`` from the first
    handoff table whose header names a ``Result`` column."""
    for block in _iter_tables(markdown):
        if len(block) < 2:
            continue
        header = [_strip_md(cell).lower() for cell in block[0]]
        if not any("result" in cell for cell in header):
            continue
        result_col = next((idx for idx, cell in enumerate(header) if "result" in cell), 1)
        evidence_col = next((idx for idx, cell in enumerate(header) if "evidence" in cell),
                            result_col + 1)
        label_col = next((idx for idx, cell in enumerate(header)
                          if "injected" in cell or "natural" in cell), None)
        table: dict[int, dict] = {}
        for row in block[1:]:
            first = _strip_md(row[0])
            match = re.match(r"^(\d+)", first)
            if not match:
                continue
            number = int(match.group(1))
            if not (1 <= number <= 6):
                continue
            table[number] = {
                "result": row[result_col] if len(row) > result_col else "",
                "evidence": row[evidence_col] if len(row) > evidence_col else "",
                "label": row[label_col] if label_col is not None and len(row) > label_col else "",
            }
        if table:
            return table
    return {}


def parse_identities(markdown: str, roster=None) -> list[tuple[int, str | None]]:
    """Return ``[(source_id, enum_name)]`` named in the handoff, roster-verified."""
    roster = roster or []
    by_source = {entry.source_id: entry for entry in roster}
    by_name = {entry.enum_name: entry for entry in roster}
    found: dict[int, str | None] = {}
    for match in _SOURCE_ID_RE.finditer(markdown):
        found.setdefault(int(match.group(1)), None)
    if roster:
        for match in _ID_ENUM_RE.finditer(markdown):
            sid, name = int(match.group(1)), match.group(2)
            if name in by_name:
                found.setdefault(sid, name)
        for match in _NAME_PAREN_RE.finditer(markdown):
            name, sid = match.group(1), int(match.group(2))
            if name in by_name:
                found.setdefault(sid, name)
    result = []
    for sid in sorted(found):
        name = by_source[sid].enum_name if sid in by_source else found[sid]
        result.append((sid, name))
    return result


def _status_token(result_cell: str) -> str:
    text = _strip_md(result_cell).upper()
    for token in _STATUS_ORDER:
        if token in text:
            return token
    return "UNTESTED"


# Citation markers split between an unambiguous file extension and a path
# separator used between segments, so a bare "/" list-separator (e.g. a
# "frame=12 / frame=20" event clock) does not read as a citation.
_EXTENSION_CITATIONS = tuple(m for m in RECEIPT_CITATION_MARKERS if m.startswith("."))


def _has_citation(text: str) -> bool:
    clean = text.strip()
    if not clean:
        return False
    if any(ext in clean for ext in _EXTENSION_CITATIONS):
        return True
    return bool(re.search(r"\S[/\\]\S", clean))


def _receipt_shaped(text: str) -> bool:
    value = text.strip()
    if not value:
        return False
    if value.startswith(RECEIPT_KEY_PREFIXES):
        return True
    return any(marker in value for marker in RECEIPT_CITATION_MARKERS)


def _gate_verdict(number: int, row: dict) -> dict:
    """Decide whether a gate row advances; refuse injected/uncited PASSes."""
    result = _strip_md(row.get("result", ""))
    status = _status_token(result)
    if status != "PASS":
        return {"status": status, "advance": False, "reason": None, "receipt": None}
    label = _strip_md(row.get("label", ""))
    if NONNATURAL_MARKERS.search(f"{result} {label}"):
        return {"status": "PASS", "advance": False, "reason": "injected", "receipt": None}
    evidence = _strip_md(row.get("evidence", ""))
    if number == 5:
        if _receipt_shaped(evidence):
            return {"status": "PASS", "advance": True, "reason": None, "receipt": evidence}
        return {"status": "PASS", "advance": False, "reason": "uncited", "receipt": None}
    if not _has_citation(evidence):
        return {"status": "PASS", "advance": False, "reason": "uncited", "receipt": None}
    return {"status": "PASS", "advance": True, "reason": None, "receipt": None}


def ingest(markdown: str, roster=None) -> list[dict]:
    """Parse a handoff and return per-identity candidate rows with
    ``advances``, ``refused`` and ``blocking`` (the ``admission_requirements``
    output) without writing anything."""
    roster = roster if roster is not None else load_and_validate()
    base = by_id(roster)
    table = parse_gate_table(markdown)
    rows: list[dict] = []
    for source_id, name in parse_identities(markdown, roster):
        entry = base.get(source_id)
        if entry is None:
            rows.append({"source_id": source_id, "enum_name": name, "role": "unknown",
                         "advances": [], "refused": {}, "blocking": ["unknown source id"]})
            continue
        role = identity_role(entry)
        if role not in ("source", "variant"):
            rows.append({"source_id": source_id, "enum_name": entry.enum_name, "role": role,
                         "skipped": True, "advances": [], "refused": {}, "blocking": []})
            continue
        gates: dict[str, str] = {}
        advances: list[str] = []
        refused: dict[str, str] = {}
        receipt: str | None = None
        for number, gate in GATE_BY_NUMBER.items():
            if number not in table:
                gates[gate] = "UNTESTED"
                continue
            verdict = _gate_verdict(number, table[number])
            if verdict["advance"]:
                gates[gate] = "PASS"
                advances.append(gate)
                if gate == "transport_reward":
                    receipt = verdict["receipt"]
            else:
                gates[gate] = verdict["status"] if verdict["status"] != "PASS" else "UNTESTED"
                if verdict["reason"]:
                    refused[gate] = verdict["reason"]
        candidate = replace(entry, gates=gates, notes=(), delivery_receipt=receipt)
        rows.append({"source_id": source_id, "enum_name": entry.enum_name, "role": role,
                     "advances": advances, "refused": refused,
                     "blocking": admission_requirements(candidate)})
    return rows


def apply_ingested_gates(rows: list[dict], ledger_path) -> list[tuple[str, list[str]]]:
    """Merge validated advanced gates into an evidence overlay (merge-only).

    Sets ``gates[<gate>]="PASS"`` for each advanced gate on rows that already
    exist; never fabricates a row, never writes ``transport_reward`` (a receipt is
    a manual lane-06 step) and never touches ``eligibility`` or ``delivery_receipt``.
    """
    path = Path(ledger_path)
    if not path.is_file():
        raise FileNotFoundError(f"ledger not found: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.setdefault("entries", {})
    changed: list[tuple[str, list[str]]] = []
    for row in rows:
        if row.get("skipped") or row["source_id"] is None:
            continue
        advanced = [gate for gate in row["advances"] if gate != "transport_reward"]
        if not advanced:
            continue
        key = str(row["source_id"])
        if key not in entries:
            continue
        gates = entries[key].setdefault("gates", {})
        for gate in advanced:
            gates[gate] = "PASS"
        changed.append((key, advanced))
    if changed:
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return changed


def _fmt_row(row: dict) -> list[str]:
    lines = []
    if row.get("skipped"):
        lines.append(f"{row['source_id']} {row['enum_name']} (role={row['role']}): "
                     f"skipped (non-seedable role)")
        return lines
    lines.append(f"{row['source_id']} {row['enum_name']} (role={row['role']}):")
    lines.append(f"  advances: {', '.join(row['advances']) or '(none)'}")
    if row["refused"]:
        details = ", ".join(f"{gate}:{reason}" for gate, reason in sorted(row["refused"].items()))
        lines.append(f"  refused PASS: {details}")
    lines.append(f"  blocking (admission_requirements): {', '.join(row['blocking']) or '(none)'}")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", nargs="+", type=Path, help="markdown handoff(s) to ingest")
    parser.add_argument("--apply", action="store_true",
                        help="merge advanced gate PASSes into the evidence ledger")
    parser.add_argument("--ledger", type=Path, default=None,
                        help="evidence ledger path (default: the committed overlay)")
    args = parser.parse_args(argv)

    roster = load_and_validate()
    ledger = args.ledger or EVIDENCE_PATH
    for path in args.handoff:
        markdown = path.read_text(encoding="utf-8")
        print(f"# {path.name}")
        rows = ingest(markdown, roster)
        for row in rows:
            for line in _fmt_row(row):
                print(line)
        if args.apply:
            for key, advanced in apply_ingested_gates(rows, ledger):
                print(f"  applied {key}: {', '.join(advanced)} -> PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
