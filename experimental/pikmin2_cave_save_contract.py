"""Read-only surface checker for the lane-11 cave checkpoint seam (issue #132).

Extracts the cited transfer/entry markers from native-log or wire text WITHOUT
importing any engine module: pure `re` over strings. It mirrors the wire rules
pinned by `engine/pc_port/pc_p2_cave_transfer.h` (schemas 1-3, 32-hex token,
floor 1-2, health in (0, 1], count 1-100, species 0-5, maturity 0-2, no
trailing data) and the write/read/validate marker order driven by
`experimental/pikmin2_cave_restart_runtime.py`. Malformed input fails closed
with ValueError; nothing is executed, built, or mutated.
"""
import re

WRITE_RE = re.compile(r"P2_LANE11_WRITE ok=([01])")
TRANSFER_HEADER_RE = re.compile(r"P2_CAVE_TRANSFER_([123])")
TRANSFER_FLOOR_RE = re.compile(r"P2_CAVE_TRANSFER floor=(\d+) survivors=(\d+) health=([0-9.e+-]+) failed=([01])")
RESTORE_RE = re.compile(r"P2_CAVE_RESTORE species=(\d+) maturity=(\d+)")
READ_RE = re.compile(r"P2_LANE11_READ bulbmin=(\d+)")
PASS_RE = re.compile(r"^PASS P2_LANE11_RESTORE$")
TOKEN_RE = re.compile(r"[0-9a-f]{32}")
MAX_SURVIVORS = 100
MAX_SPECIES = 5


class MarkerError(ValueError):
    pass


def find_markers(text):
    """Map each cited marker to its 1-based line numbers in order of appearance."""
    if not isinstance(text, str):
        raise MarkerError("Expected log text")
    found = {"write": [], "transfer_header": [], "transfer_floor": [],
             "restore": [], "read": [], "pass": []}
    for number, line in enumerate(text.splitlines(), 1):
        if WRITE_RE.search(line):
            found["write"].append(number)
        if TRANSFER_HEADER_RE.search(line):
            found["transfer_header"].append(number)
        if TRANSFER_FLOOR_RE.search(line):
            found["transfer_floor"].append(number)
        if RESTORE_RE.search(line):
            found["restore"].append(number)
        if READ_RE.search(line):
            found["read"].append(number)
        if PASS_RE.search(line):
            found["pass"].append(number)
    return found


def parse_transfer_text(text):
    """Parse and validate a P2_CAVE_TRANSFER_<schema> wire payload.

    Returns (schema, token, floor, health, survivors). Mirrors the native
    clause order: header, then Pikmin, then trailing-data rejection.
    """
    if not isinstance(text, str):
        raise MarkerError("Expected transfer text")
    lines = text.splitlines()
    if len(lines) < 3:
        raise MarkerError("header: truncated transfer")
    header = re.fullmatch(r"P2_CAVE_TRANSFER_([123])", lines[0].strip())
    if not header:
        raise MarkerError("header: unsupported transfer schema")
    schema = int(header.group(1))
    if not re.fullmatch(r"[0-9a-f]{32}", lines[1].strip()):
        raise MarkerError("header: token must be 32 hex chars")
    words = lines[2].split()
    if len(words) != 3:
        raise MarkerError("header: malformed floor line")
    try:
        floor, health, count = int(words[0]), float(words[1]), int(words[2])
    except ValueError:
        raise MarkerError("header: non-numeric floor line") from None
    if floor not in (1, 2):
        raise MarkerError("header: floor must be 1 or 2")
    if not 0 < health <= 1:
        raise MarkerError("header: health must be in (0, 1]")
    if not 1 <= count <= MAX_SURVIVORS:
        raise MarkerError("header: survivor count out of range")
    if len(lines) != 3 + count:
        raise MarkerError("header: survivor line count mismatch")
    survivors = []
    for line in lines[3:]:
        pair = line.split()
        if len(pair) != 2:
            raise MarkerError("Pikmin: malformed survivor line")
        try:
            species, maturity = int(pair[0]), int(pair[1])
        except ValueError:
            raise MarkerError("Pikmin: non-numeric survivor") from None
        if not 0 <= species <= MAX_SPECIES:
            raise MarkerError("Pikmin: species out of range")
        if not 0 <= maturity <= 2:
            raise MarkerError("Pikmin: maturity out of range")
        if species == MAX_SPECIES and schema < 3:
            raise MarkerError("Pikmin: Bulbmin needs transfer schema 3")
        survivors.append((species, maturity))
    return schema, lines[1].strip(), floor, health, survivors


def check_sequence(markers):
    """Verify the write/read/validate marker order of one two-process run."""
    for key in ("write", "transfer_header", "restore", "read", "pass"):
        if not markers.get(key):
            raise MarkerError("Missing marker: " + key)
    if not (markers["write"][0] < markers["transfer_header"][0]
            and markers["restore"][0] > markers["transfer_header"][0]
            and markers["read"][0] >= markers["restore"][0]
            and markers["pass"][0] > markers["read"][0]):
        raise MarkerError("Markers out of write/read/validate order")
    return True


def summarize(text):
    """One-shot audit of a combined run log; returns findings, never raises."""
    try:
        markers = find_markers(text)
        ordered = check_sequence(markers)
    except MarkerError as error:
        return dict(complete=False, reason=str(error), markers={})
    return dict(complete=True, reason="write/read/validate markers in order",
                markers={k: len(v) for k, v in markers.items()})
