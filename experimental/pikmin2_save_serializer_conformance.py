"""Durable save serializer conformance contract (#712).

Root-only tooling producer for the provider-save-progression partition.
Re-verifies the #658 save-block pins read-only against the canonical native
research tree and specifies the per-area / per-squad / per-captain
round-trip conformance contract with size-guard and malformed-input
negatives. No engine execution, no save-format change, no shared/family/
native edits, no ADMIT.

Pin basis (#658, re-verified this turn against
`native/pikmin2-research/src/plugProjectKandoU/gamePlayDataMemCard.cpp`):

- PlayData::write:39 / PlayData::read:707 (durable save entry; version,
  treasure count, debt flags, ...).
- OlimarData::write:1346 / OlimarData::read:1360 (captain flag bytes x2).
- CaveSaveData::write:1372 / CaveSaveData::read:1411 (formation Pikmin,
  time, course/cave/floor, waterwraith state, version-gated fields behind
  the `size` guard, e.g. `if ('j009' <= size)`).
"""

RESEARCH_REL = ("native/pikmin2-research/src/plugProjectKandoU/"
                "gamePlayDataMemCard.cpp")

# (symbol, line, role). Lines are re-verified, never assumed.
PINS = (
    ("PlayData::write", 39, "durable save entry"),
    ("PlayData::read", 707, "restore entry"),
    ("OlimarData::write", 1346, "captain block write"),
    ("OlimarData::read", 1360, "captain block restore"),
    ("CaveSaveData::write", 1372, "cave payload write"),
    ("CaveSaveData::read", 1411, "cave payload restore (size-guarded)"),
)

# Abstract block shapes mirroring the observed field order. These are
# contract records for the conformance checker, not engine values.
BLOCK_FIELDS = {
    "playdata": ("version", "treasure_count", "debt_flags",
                 "area_records", "squad_records", "captain_records"),
    "olimardata": ("flags",),
    "cavesavedata": ("formation", "time", "course_idx", "cave_id",
                     "floor", "waterwraith", "gated"),
}

VERSION_FLOOR = "j009"

DOWNSTREAM = (132, 112, 68, 533, 550, 154, 161)


def read_research_text(research_root):
    """Read the research TU bytes-free of execution; fail closed."""
    from pathlib import Path
    path = Path(research_root) / RESEARCH_REL
    try:
        data = path.read_bytes()
    except OSError:
        raise ValueError("research source unavailable: " + str(path))
    if not data:
        raise ValueError("research source empty: " + str(path))
    return data.decode("utf-8", errors="replace").splitlines()


def verify_pins(research_root):
    """Re-verify every pin; return rows or explicit ABSENT verdicts."""
    try:
        lines = read_research_text(research_root)
    except ValueError as exc:
        return [{"symbol": s, "line": n, "role": r, "status": "ABSENT",
                 "detail": str(exc)} for s, n, r in PINS]
    rows = []
    for symbol, number, role in PINS:
        name = symbol.split("::")[-1]
        if not (1 <= number <= len(lines)):
            rows.append({"symbol": symbol, "line": number, "role": role,
                         "status": "ABSENT",
                         "detail": "line out of range"})
            continue
        got = lines[number - 1]
        if got.strip().startswith("void " + symbol + "("):
            rows.append({"symbol": symbol, "line": number, "role": role,
                         "status": "present",
                         "detail": got.strip()[:90]})
        else:
            rows.append({"symbol": symbol, "line": number, "role": role,
                         "status": "ABSENT",
                         "detail": "expected %r, found %r"
                                   % (symbol, got.strip()[:60])})
    return rows


def all_present(rows):
    return all(row["status"] == "present" for row in rows)


def _check_block(kind, block):
    if not isinstance(block, dict):
        raise ValueError("block must be a mapping")
    fields = BLOCK_FIELDS.get(kind)
    if fields is None:
        raise ValueError("unknown block kind: %r" % (kind,))
    missing = [key for key in fields if key not in block]
    if missing:
        raise ValueError("block %s missing field(s): %s"
                         % (kind, ", ".join(missing)))
    return {key: block[key] for key in fields}


def serialize(kind, block):
    """Deterministic encode of an abstract block (contract bytes)."""
    import json
    record = _check_block(kind, block)
    return json.dumps({"kind": kind, "fields": record},
                      sort_keys=True).encode("utf-8")


def parse(kind, data, size=None):
    """Decode + size-guard abstract block bytes (contract read path)."""
    import json
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError("empty input refused")
    if size is not None and len(data) > size:
        raise ValueError("input exceeds declared size guard")
    try:
        record = json.loads(bytes(data).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ValueError("malformed input refused")
    if not isinstance(record, dict) or record.get("kind") != kind:
        raise ValueError("kind mismatch refused")
    fields = record.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("malformed fields refused")
    if kind == "cavesavedata" and size is not None:
        # Mirrors the source `if ('j009' <= size)` version gate: gated
        # fields are only admitted when the declared size covers them.
        if size < len(data) and "gated" in fields:
            raise ValueError("gated fields exceed declared size guard")
    return _check_block(kind, fields)


def round_trip(kind, block, size=None):
    """Serialize then parse; return True only on exact field equality."""
    expect = _check_block(kind, block)
    got = parse(kind, serialize(kind, block), size=size)
    return got == expect


def review_request():
    """Exact #186 shared-owner review request (text, not an edit)."""
    return (
        "Review requested of #186 (shared-owner review): independent "
        "per-area / per-squad / per-captain save/restore semantics extending "
        "the audited card format at PlayData::write:39/read:707, "
        "OlimarData::write:1346/read:1360 and CaveSaveData::write:1372/"
        "read:1411 (size-guarded), before any engine wire. No save-format "
        "change is proposed or made by this slice."
    )
