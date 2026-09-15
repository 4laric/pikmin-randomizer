"""Host-side validator for the lane-29 Kurage corpse-receipt runtime gate.

The native fixture ``tools/p2_kurage_runtime.cpp`` runs under
``--receiver-corpse-receipt`` and emits a fixed sequence of marker lines that
close the corpse-receipt gate: a bound Lesser Spotted Jellyfloat resolves its
generator, survives a post-death tick via an injected health-zero write, and is
then forgotten so a recycled address never mis-resolves.

This module only parses log text. It never builds, runs, or hardcodes any
absolute native path; the optional source-tree probe resolves the tree root from
``PIKMIN_NATIVE_ROOT`` and degrades to ``None``/``False`` when absent.
"""
import os
import re
from pathlib import Path

REQUIRED_MARKERS = (
    "P2_KURAGE_CORPSE_RECEIPT_PASS generator=",
    "P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=",
    "P2_KURAGE_CORPSE_CLEANUP_PASS forgotten=1 bound=0",
    "PASS KURAGE_RUNTIME corpse_receipt_cleanup",
)

DEAD_CORPSE_RECEIPT_PREFIX = "P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator="
CLEANUP_PREFIX = "P2_KURAGE_CORPSE_CLEANUP_PASS"
PASS_CLEANUP_PREFIX = "PASS KURAGE_RUNTIME corpse_receipt_cleanup"

_GENERATOR_RE = re.compile(r"P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS\s+generator=(\d+)")


def parse_generator(lines):
    """Return the generator number from ``P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS``,
    or ``None`` when the line is absent or malformed."""
    for line in lines:
        match = _GENERATOR_RE.search(line)
        if match:
            return int(match.group(1))
    return None


def validate_corpse_receipt(lines):
    """Validate a corpse-receipt log against ``REQUIRED_MARKERS``.

    Returns a dict summarising presence of each gate marker, the parsed
    generator number, and the marker strings still missing (empty means PASS).
    """
    seen = {marker: any(marker in line for line in lines) for marker in REQUIRED_MARKERS}
    missing = [marker for marker, present in seen.items() if not present]
    return {
        "ok": not missing,
        "corpse_receipt": seen[REQUIRED_MARKERS[0]],
        "dead_corpse_receipt": seen[REQUIRED_MARKERS[1]],
        "cleanup": seen[REQUIRED_MARKERS[2]],
        "pass_marker": seen[REQUIRED_MARKERS[3]],
        "missing": missing,
        "generator": parse_generator(lines),
    }


def native_corpsereceipt_flag_present():
    """Confirm the native fixture still registers ``--receiver-corpse-receipt``.

    Resolves the tree root from ``PIKMIN_NATIVE_ROOT`` (never a hardcoded
    path). Returns ``None`` when the variable is unset, ``False`` when the
    fixture does not exist or lacks the flag, and ``True`` when it declares it.
    """
    root = os.environ.get("PIKMIN_NATIVE_ROOT")
    if not root:
        return None
    fixture = Path(root) / "tools" / "p2_kurage_runtime.cpp"
    if not fixture.is_file():
        return False
    return "--receiver-corpse-receipt" in fixture.read_text(errors="replace")


def default_sample_log():
    """Representative passing corpse-receipt log (generator 201001, live squad
    20, centred 960x540 window) containing every ``REQUIRED_MARKERS`` entry."""
    return (
        "P2_KURAGE_WINDOW size=960x540 pos=450,130 display=1920x1080 centered=1\n"
        "P2_KURAGE_SQUAD live=20\n"
        "P2_KURAGE_RECEIVER_STEP setup\n"
        "P2_KURAGE_CORPSE_RECEIPT_PASS generator=201001 bound=1 drop=BDT_Normal\n"
        "P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=201001 injected=health_zero\n"
        "P2_KURAGE_CORPSE_CLEANUP_PASS forgotten=1 bound=0\n"
        "PASS KURAGE_RUNTIME corpse_receipt_cleanup\n"
    )
