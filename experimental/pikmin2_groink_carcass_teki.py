"""Root-side validator for the native Groink carcass sidecar seams (#198/#209).

Lane 21 slice 2 binds the parked ``P2GroinkCarcass`` policy to a live generated
Groink actor in ``pc_port/pc_p2_groink_teki.cpp``. That module emits an ordered
set of ``P2_GROINK_CARCASS_*`` host markers (READY -> BECOME -> GAUGE_ACTIVE ->
KILL_PELLET+BIRTH, with GAUGE_INACTIVE on early pellet death). The sidecar is a
native seam: if the carcass-birth marker (the ``RequestBirth`` host command) is
stripped, the revival contract is silently broken and nothing at runtime reloads
the replacement object.

This validator locates the source of truth through ``PIKMIN_NATIVE_ROOT`` only
(no lane-specific paths) and fails when a required marker is missing, so a
regression that drops the birth seam is caught in the root suite.
"""
import os
from pathlib import Path

MARKERS = (
    "P2_GROINK_CARCASS_READY",
    "P2_GROINK_CARCASS_BECOME",
    "P2_GROINK_CARCASS_GAUGE_ACTIVE",
    "P2_GROINK_CARCASS_GAUGE_INACTIVE",
    "P2_GROINK_CARCASS_KILL_PELLET",
    "P2_GROINK_CARCASS_BIRTH",
)
_BIRTH_MARKER = "P2_GROINK_CARCASS_BIRTH"


def native_source() -> "Path | None":
    """Return the native sidecar source located through PIKMIN_NATIVE_ROOT."""
    root = os.environ.get("PIKMIN_NATIVE_ROOT")
    if not root:
        return None
    candidate = Path(root) / "pc_port" / "pc_p2_groink_teki.cpp"
    return candidate if candidate.is_file() else None


def missing_markers(text: str) -> "list[str]":
    return [marker for marker in MARKERS if marker not in text]


def has_birth_marker(text: str) -> bool:
    return _BIRTH_MARKER in text


def validate(text: str) -> dict:
    """Return {'passed': bool, 'missing': [...]} for a native source/result."""
    missing = missing_markers(text)
    return {"passed": not missing, "missing": missing}
