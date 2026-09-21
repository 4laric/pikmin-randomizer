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

TERRAIN_ALLOW = frozenset({"ground", "water", "mixed", "air"})

_HEX64_RE = re.compile(r"[0-9a-fA-F]{64}")
_COMMIT_RE = re.compile(r"[0-9a-fA-F]{7,40}")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

# --- BEGIN proxy-extract2 optional override fields (issue #871) ---
# Small self-contained block validating the data-driven extractor
# overrides; kept delimited so the parallel proxy worker's change to this
# file merges cleanly. Shapes only: registry membership of ``clips``
# sources is checked by the extractor against the ISO (clear error naming
# the species' actual stems).
PARAM_DIR_RE = re.compile(r"[a-z][a-z0-9_]{0,31}")
CLIP_STEM_RE = re.compile(r"[A-Za-z0-9_]+")
METADATA_FILES = ("enemyanimmgr.txt", "enemyparm.txt", "enemycoll.txt",
                  "enemystoneinfo.txt")
# Native clip-name lists the extractor requires cover from (dead/attack /
# move / wait groups); alias keys must come from these.
CANONICAL_CLIPS = frozenset({
    "dead", "dead1", "pdead1",
    "attack1", "attack", "attack2", "charge", "hit_start",
    "move1", "move", "move2", "run1", "walk",
    "wait1", "wait", "wait2",
})


def _optional_overrides(document, path_name):
    """Validate ``asset_dir`` / ``param_dir`` / ``clips`` / ``param_files``.

    Returns ``(asset_dir, param_dir, clips, param_files)`` with ``None`` /
    ``None`` / ``{}`` / ``{}`` defaults. Fails closed on any malformed
    field. ``param_files`` maps a metadata filename to its parameter
    prefix for split families (Volatile Dweevil: shared ``otakara/`` anim
    mgr/collision/stone plus its own ``bombotakara/enemyparm.txt``).
    """
    asset_dir = document.get("asset_dir")
    if asset_dir is not None and (
            not isinstance(asset_dir, str) or not ENUM_RE.fullmatch(asset_dir)):
        raise ValueError(
            f"proxy declaration asset_dir invalid: {path_name}")
    param_dir = document.get("param_dir")
    if param_dir is not None and (
            not isinstance(param_dir, str) or not PARAM_DIR_RE.fullmatch(param_dir)):
        raise ValueError(
            f"proxy declaration param_dir invalid: {path_name}")
    clips = document.get("clips")
    if clips is None:
        clips = {}
    else:
        if not isinstance(clips, dict) or not clips:
            raise ValueError(
                f"proxy declaration clips must be a non-empty object: {path_name}")
        for canonical, source in clips.items():
            if canonical not in CANONICAL_CLIPS:
                raise ValueError(
                    f"proxy declaration clips key not a native clip name: "
                    f"{canonical!r} ({path_name})")
            if not isinstance(source, str) or not CLIP_STEM_RE.fullmatch(source):
                raise ValueError(
                    f"proxy declaration clips source invalid: {source!r} ({path_name})")
            if source == canonical:
                raise ValueError(
                    f"proxy declaration clips alias is a no-op: {canonical!r} ({path_name})")
        if len(set(clips.values())) != len(clips):
            raise ValueError(
                f"proxy declaration clips sources must be distinct: {path_name}")
        clips = dict(clips)
    param_files = document.get("param_files")
    if param_files is None:
        return asset_dir, param_dir, clips, {}
    if not isinstance(param_files, dict) or not param_files:
        raise ValueError(
            f"proxy declaration param_files must be a non-empty object: {path_name}")
    for filename, prefix in param_files.items():
        if filename not in METADATA_FILES:
            raise ValueError(
                f"proxy declaration param_files key not a metadata file: "
                f"{filename!r} ({path_name})")
        if not isinstance(prefix, str) or not PARAM_DIR_RE.fullmatch(prefix):
            raise ValueError(
                f"proxy declaration param_files prefix invalid: {prefix!r} ({path_name})")
    return asset_dir, param_dir, clips, dict(param_files)


# --- END proxy-extract2 optional override fields ---

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


def _validate_terrains(document, path_name):
    """Return the validated terrains list, defaulting to ``["ground"]``."""
    terrains = document.get("terrains", ["ground"])
    if not isinstance(terrains, list) or not terrains:
        raise ValueError(f"proxy declaration terrains must be a non-empty list: {path_name}")
    seen = set()
    for terrain in terrains:
        if not isinstance(terrain, str) or terrain not in TERRAIN_ALLOW:
            raise ValueError(
                f"proxy declaration terrain must be one of {sorted(TERRAIN_ALLOW)}: {path_name}")
        if terrain in seen:
            raise ValueError(f"proxy declaration terrains contains a duplicate: {path_name}")
        seen.add(terrain)
    return list(terrains)


def _validate_evidence(document, path_name):
    """Return the validated evidence block, or ``None`` when absent.

    A present block must carry non-empty ``run``, ``log``, ``log_sha256``
    (64 hex), ``native_commit`` (7-40 hex), ``recorded`` (YYYY-MM-DD) and a
    ``markers`` object whose ``table``, ``bind`` and ``draw`` entries are all
    boolean ``True``. Anything less fails closed.
    """
    evidence = document.get("evidence")
    if evidence is None:
        return None
    if not isinstance(evidence, dict):
        raise ValueError(f"proxy declaration evidence must be an object: {path_name}")
    for key in ("run", "log"):
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"proxy declaration evidence.{key} must be a non-empty string: {path_name}")
    digest = evidence.get("log_sha256")
    if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
        raise ValueError(f"proxy declaration evidence.log_sha256 must be 64 hex: {path_name}")
    commit = evidence.get("native_commit")
    if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
        raise ValueError(f"proxy declaration evidence.native_commit must be 7-40 hex: {path_name}")
    recorded = evidence.get("recorded")
    if not isinstance(recorded, str) or not _DATE_RE.fullmatch(recorded):
        raise ValueError(f"proxy declaration evidence.recorded must be YYYY-MM-DD: {path_name}")
    import datetime as _datetime
    try:
        _datetime.date.fromisoformat(recorded)
    except ValueError as error:
        raise ValueError(
            f"proxy declaration evidence.recorded is not a calendar date: {path_name}") from error
    markers = evidence.get("markers")
    if not isinstance(markers, dict):
        raise ValueError(f"proxy declaration evidence.markers must be an object: {path_name}")
    for key in ("table", "bind", "draw"):
        if markers.get(key) is not True:
            raise ValueError(
                f"proxy declaration evidence.markers.{key} must be true: {path_name}")
    return {
        "run": evidence["run"],
        "log": evidence["log"],
        "log_sha256": digest,
        "native_commit": commit,
        "recorded": recorded,
        "markers": {key: True for key in ("table", "bind", "draw")},
    }


def tier_ids(tier, directory=None):
    """Sorted proxy source ids for one opt-in tier.

    ``"proven"`` returns only rows carrying a valid evidence block;
    ``"declared"`` returns every declared row. Anything else raises
    ``ValueError``.
    """
    if tier not in ("proven", "declared"):
        raise ValueError(f"unknown proxy tier {tier!r}; expected 'proven' or 'declared'")
    rows = load_rows(directory=directory)
    if tier == "declared":
        return sorted(row["source_id"] for row in rows)
    return sorted(row["source_id"] for row in rows if row.get("evidence") is not None)


def load_rows(directory=None):
    """Load and validate every proxy declaration, sorted by source id.

    Fails closed with a clear ``ValueError`` on: a bad schema, a filename not
    matching its content, an enum name not matching the roster for that source
    id, a duplicate source or enum, a source id that already has a non-proxy
    path (anything in today's ``IDENTITY_FAMILY``/``EXTRACTORS`` outside the
    ``proxy``/``extract_proxy`` rows this family owns), a ``pose_limit``
    outside 2..8, a ``host_teki`` outside the safe-vehicle allowlist, a
    ``terrains`` entry outside the proxy terrain allowlist, or a malformed
    ``evidence`` block.
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
        terrains = _validate_terrains(document, path.name)
        evidence = _validate_evidence(document, path.name)
        asset_dir, param_dir, clips, param_files = _optional_overrides(document, path.name)
        row = {
            "schema": SCHEMA,
            "source_id": source_id,
            "enum_name": enum_name,
            "host_teki": host_teki,
            "pose_limit": pose_limit,
            "terrains": terrains,
            "notes": document.get("notes", ""),
            "asset_dir": asset_dir,
            "param_dir": param_dir,
            "clips": clips,
            "param_files": param_files,
        }
        if evidence is not None:
            row["evidence"] = evidence
        rows.append(row)
    rows.sort(key=lambda row: row["source_id"])
    return rows
