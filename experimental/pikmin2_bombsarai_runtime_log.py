"""Root-side parser/validator for the lane-27 BombSarai GL runtime fixture.

Parses the marker stream emitted by ``engine/tools/p2_bombsarai_runtime.cpp``
into a structured per-scenario result. Dependency-free Python 3.

The fixture prints one marker per line. Recognised markers are matched by
their leading token; unknown and auxiliary lines (``P2_BOMBSARAI_FLOOR_PROBE``,
``P2_BOMBSARAI_MAP_PROBES_PASS``, ``BLOCKED`` style logs, etc.) are tolerated.
A recognised marker that lacks its ``scenario=`` token counts as blatant
corruption and raises ``ValueError``.
"""


_DEFAULT_SCENARIO = {
    "joint_follow": False,
    "travel_y": None,
    "throw_kind": None,
    "blast_fired": False,
    "hit_count": None,
    "carrier_dead": False,
    "scenario_pass": False,
}

_PASS_LINE = "PASS BOMBSARAI_RUNTIME"

# Markers the validator tracks. Each must carry a ``scenario=`` token.
_SCENARIO_MARKERS = frozenset((
    "P2_BOMBSARAI_JOINT_FOLLOW",
    "P2_BOMBSARAI_FSM_THROW",
    "P2_BOMBSARAI_BLAST",
    "P2_BOMBSARAI_SCENARIO_PASS",
))


def _field(tokens, key):
    """Return the value of the first ``key=value`` token, or ``None``."""
    prefix = key + "="
    for token in tokens:
        if token.startswith(prefix):
            return token[len(prefix):]
    return None


def _parse_int(tokens, key):
    raw = _field(tokens, key)
    if raw is None:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _parse_float(tokens, key):
    raw = _field(tokens, key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _blank():
    return dict(_DEFAULT_SCENARIO)


def _scenarios(names):
    return {name: _blank() for name in names}


def validate_markers(log_text, scenarios=('approach', 'purple', 'death')):
    """Parse the native fixture marker stream.

    Returns ``{"passed": bool, "scenarios": {...}}``. A missing/empty log
    yields the all-false/None structure without raising. Malformed marker
    lines (recognised marker without ``scenario=``) raise ``ValueError``;
    unknown/extra lines and out-of-order lines are ignored, and individually
    malformed numeric fields degrade to ``None`` instead of aborting.
    """
    result = {
        "passed": False,
        "scenarios": _scenarios(scenarios),
    }
    if not log_text:
        return result

    for line in log_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == _PASS_LINE:
            result["passed"] = True
            continue
        tokens = stripped.split()
        marker = tokens[0]
        if marker not in _SCENARIO_MARKERS:
            continue
        name = _field(tokens, "scenario")
        if name is None:
            raise ValueError("malformed marker line: %r" % line)
        if name not in result["scenarios"]:
            continue
        entry = result["scenarios"][name]
        if marker == "P2_BOMBSARAI_JOINT_FOLLOW":
            entry["joint_follow"] = True
            entry["travel_y"] = _parse_float(tokens, "travel_y")
        elif marker == "P2_BOMBSARAI_FSM_THROW":
            entry["throw_kind"] = _field(tokens, "kind")
        elif marker == "P2_BOMBSARAI_BLAST":
            entry["blast_fired"] = True
            entry["hit_count"] = _parse_int(tokens, "hits")
            entry["carrier_dead"] = _field(tokens, "carrier_dead") == "1"
        elif marker == "P2_BOMBSARAI_SCENARIO_PASS":
            entry["scenario_pass"] = True
    return result
