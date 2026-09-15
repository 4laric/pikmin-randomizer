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
* A gate table belongs to ONE identity: the source id named in the nearest
  preceding "Source ID" line (or an identity-naming heading). Other identities
  named in the same handoff but without their own table are reported as
  ``shared table, excluded`` (all gates ``UNTESTED``) and are never applied.
* A ``PASS`` only advances a gate when the row (Result + Injected/natural label
  + Evidence) does *not* match ``NONNATURAL_MARKERS`` (injected/proxy/fixture/
  forced/vehicle/visual/host/display), and the Evidence carries a citation: a
  ``.md``/``.log``/``.txt``/``.json`` token (``\\S+\\.(md|log|txt|json)\\b``) or a
  file path rooted at ``docs/``/``output/``/``tests/`` with at least two segments.
  ``transport_reward`` instead requires a lane-06 receipt (``onion:``/``corpse:``/
  ``receipt:`` key or the same citation).

Table format (the parser is the contract; see docs/PIKMIN2_ENEMY_ROSTER.md):

    | Gate | Result | Evidence [| Injected vs natural] |
    |---|---|---:|
    | 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_*.md ... |

* Rows are matched by their leading gate number (1..6 -> ``GATE_IDS``).
* A literal ``|`` inside a cell must be escaped as ``\\|``.
* ``Result`` status is matched at the start of the cell
  (``^(PASS|PARTIAL|FAIL|BLOCKED|UNTESTED|N/A)\\b``); anything else reads as
  ``UNTESTED``. Bold and a parenthetical are fine.
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

# A Result cell must open with one of these tokens; anything else is UNTESTED.
# (This deliberately rejects "FAIL (was PASS earlier)" and "BYPASSED".)
_STATUS_RE = re.compile(r"(PASS|PARTIAL|FAIL|BLOCKED|UNTESTED|N/A)\b")

_SOURCE_ID_RE = re.compile(r"(?:source_id|EnemyID)\s*[`\"']?\s*(\d+)")
_ID_ENUM_RE = re.compile(r"\b(\d{1,3})\s*`([A-Za-z][A-Za-z0-9_]*)`")
_NAME_PAREN_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*\(\s*(\d+)")
# Roster-name + bare number ("DangoMushi 94", "BigFoot 69"), number + roster-name
# ("73 BigTreasure"), and "enemy NN"/"enemy ID NN" ("enemy 30"). The name forms
# are roster-filtered like _NAME_PAREN_RE.
_NAME_NUM_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s+(\d{1,3})\b")
_NUM_NAME_RE = re.compile(r"\b(\d{1,3})\s+([A-Za-z][A-Za-z0-9_]*)\b")
_ENEMY_NUM_RE = re.compile(r"\benemy\s+(?:id\s+)?(\d{1,3})\b", re.IGNORECASE)
# "source id 44" / "P2 id 72" (space-separated, possibly bold-marked).
_SOURCE_ID_SPACE_RE = re.compile(r"\b(?:source\s+id|P2\s+id)\s*:?\s*\**\s*(\d{1,3})\b",
                                 re.IGNORECASE)

# A line that names the identity a following table belongs to: the prose
# "Source ID" / "Source enemy ID" / "Concrete source ID" line. A bare "EnemyID"
# token on another line is deliberately NOT a clue, so a payload/child mention
# ("... EnemyID 36 ..." on a wrapped line) cannot steal the owner identity.
_OWNER_LINE_RE = re.compile(r"source\s+(?:enemy\s+)?id", re.IGNORECASE)

# A citation is an extension token at a token boundary, or a path rooted at a
# known directory with one segment after the root (two segments counting the
# root). "12/16", "frame=12 / frame=20" and other bare separators do not count.
_EXT_CITATION_RE = re.compile(r"\S+\.(?:md|log|txt|json)\b")
_PLAIN_PATH_RE = re.compile(r"\b(?:docs|output|tests)/\S+")


def _strip_md(text: str) -> str:
    return re.sub(r"`|\*|_", "", text or "").strip()


def _split_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    stripped = stripped.strip("|")
    # Tokenise: a backslash escapes exactly the next character (so ``\|`` is a
    # literal pipe and ``\\|`` is a literal backslash followed by a separator).
    cells: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(stripped):
        ch = stripped[i]
        if ch == "\\" and i + 1 < len(stripped):
            current.append(stripped[i + 1])
            i += 2
            continue
        if ch == "|":
            cells.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    cells.append("".join(current).strip())
    return cells


def _iter_tables(markdown: str):
    """Yield ``(start_line_index, block)`` for each pipe table block."""
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        start = i
        block = []
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            cells = _split_row(lines[i])
            if cells:
                block.append(cells)
            i += 1
        if block:
            yield start, block


def _extract_gate_table(block: list[list[str]]) -> dict[int, dict]:
    if len(block) < 2:
        return {}
    header = [_strip_md(cell).lower() for cell in block[0]]
    if not any("result" in cell or "status" in cell for cell in header):
        return {}
    result_col = next((idx for idx, cell in enumerate(header)
                       if "result" in cell or "status" in cell), 1)
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
    return table


def parse_gate_table(markdown: str) -> dict[int, dict]:
    """Return ``{gate_number: {'result','evidence','label'}}`` from the first
    handoff table whose header names a ``Result`` column."""
    for _, block in _iter_tables(markdown):
        table = _extract_gate_table(block)
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
        for match in _NAME_NUM_RE.finditer(markdown):
            name, sid = match.group(1), int(match.group(2))
            if name in by_name:
                found.setdefault(sid, name)
        for match in _NUM_NAME_RE.finditer(markdown):
            sid, name = int(match.group(1)), match.group(2)
            if name in by_name:
                found.setdefault(sid, name)
    for match in _ENEMY_NUM_RE.finditer(markdown):
        sid = int(match.group(1))
        if not roster or sid in by_source:
            found.setdefault(sid, None)
    for match in _SOURCE_ID_SPACE_RE.finditer(markdown):
        sid = int(match.group(1))
        if not roster or sid in by_source:
            found.setdefault(sid, None)
    result = []
    for sid in sorted(found):
        name = by_source[sid].enum_name if sid in by_source else found[sid]
        result.append((sid, name))
    return result


def _status_token(result_cell: str) -> str:
    text = _strip_md(result_cell).upper()
    match = _STATUS_RE.match(text)
    return match.group(1) if match else "UNTESTED"


def _has_citation(text: str) -> bool:
    clean = text.strip()
    if not clean:
        return False
    if _EXT_CITATION_RE.search(clean):
        return True
    return bool(_PLAIN_PATH_RE.search(clean))


def _receipt_shaped(text: str) -> bool:
    value = text.strip()
    if not value:
        return False
    if value.startswith(RECEIPT_KEY_PREFIXES):
        return True
    return _has_citation(value)


def _gate_verdict(number: int, row: dict) -> dict:
    """Decide whether a gate row advances; refuse injected/uncited PASSes."""
    result = _strip_md(row.get("result", ""))
    status = _status_token(result)
    if status != "PASS":
        return {"status": status, "advance": False, "reason": None, "receipt": None}
    label = _strip_md(row.get("label", ""))
    evidence = _strip_md(row.get("evidence", ""))
    if NONNATURAL_MARKERS.search(f"{result} {label} {evidence}"):
        return {"status": "PASS", "advance": False, "reason": "injected", "receipt": None}
    if number == 5:
        if _receipt_shaped(evidence):
            return {"status": "PASS", "advance": True, "reason": None, "receipt": evidence}
        return {"status": "PASS", "advance": False, "reason": "uncited", "receipt": None}
    if not _has_citation(evidence):
        return {"status": "PASS", "advance": False, "reason": "uncited", "receipt": None}
    return {"status": "PASS", "advance": True, "reason": None, "receipt": None}


def _owner_from_line(line: str, by_name=None) -> int | None:
    match = _SOURCE_ID_RE.search(line)
    if match:
        return int(match.group(1))
    match = _ID_ENUM_RE.search(line)
    if match:
        return int(match.group(1))
    if by_name:
        match = _NAME_PAREN_RE.search(line)
        if match and match.group(1) in by_name:
            return int(match.group(2))
        match = _NAME_NUM_RE.search(line)
        if match and match.group(1) in by_name:
            return int(match.group(2))
        match = _NUM_NAME_RE.search(line)
        if match and match.group(2) in by_name:
            return int(match.group(1))
    return None


def _bound_tables(markdown: str, roster) -> dict[int, dict]:
    """Bind each gate table to the source id named nearest above it.

    Walks back from a table to the nearest "Source ID" line or heading that names
    an identity (``source_id``/``EnemyID``/``N Name``/``Name (N)``); a heading that
    names no identity is only skipped, never treated as a stop, so a table under
    ``## WaterOtakara (60)`` binds 60 and not an earlier Source-ID line. Returns
    ``{source_id: gate_table}``.
    """
    lines = markdown.splitlines()
    by_name = {entry.enum_name for entry in roster}
    bound: dict[int, dict] = {}
    for start, block in _iter_tables(markdown):
        table = _extract_gate_table(block)
        if not table:
            continue
        owner = None
        for idx in range(start - 1, -1, -1):
            line = lines[idx]
            if _OWNER_LINE_RE.search(line):
                owner = _owner_from_line(line, by_name)
                if owner is not None:
                    break
            elif line.lstrip().startswith("#"):
                owner = _owner_from_line(line, by_name)
                if owner is not None:
                    break
        if owner is not None and owner not in bound:
            bound[owner] = table
    return bound


def _ingest_identity(entry, table: dict[int, dict] | None) -> dict:
    role = identity_role(entry)
    if table is None:
        # Named in the handoff but no table of its own: never advanced.
        candidate = replace(entry, gates={gate: "UNTESTED" for gate in GATE_IDS},
                            notes=(), delivery_receipt=None)
        return {"source_id": entry.source_id, "enum_name": entry.enum_name, "role": role,
                "shared": True, "advances": [], "refused": {},
                "blocking": admission_requirements(candidate)}
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
    return {"source_id": entry.source_id, "enum_name": entry.enum_name, "role": role,
            "advances": advances, "refused": refused,
            "blocking": admission_requirements(candidate)}


def ingest(markdown: str, roster=None) -> list[dict]:
    """Parse a handoff into per-identity candidate rows (no writes)."""
    roster = roster if roster is not None else load_and_validate()
    base = by_id(roster)
    bound = _bound_tables(markdown, roster)
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
        rows.append(_ingest_identity(entry, bound.get(source_id)))
    return rows


def apply_ingested_gates(rows: list[dict], ledger_path) -> list[tuple[str, list[str]]]:
    """Merge validated advanced gates into an evidence overlay (merge-only)."""
    path = Path(ledger_path)
    if not path.is_file():
        raise FileNotFoundError(f"ledger not found: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.setdefault("entries", {})
    changed: list[tuple[str, list[str]]] = []
    for row in rows:
        if row.get("skipped") or row.get("shared") or row["source_id"] is None:
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
    if row.get("skipped"):
        return [f"{row['source_id']} {row['enum_name']} (role={row['role']}): "
                f"skipped (non-seedable role)"]
    head = f"{row['source_id']} {row['enum_name']} (role={row['role']})"
    if row.get("shared"):
        head += " (shared table, excluded)"
    lines = [head + ":"]
    lines.append(f"  advances: {', '.join(row['advances']) or '(none)'}")
    if row.get("refused"):
        details = ", ".join(f"{gate}:{reason}" for gate, reason in sorted(row["refused"].items()))
        lines.append(f"  refused PASS: {details}")
    lines.append(f"  blocking (admission_requirements): {', '.join(row['blocking']) or '(none)'}")
    return lines


def build_advance_report(docs, roster=None) -> dict:
    """Aggregate a dry-run across ``[(handoff_label, markdown), ...]``.

    Deterministic: identities are keyed/sorted by ``source_id``, gates by
    ``GATE_IDS`` order and handoffs are name-sorted. Returns ``{"identities":
    [...], "summary": {gates_away: count}, "total": n, "handoffs": {label:
    [(source_id, enum_name), ...]}}``.
    """
    roster = roster if roster is not None else load_and_validate()
    base = by_id(roster)
    merged: dict[int, dict] = {}
    handoffs: dict[str, list[tuple[int, str | None]]] = {}
    for label, markdown in docs:
        found: dict[int, str | None] = {}
        for row in ingest(markdown, roster):
            if row.get("skipped") or row["role"] == "unknown":
                found.setdefault(row["source_id"],
                                 base[row["source_id"]].enum_name
                                 if row["source_id"] in base else None)
                continue
            source_id = row["source_id"]
            found.setdefault(source_id, row["enum_name"])
            rec = merged.setdefault(source_id, {
                "source_id": source_id, "enum_name": row["enum_name"], "role": row["role"],
                "handoffs": [], "advances": set(), "refused": {}, "shared": True,
            })
            if label not in rec["handoffs"]:
                rec["handoffs"].append(label)
            rec["advances"] |= set(row["advances"])
            if not row.get("shared"):
                # Any handoff that binds a table for this identity makes it a real
                # candidate; "shared" stays True only when none does.
                rec["shared"] = False
            for gate, reason in row.get("refused", {}).items():
                rec["refused"].setdefault(gate, set()).add(reason)
        handoffs[label] = [(sid, found[sid]) for sid in sorted(found)]
    identities = []
    for source_id in sorted(merged):
        rec = merged[source_id]
        advances = [gate for gate in GATE_IDS if gate in rec["advances"]]
        blocking = [gate for gate in GATE_IDS if gate not in rec["advances"]]
        identities.append({
            "source_id": source_id, "enum_name": rec["enum_name"], "role": rec["role"],
            "handoffs": sorted(rec["handoffs"]),
            "advances": advances,
            "refused": {gate: sorted(rec["refused"][gate]) for gate in sorted(rec["refused"])},
            "shared": rec["shared"],
            "blocking": blocking,
            "gates_away": len(blocking),
        })
    summary = {gates: 0 for gates in range(7)}
    for row in identities:
        summary[row["gates_away"]] += 1
    return {"identities": identities, "summary": summary, "total": len(identities),
            "handoffs": handoffs}


def render_advance_report(report: dict, branch: str) -> str:
    """Render ``build_advance_report`` output as deterministic markdown."""
    command = f"py -3.12 scripts/generate_p2_advance_report.py --branch {branch}"
    lines = [
        "# P2 roster advance report (dry run)",
        "",
        "Deny-by-default admission dry-run across every lane handoff on",
        f"`{branch}`. Per identity: the gates the handoff(s) would",
        "advance, the PASSes refused and why (`uncited` / `injected` / `shared table`),",
        "and the gates still blocking `admission_requirements`. Nothing is admitted and",
        "nothing is written (dry run).",
        "",
        "Regenerate with:",
        "",
        "    " + command,
        "",
        "## Handoffs read",
        "",
    ]
    for label in sorted(report["handoffs"]):
        sids = report["handoffs"][label]
        if not sids:
            lines.append(f"- {label}: (none)")
        else:
            parts = ", ".join(f"{sid} {name}" if name else str(sid) for sid, name in sids)
            lines.append(f"- {label}: {parts}")
    lines += [
        "",
        "## Gates-away summary",
        "",
        "| Gates away from admission | Identities |",
        "|---:|---:|",
    ]
    for gates in range(7):
        lines.append(f"| {gates} | {report['summary'].get(gates, 0)} |")
    lines += [
        "",
        f"Seedable (`source`/`variant`) identities named across handoffs: {report['total']}",
        "",
        "## Per-identity detail",
    ]
    for row in report["identities"]:
        lines.append("")
        head = f"### {row['source_id']} {row['enum_name']} ({row['role']})"
        if row["shared"]:
            head += " — shared table, excluded"
        lines.append(head)
        lines.append(f"- handoffs: {', '.join(row['handoffs'])}")
        lines.append(f"- advances: {', '.join(row['advances']) or '(none)'}")
        if row["refused"]:
            refused = ", ".join(f"{gate}={','.join(reasons)}"
                                for gate, reasons in row["refused"].items())
            lines.append(f"- refused: {refused}")
        lines.append(f"- blocking: {', '.join(row['blocking']) or '(none)'}")
    return "\n".join(lines) + "\n"


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
