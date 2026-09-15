"""Lane-29 validator for the NATURAL Kurage carcass -> Research Pod receipt (#243).

Distinct from :mod:`experimental.pikmin2_kurage_runtime`, which parses the
*isolated* ``p2_kurage_runtime`` replacement-main fixture (an injected
``health_zero`` death that only asserts the receipt resolver). This module parses
the *production* ``nectar.exe --experimental-pikmin2-room`` run log and requires
the full natural chain: a real generated proxy death, a carcass Pellet, a
FreeMode grasp that latches TransportMode carriers, a moving haul, and the Pod
crediting ``corpse:kurage:<generator>`` through ``pc_p2_preview_deliver``.

It never builds, runs, or hardcodes any absolute path; the optional source-tree
probe resolves the tree root from ``PIKMIN_NATIVE_ROOT`` and degrades to
``None``/``False`` when absent.
"""
import os
import re
from pathlib import Path

RECEIPT_RE = re.compile(
    r"\[Pikipelago\]\s+P2_POD_RECEIPT\s+id=corpse:kurage:(\d+)\s+value=(-?\d+)\s+"
    r"new=(\d+)\s+pokos=(-?\d+)\s+seeds=(\d+)"
)
DEAD_RE = re.compile(r"P2_KURAGE_TEKI_DEAD\s+generator=(\d+)")
CONFIG_RE = re.compile(r"P2_KURAGE_TEKI_CORPSE_CONFIG\s+carry_min=(-?\d+)\s+carry_max=(-?\d+)")
CORPSE_RE = re.compile(r"P2_KURAGE_TEKI_CORPSE\s+tick=(\d+)\s+x=(-?[\d.]+)\s+z=(-?[\d.]+)\s+moved=(-?[\d.]+)\s+carriers=(\d+)")

REQUIRED_MARKERS = (
    "P2_KURAGE_TEKI_READY generator=",
    "P2_KURAGE_TEKI_DEAD generator=",
    "P2_KURAGE_TEKI_CORPSE_CONFIG",
    "P2_KURAGE_TEKI_CAPTAIN_PARK",
    "P2_KURAGE_TEKI_FREE_RECRUIT",
    "[Pikipelago] P2_POD_RECEIPT id=corpse:kurage:",
    "P2_KURAGE_TEKI_CORPSE_DELIVERED",
)


def parse_receipt(lines):
    """Return the parsed Pod receipt tuple or ``None`` when absent/malformed."""
    for line in lines:
        match = RECEIPT_RE.search(line)
        if match:
            generator, value, new, pokos, seeds = (int(part) for part in match.groups())
            return {"generator": generator, "value": value, "new": new,
                    "pokos": pokos, "seeds": seeds}
    return None


def max_moved(lines):
    """Largest carcass haul distance reported by the ``CORPSE tick`` probes."""
    best = None
    for line in lines:
        match = CORPSE_RE.search(line)
        if match:
            moved = float(match.group(4))
            best = moved if best is None else max(best, moved)
    return best


def max_carriers(lines):
    """Largest simultaneous TransportMode carrier count on the carcass."""
    best = 0
    for line in lines:
        match = CORPSE_RE.search(line)
        if match:
            best = max(best, int(match.group(5)))
    return best


def validate_pod_receipt(lines):
    """Validate a production run log against the natural receipt chain.

    Returns a dict: ``ok`` (all natural markers present and consistent), the
    parsed ``receipt``, the ``generator``, the ``max_moved`` haul and
    ``max_carriers``, and the ``missing`` marker list. ``ok`` is False if the
    receipt is an injected fixture or the haul never moved.
    """
    seen = {marker: any(marker in line for line in lines) for marker in REQUIRED_MARKERS}
    missing = [marker for marker, present in seen.items() if not present]
    receipt = parse_receipt(lines)
    generator = None
    dead = None
    for line in lines:
        match = DEAD_RE.search(line)
        if match:
            dead = int(match.group(1))
    if receipt is not None:
        generator = receipt["generator"]
    if dead is not None and generator is not None and dead != generator:
        missing.append("generator mismatch (dead=%d receipt=%d)" % (dead, generator))
    # An injected fixture that only asserts the resolver must not pass here.
    if any("injected=health_zero" in line for line in lines):
        missing.append("injected=health_zero present (not a natural death)")
    moved = max_moved(lines)
    if moved is None or moved <= 0.0:
        missing.append("carcass never moved (max_moved=%s)" % (moved,))
    carriers = max_carriers(lines)
    if carriers <= 0:
        missing.append("no TransportMode carrier latched (max_carriers=0)")
    return {
        "ok": not missing,
        "missing": missing,
        "generator": generator,
        "dead_generator": dead,
        "receipt": receipt,
        "max_moved": moved,
        "max_carriers": carriers,
    }


def native_pod_chain_present():
    """Confirm the native sidecar still wires the natural Pod carry chain.

    Resolves the tree root from ``PIKMIN_NATIVE_ROOT`` (never a hardcoded path).
    Returns ``None`` when unset, ``False`` when the file is absent or lacks the
    carry-tail markers, and ``True`` when it declares them.
    """
    root = os.environ.get("PIKMIN_NATIVE_ROOT")
    if not root:
        return None
    source = Path(root) / "pc_port" / "pc_p2_kurage_teki.cpp"
    if not source.is_file():
        return False
    text = source.read_text(errors="replace")
    return all(token in text for token in
               ("P2_KURAGE_TEKI_CORPSE", "P2_KURAGE_TEKI_FREE_RECRUIT",
                "P2_KURAGE_TEKI_CAPTAIN_PARK", "P2_KURAGE_TEKI_DEAD"))


def default_sample_log():
    """Representative passing production log (generator 201001, natural haul)."""
    return (
        "P2_KURAGE_VISUAL_MISSING generator=201001 (host body draw)\n"
        "P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter\n"
        "[Pikipelago] P2_POD_READY treasure=bolt value=180 weight=15 capacity=25 pokos=0\n"
        "P2_KURAGE_TEKI_DEAD generator=201001\n"
        "P2_KURAGE_TEKI_CORPSE_CONFIG carry_min=7 carry_max=14 min_free_slot=0 alive=1\n"
        "P2_KURAGE_TEKI_CAPTAIN_PARK x=81.150 z=427.742\n"
        "P2_KURAGE_TEKI_FREE_RECRUIT count=18 carriers=0 squad=18\n"
        "P2_KURAGE_TEKI_CORPSE tick=30 x=53.864 z=140.042 moved=29.930 carriers=8\n"
        "P2_KURAGE_TEKI_CORPSE tick=330 x=-89.034 z=-23.373 moved=227.592 carriers=14\n"
        "P2_KURAGE_TEKI_CORPSE tick=630 x=-202.928 z=-184.130 moved=421.858 carriers=15\n"
        "P2_KURAGE_TEKI_CORPSE tick=750 x=-212.791 z=-181.744 moved=426.828 carriers=1\n"
        "[Pikipelago] P2_POD_RECEIPT id=corpse:kurage:201001 value=2 new=1 pokos=2 seeds=0\n"
        "P2_KURAGE_TEKI_CORPSE_DELIVERED\n"
    )
