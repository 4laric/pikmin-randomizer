"""Root-side validator and config writer for the Groink carcass sidecar (#198/#209).

Lane 21 slice 2 binds the parked ``P2GroinkCarcass`` policy to a live generated
Groink actor (``pc_port/pc_p2_groink_teki.cpp``). The natural revival path emits
an ordered run-log sequence::

    P2_GROINK_CARCASS_READY
    P2_GROINK_CARCASS_BECOME
    P2_GROINK_CARCASS_GAUGE_ACTIVE
    P2_GROINK_CARCASS_KILL_PELLET
    P2_GROINK_CARCASS_BIRTH

``validate_log`` checks a captured run log for that order and flips when a marker
(notably the carcass-birth/RequestBirth marker) is stripped or reordered. A
secondary static guard greps the native seam source for every marker literal so
a regression that drops the emission at its source is also caught; the native
path is resolved only through ``PIKMIN_NATIVE_ROOT`` (no lane-specific paths).

``sidecar_config`` writes the ``p2-groink-teki.txt`` profile the native sidecar
reads at ``GameCoreSection::finalSetup``.
"""
import math
import os
from pathlib import Path

# Happy-path revival order. GAUGE_INACTIVE is a sibling (early pellet death) and
# is validated by presence in the source only, not by this ordering.
ORDER = (
    "P2_GROINK_CARCASS_READY",
    "P2_GROINK_CARCASS_BECOME",
    "P2_GROINK_CARCASS_GAUGE_ACTIVE",
    "P2_GROINK_CARCASS_KILL_PELLET",
    "P2_GROINK_CARCASS_BIRTH",
)
_MARKERS = ORDER + ("P2_GROINK_CARCASS_GAUGE_INACTIVE",)
_BIRTH_MARKER = "P2_GROINK_CARCASS_BIRTH"
CONFIG_MAGIC = "P2_GROINK_TEKI_1"
CONFIG_NAME = "p2-groink-teki.txt"


def validate_log(log: str) -> dict:
    """Ordered run-log validation. Each marker must appear after the previous."""
    missing = []
    pos = -1
    for marker in ORDER:
        nxt = log.find(marker, pos + 1)
        if nxt < 0:
            missing.append(marker)
        else:
            pos = nxt
    return {"passed": not missing, "missing": missing}


def missing_markers(text: str) -> list:
    """Static source guard: every marker literal must be referenced in the seam."""
    return [marker for marker in _MARKERS if marker not in text]


def validate_source(text: str) -> dict:
    missing = missing_markers(text)
    return {"passed": not missing, "missing": missing}


def has_birth_marker(text: str) -> bool:
    return _BIRTH_MARKER in text


def native_source() -> "Path | None":
    """Return the native sidecar source located through PIKMIN_NATIVE_ROOT."""
    root = os.environ.get("PIKMIN_NATIVE_ROOT")
    if not root:
        return None
    candidate = Path(root) / "pc_port" / "pc_p2_groink_teki.cpp"
    return candidate if candidate.is_file() else None


def sidecar_config(generator, teki_type, gauge_delay=30.0, recovery_seconds=10.0, max_health=1200.0):
    """Write the p2-groink-teki.txt profile naming the generated host actor.

    The native reader (``P2_GROINK_TEKI_1 1 <gen> <type> <gaugeDelay>
    <recoverySeconds> <maxHealth>``) binds the Teki at that generator/type and
    hands the three floats to ``P2GroinkCarcass::become``.
    """
    if type(generator) is not int or not 0 < generator <= 0xFFFFFFFF:
        raise ValueError("Invalid Groink generator identity")
    if type(teki_type) is not int or not 0 <= teki_type <= 255:
        raise ValueError("Invalid Groink Teki type")
    values = (gauge_delay, recovery_seconds, max_health)
    if any(not isinstance(v, (int, float)) or not math.isfinite(float(v)) or float(v) < 0.0 for v in values):
        raise ValueError("Invalid Groink carcass config value")
    if float(recovery_seconds) <= 0.0:
        raise ValueError("Groink recovery seconds must be > 0")
    return (f"{CONFIG_MAGIC}\n1\n{generator} {teki_type} "
            f"{float(gauge_delay)} {float(recovery_seconds)} {float(max_health)}\n")
