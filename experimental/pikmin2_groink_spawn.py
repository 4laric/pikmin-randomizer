"""Root-side gate 1 validator for lane 21 Groink spawn (source_id=78).

Gate 1 requires a natural ordinary-seed observation chain, not fixture-only
attachment:

- Ordinary generator birth resolves the seeded identity:
  ``P2_SEED_RESOLVE source_id=78 target=<seed target> original_type=<P1 type>
  x=<x> z=<z>`` (native `src/plugPikiNakata/genteki.cpp:140-141`). In that line,
  ``target`` is the seed-target UID, which is distinct from the native generator
  file identifier (`_70`).
- An accepted lane-04 sidecar joins the physical generator to the catalog slot:
  ``P2_PLACEMENT_SLOT generator=<generator file id> slot=<seed slot> ...``
  (`pc_port/pc_p2_placement_probe.cpp:101`).
- A future MiniHoudai generated-placement claim emits an explicit
  ``source_id=78`` marker. The accepted contract is a generated-placement claim
  and a Groink family bind marker that both carry the same seed-target UID and
  physical generator identifier::

      P2_GENERATED_PLACEMENT source_id=78 target=<seed target> bound=1
      P2_GROINK_TEKI_BIND source_id=78 seed_target=<seed target>
          generator=<generator file id> bound=1

No current native emitter produces that `case 78` pair, so this module is an
acceptance/model contract for a future log. It intentionally does not accept a
staged Groink carcass-sidecar marker as identity evidence: that marker lacks a
source ID and can be emitted for a fixture-bound P1 host.
"""
import re

SOURCE_ID = 78
RESOLVE_MARKER = "P2_SEED_RESOLVE"
GENERATED_CLAIM_MARKER = "P2_GENERATED_PLACEMENT"
GROINK_BIND_MARKER = "P2_GROINK_TEKI_BIND"
PLACEMENT_MARKER = "P2_PLACEMENT_SLOT"

_KV_RE = re.compile(r"(\w+)\s*=\s*([^\s]+)")


def _parse_kv(line: str) -> dict:
    """Return explicit key=value pairs from a single log line."""
    return {key: value for key, value in _KV_RE.findall(line)}


def _is_target(value: "str | None", expected: str) -> bool:
    return value is not None and value == expected


def validate_log(log: str) -> dict:
    """Check whether a native log contains a connected natural 78-spawn chain."""
    resolve_line = bind_line = claim_line = placement_line = None
    resolve_line_number = bind_line_number = None
    claim_line_number = placement_line_number = None
    resolve_target = bind_target = bind_generator = placement_slot = None
    placement_generator = None

    lines = log.splitlines() if log else []
    for index, line in enumerate(lines, start=1):
        if resolve_line is None and RESOLVE_MARKER in line:
            kv = _parse_kv(line)
            if kv.get("source_id") == "78" and "target" in kv:
                resolve_line = line
                resolve_line_number = index
                resolve_target = kv["target"]
        if claim_line is None and GENERATED_CLAIM_MARKER in line:
            kv = _parse_kv(line)
            if kv.get("source_id") == "78" and "target" in kv:
                claim_line = line
                claim_line_number = index
        if bind_line is None and GROINK_BIND_MARKER in line:
            kv = _parse_kv(line)
            if kv.get("source_id") == "78" and "seed_target" in kv and "generator" in kv:
                bind_line = line
                bind_line_number = index
                bind_target = kv["seed_target"]
                bind_generator = kv["generator"]
        if placement_line is None and PLACEMENT_MARKER in line:
            kv = _parse_kv(line)
            if "slot" in kv and "generator" in kv:
                placement_line = line
                placement_line_number = index
                placement_slot = kv["slot"]
                placement_generator = kv["generator"]

    connected = (
        resolve_line is not None
        and claim_line is not None
        and bind_line is not None
        and placement_line is not None
        and _is_target(resolve_target, placement_slot or "")
        and _is_target(bind_target, resolve_target or "")
        and bind_generator == placement_generator
    )
    missing = []
    if resolve_line is None:
        missing.append(f"{RESOLVE_MARKER} source_id=78")
    if claim_line is None:
        missing.append(f"{GENERATED_CLAIM_MARKER} source_id=78")
    if bind_line is None:
        missing.append(f"{GROINK_BIND_MARKER} source_id=78")
    if placement_line is None:
        missing.append(PLACEMENT_MARKER)

    return {
        "passed": connected,
        "connected": connected,
        "source_id": SOURCE_ID,
        "resolve_target": resolve_target,
        "bind_target": bind_target,
        "bind_generator": bind_generator,
        "placement_slot": placement_slot,
        "placement_generator": placement_generator,
        "resolve_line": resolve_line,
        "resolve_line_number": resolve_line_number,
        "claim_line": claim_line,
        "claim_line_number": claim_line_number,
        "bind_line": bind_line,
        "bind_line_number": bind_line_number,
        "placement_line": placement_line,
        "placement_line_number": placement_line_number,
        "missing": missing,
    }
