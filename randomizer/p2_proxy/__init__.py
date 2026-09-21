"""Data-driven campaign-proxy species declarations (issue #871).

One JSON file per species so parallel work never edits a shared file:
``randomizer/p2_proxy/<source_id>_<Enum>.json`` with ``schema``, ``source_id``,
``enum_name``, ``host_teki`` (a safe Pikmin 1 vehicle type) and ``pose_limit``.
:func:`load_rows` validates every row fail-closed and returns them sorted by
source id. Admission stays evidence-gated elsewhere; these rows only declare
how a proxy species is extracted and staged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA = 1

ENUM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}")

# Safe Pikmin 1 vehicles a proxy host may use. The placeholder types 26-29 and
# 34 crash the game and are never allowed.
HOST_ALLOW = frozenset({
    0, 2, 3, 4, 6, 8, 9, 11, 15, 16, 17, 18, 19, 20, 24, 25, 30, 31, 32, 33,
})

REPO_ROOT = Path(__file__).resolve().parents[2]
ROSTER_PATH = REPO_ROOT / "docs" / "PIKMIN2_ENEMY_ROSTER.json"


def _roster_enums():
    """Map source id -> enum name from the canonical roster snapshot."""
    try:
        payload = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"proxy roster unreadable: {ROSTER_PATH}: {error}") from error
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"proxy roster carries no entries: {ROSTER_PATH}")
    mapping = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source_id, enum_name = entry.get("source_id"), entry.get("enum_name")
        if type(source_id) is int and isinstance(enum_name, str):
            mapping[source_id] = enum_name
    return mapping


def load_rows(directory=None):
    """Load and validate every proxy declaration, sorted by source id.

    Fails closed with a clear ``ValueError`` on: a bad schema, a filename not
    matching its content, an enum name not matching the roster for that source
    id, a duplicate source or enum, a source id that already has a non-proxy
    path (anything in today's ``IDENTITY_FAMILY``/``EXTRACTORS`` outside the
    ``proxy``/``extract_proxy`` rows this family owns), a ``pose_limit``
    outside 2..8, or a ``host_teki`` outside the safe-vehicle allowlist.
    """
    directory = Path(directory) if directory is not None else Path(__file__).parent
    if not directory.is_dir():
        raise ValueError(f"proxy declaration directory missing: {directory}")
    roster = _roster_enums()
    try:
        from experimental.pikmin2_family_install import IDENTITY_FAMILY
    except Exception:
        IDENTITY_FAMILY = {}
    try:
        from scripts.p2_prepare_content import EXTRACTORS
    except Exception:
        EXTRACTORS = {}
    rows = []
    seen_sources, seen_enums = set(), set()
    for path in sorted(directory.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError(f"proxy declaration unreadable: {path.name}: {error}") from error
        if not isinstance(document, dict):
            raise ValueError(f"proxy declaration malformed: {path.name}")
        if document.get("schema") != SCHEMA or type(document.get("schema")) is not int:
            raise ValueError(f"proxy declaration schema mismatch: {path.name}")
        source_id = document.get("source_id")
        enum_name = document.get("enum_name")
        host_teki = document.get("host_teki")
        pose_limit = document.get("pose_limit")
        if type(source_id) is not int or isinstance(source_id, bool):
            raise ValueError(f"proxy declaration source id invalid: {path.name}")
        if not isinstance(enum_name, str) or not ENUM_RE.fullmatch(enum_name):
            raise ValueError(f"proxy declaration enum name invalid: {path.name}")
        if path.name != f"{source_id}_{enum_name}.json":
            raise ValueError(
                f"proxy declaration filename does not match its content: {path.name}")
        expected = roster.get(source_id)
        if expected is None:
            raise ValueError(f"proxy declaration source id unknown to the roster: {path.name}")
        if expected != enum_name:
            raise ValueError(
                f"proxy declaration enum mismatch for source {source_id}: "
                f"{enum_name!r} != roster {expected!r} ({path.name})")
        if source_id in seen_sources:
            raise ValueError(f"proxy declaration duplicate source id: {source_id}")
        if enum_name in seen_enums:
            raise ValueError(f"proxy declaration duplicate enum name: {enum_name!r}")
        seen_sources.add(source_id)
        seen_enums.add(enum_name)
        family_by_id = IDENTITY_FAMILY.get(source_id)
        family_by_name = IDENTITY_FAMILY.get(enum_name.lower())
        if (family_by_id is not None and family_by_id != "proxy"
                or family_by_name is not None and family_by_name != "proxy"):
            raise ValueError(
                f"proxy declaration source already has a non-proxy family path: {path.name}")
        extractor = EXTRACTORS.get(source_id)
        if extractor is not None and extractor != "extract_proxy":
            raise ValueError(
                f"proxy declaration source already has a non-proxy extractor: {path.name}")
        if type(pose_limit) is not int or isinstance(pose_limit, bool) \
                or not 2 <= pose_limit <= 8:
            raise ValueError(f"proxy declaration pose_limit must be 2..8: {path.name}")
        if type(host_teki) is not int or isinstance(host_teki, bool) \
                or host_teki not in HOST_ALLOW:
            raise ValueError(f"proxy declaration host_teki not an allowed vehicle: {path.name}")
        rows.append({
            "schema": SCHEMA,
            "source_id": source_id,
            "enum_name": enum_name,
            "host_teki": host_teki,
            "pose_limit": pose_limit,
            "notes": document.get("notes", ""),
        })
    rows.sort(key=lambda row: row["source_id"])
    return rows
