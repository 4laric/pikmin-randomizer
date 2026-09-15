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


def _parse_bool(tokens, key):
    raw = _field(tokens, key)
    if raw is None:
        return None
    return raw == "1"


def _parse_carrier(tokens):
    """Return the carrier index, defaulting absent/malformed ``carrier=`` to 0."""
    raw = _field(tokens, "carrier")
    if raw is None:
        return 0
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return 0


def _blank_carrier():
    return {
        "joint_follow": False,
        "travel_y": None,
        "travel_xz": None,
        "throw_kind": None,
        "blast_fired": False,
        "blast_token": None,
        "blast_carrier_valid": None,
        "hit_count": None,
        "carrier_dead": False,
    }


def _carrier_entry(entry, carrier_index):
    carriers = entry["carriers"]
    if carrier_index not in carriers:
        carriers[carrier_index] = _blank_carrier()
    return carriers[carrier_index]


def _blank():
    entry = dict(_DEFAULT_SCENARIO)
    entry["carriers"] = {}
    return entry


def _scenarios(names):
    return {name: _blank() for name in names}


def validate_markers(log_text, scenarios=('approach', 'purple', 'death')):
    """Parse the native fixture marker stream.

    Returns ``{"passed": bool, "scenarios": {...}}``. A missing/empty log
    yields the all-false/None structure without raising. Malformed marker
    lines (recognised marker without ``scenario=``) raise ``ValueError``;
    unknown/extra lines and out-of-order lines are ignored, and individually
    malformed numeric fields degrade to ``None`` instead of aborting.

    ``passed`` is only True when a ``PASS BOMBSARAI_RUNTIME`` line is present
    AND every requested scenario reports ``scenario_pass`` AND (when the
    ``multi`` scenario was requested) the ``multi`` carriers record at least
    two distinct blast tokens and at least one carrier with ``travel_xz > 0``.
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
            carrier = _carrier_entry(entry, _parse_carrier(tokens))
            carrier["joint_follow"] = True
            carrier["travel_y"] = _parse_float(tokens, "travel_y")
            carrier["travel_xz"] = _parse_float(tokens, "travel_xz")
        elif marker == "P2_BOMBSARAI_FSM_THROW":
            entry["throw_kind"] = _field(tokens, "kind")
            carrier = _carrier_entry(entry, _parse_carrier(tokens))
            carrier["throw_kind"] = _field(tokens, "kind")
        elif marker == "P2_BOMBSARAI_BLAST":
            entry["blast_fired"] = True
            entry["hit_count"] = _parse_int(tokens, "hits")
            entry["carrier_dead"] = _field(tokens, "carrier_dead") == "1"
            carrier = _carrier_entry(entry, _parse_carrier(tokens))
            carrier["blast_fired"] = True
            carrier["blast_token"] = _parse_int(tokens, "token")
            carrier["blast_carrier_valid"] = _parse_bool(tokens, "carrier_valid")
            carrier["hit_count"] = _parse_int(tokens, "hits")
            carrier["carrier_dead"] = _field(tokens, "carrier_dead") == "1"
        elif marker == "P2_BOMBSARAI_SCENARIO_PASS":
            entry["scenario_pass"] = True

    if result["passed"]:
        for entry in result["scenarios"].values():
            if not entry["scenario_pass"]:
                result["passed"] = False
        multi = result["scenarios"].get("multi")
        if multi is not None:
            tokens = {carrier["blast_token"] for carrier in multi["carriers"].values()
                      if carrier["blast_token"] is not None}
            if len(tokens) < 2:
                result["passed"] = False
            if not any(carrier["travel_xz"] is not None and carrier["travel_xz"] > 0
                       for carrier in multi["carriers"].values()):
                result["passed"] = False
    return result
