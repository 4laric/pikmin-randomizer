"""Root-side gate 1 validator for lane 21 Groink spawn (source_id=78).

Lane 21 gate 1 requires a native run log to show seed resolution and a
MiniHoudai bind/ready marker for the same generator/target in the same run::

    P2_SEED_RESOLVE source_id=78 generator=<gen> target=<target> ...
    P2_GROINK_TEKI_<BIND|READY|...> generator=<gen> ...
    P2_GROINK_CARCASS_READY generator=<gen> ...
    P2_PLACEMENT_SLOT generator=<gen> ...

``validate_log`` parses the log string line by line:

* resolve: first line containing ``P2_SEED_RESOLVE`` with an explicit
  ``source_id=78`` key=value match; generator/target identifiers are taken
  from explicit ``key=value`` matches only.
* bind: first same-run MiniHoudai bind/ready marker, covering existing
  ``P2_GROINK_TEKI_*`` forms and the ``P2_GROINK_CARCASS_READY`` form.
* placement: first ``P2_PLACEMENT_SLOT`` line where present (informational
  only; never sufficient for a pass on its own).

Gate 1 passes only when resolve and bind co-occur with the same generator.
A fixture-forced placement line plus a spawn marker without a resolve line
still fails.
"""
import re

SOURCE_ID = 78
RESOLVE_MARKER = "P2_SEED_RESOLVE"
PLACEMENT_MARKER = "P2_PLACEMENT_SLOT"
BIND_READY_MARKER = "P2_GROINK_CARCASS_READY"
_BIND_TEKI_RE = re.compile(r"P2_GROINK_TEKI_[A-Z0-9_]+")
_SOURCE_ID_RE = re.compile(r"(?:^|\s)source_id\s*=\s*78\b")
_KV_RE = re.compile(r"(\w+)\s*=\s*([^\s]+)")

_GENERATOR_KEYS = ("generator", "gen", "generator_id")
_TARGET_KEYS = ("target", "target_generator", "teki_type", "type")


def _parse_kv(line: str) -> dict:
    """Return explicit key=value pairs from a single log line."""
    return {key: value for key, value in _KV_RE.findall(line)}


def _extract_int(kv: dict, keys) -> "int | None":
    for key in keys:
        if key in kv:
            try:
                return int(kv[key], 0)
            except ValueError:
                return None
    return None


def _is_resolve_line(line: str) -> bool:
    return RESOLVE_MARKER in line and _SOURCE_ID_RE.search(line) is not None


def _is_bind_line(line: str) -> bool:
    return BIND_READY_MARKER in line or _BIND_TEKI_RE.search(line) is not None


def _is_placement_line(line: str) -> bool:
    return PLACEMENT_MARKER in line


def validate_log(log: str) -> dict:
    """Check gate 1 resolve+bind co-occurrence for source_id=78.

    Returns a dict with the resolve line/line-number, bind line/line-number,
    placement line/line-number where present, the matched generator, and
    whether resolve+bind co-occur for the same generator.
    """
    resolve_line = None
    resolve_line_number = None
    resolve_generator = None
    resolve_target = None
    bind_line = None
    bind_line_number = None
    bind_generator = None
    placement_line = None
    placement_line_number = None

    lines = log.splitlines() if log else []
    for index, line in enumerate(lines, start=1):
        if resolve_line is None and _is_resolve_line(line):
            kv = _parse_kv(line)
            resolve_line = line
            resolve_line_number = index
            resolve_generator = _extract_int(kv, _GENERATOR_KEYS)
            resolve_target = _extract_int(kv, _TARGET_KEYS)
        if bind_line is None and _is_bind_line(line):
            kv = _parse_kv(line)
            bind_line = line
            bind_line_number = index
            bind_generator = _extract_int(kv, _GENERATOR_KEYS)
        if placement_line is None and _is_placement_line(line):
            placement_line = line
            placement_line_number = index

    matched_generator = None
    cooccurs = False
    if (resolve_line is not None and bind_line is not None
            and resolve_generator is not None and bind_generator is not None
            and resolve_generator == bind_generator):
        matched_generator = resolve_generator
        cooccurs = True

    missing = []
    if resolve_line is None:
        missing.append(RESOLVE_MARKER)
    if bind_line is None:
        missing.append("P2_GROINK_TEKI_BIND_READY")

    # Placement alone is never sufficient: pass requires generator-matched
    # resolve+bind co-occurrence.
    passed = cooccurs

    return {
        "passed": passed,
        "cooccurs": cooccurs,
        "generator": matched_generator,
        "resolve_generator": resolve_generator,
        "resolve_target": resolve_target,
        "bind_generator": bind_generator,
        "resolve_line": resolve_line,
        "resolve_line_number": resolve_line_number,
        "bind_line": bind_line,
        "bind_line_number": bind_line_number,
        "placement_line": placement_line,
        "placement_line_number": placement_line_number,
        "has_placement": placement_line is not None,
        "missing": missing,
    }
