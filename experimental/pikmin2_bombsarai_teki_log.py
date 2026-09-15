"""Root-side marker validator for the lane-27 BombSarai teki carrier binding.

Parses the ``P2_BOMBSARAI_TEKI_*`` marker stream emitted by
``pc_port/pc_p2_bombsarai_teki.cpp`` plus the Pod corpse receipt into a set of
per-marker flip flags used to gate the slice-4 acceptance. Dependency-free.
"""
import math

_PASS_GATE_DEFAULTS = {
    "ready": False,          # P2_BOMBSARAI_TEKI_READY  (generated actor bound)
    "supplied": False,       # P2_BOMBSARAI_TEKI_SUPPLY  (bomb born from the pool)
    "joint_follow": False,   # P2_BOMBSARAI_TEKI_JOINT_FOLLOW (captured payload rode the carrier)
    "thrown": False,         # P2_BOMBSARAI_TEKI_THROW  (Release/Fall/Death lob)
    "blasted": False,        # P2_BOMBSARAI_TEKI_BLAST  (blast applied to live receivers)
    "dead": False,           # P2_BOMBSARAI_TEKI_DEAD   (killed by ordinary Pikmin)
    "corpse": False,         # P2_POD_RECEIPT ... bombsarai ... corpse receipt credited
}
_THROWN_KINDS = ("Release", "Fall", "Death")
_ENGAGED_NEAREST = 60.0


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _as_str(value):
    return value if value else None


_PROBE_FIELDS = (("tick", _as_int), ("y", _as_float),
                 ("nearest", _as_float), ("squad", _as_int))
_CORPSE_FIELDS = (("tick", _as_int), ("moved", _as_float), ("carriers", _as_int))
_CORPSE_CONFIG_FIELDS = (("carry_min", _as_int), ("carry_max", _as_int))
_MOVE_FIELDS = (("tick", _as_int), ("state", _as_str), ("x", _as_float),
                ("z", _as_float), ("lane", _as_float), ("host", _as_float))
_HIT_FIELDS = (("kind", _as_str), ("hp_before", _as_float),
               ("hp_after", _as_float), ("applied", _as_int),
               ("alive_after", _as_int))
_FORGET_FIELDS = (("bound_before", _as_int), ("corpse_before", _as_int),
                  ("bound_after", _as_int), ("corpse_after", _as_int))
_RESET_FIELDS = _FORGET_FIELDS
_REENTRY_FIELDS = (("bound_before", _as_int),
                   ("bound_after_reset", _as_int),
                   ("corpse_after_reset", _as_int),
                   ("bound_after", _as_int), ("corpse_after", _as_int))


def _move_travel(moves):
    points = [(m["x"], m["z"]) for m in moves
              if m["x"] is not None and m["z"] is not None]
    if len(points) < 2:
        return None
    travel = 0.0
    for (x0, z0), (x1, z1) in zip(points, points[1:]):
        travel += math.hypot(x1 - x0, z1 - z0)
    return travel


def _parse_fields(tokens, field_spec):
    fields = {name: None for name, _ in field_spec}
    for token in tokens:
        key, sep, value = token.partition("=")
        if not sep:
            continue
        for name, parse in field_spec:
            if key == name:
                fields[name] = parse(value)
                break
    return fields


def _parse_probe(tokens):
    return _parse_fields(tokens, _PROBE_FIELDS)


def validate_teki_markers(log_text):
    """Parse the teki marker stream into per-marker flip flags.

    Returns ``{"gates": {...bool...}, "blasts": int, "pikmin_hits": int,
    "throw_kind": str|None, "probes": [...], "min_y": float|None,
    "max_nearest": float|None, "engaged": bool, "corpse_probes": [...],
    "corpse_max_carriers": int, "corpse_moved": float|None,
    "corpse_config": {...}|None, "transported": bool}``. Empty log -> all-false.
    Unknown/malformed lines are ignored; a recognized marker with a missing
    generator value degrades silently (its gate stays False) rather than
    raising. Per-probe numeric fields that are missing or malformed parse to
    ``None`` without raising; ``min_y``/``max_nearest`` ignore those ``None``
    values. ``engaged`` is True iff at least one probe has ``squad >= 1`` and
    ``nearest <= 60.0``. ``corpse_max_carriers``/``corpse_moved`` aggregate the
    per-second corpse probes (0/None when absent); ``transported`` is True iff
    the corpse was ever carried or a ``P2_POD_RECEIPT`` credited ``bombsarai``.
    """
    gates = dict(_PASS_GATE_DEFAULTS)
    blasts = 0
    pikmin_hits = 0
    throw_kind = None
    probes = []
    corpse_probes = []
    corpse_config = None
    receipt_bombsarai = False
    moves = []
    hits = []
    forget = None
    reentry = None
    reentry_pass = False
    if not log_text:
        return {"gates": gates, "blasts": 0, "pikmin_hits": 0,
                "throw_kind": None, "probes": [], "min_y": None,
                "max_nearest": None, "engaged": False,
                "corpse_probes": [], "corpse_max_carriers": 0,
                "corpse_moved": None, "corpse_config": None,
                "transported": False, "moves": [], "move_travel": None,
                "states_seen": [], "hits": [], "hit_damage": None,
                "forget": None, "reentry": None, "reentry_pass": False}
    for line in log_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        tokens = stripped.split()
        marker = tokens[0]
        if marker == "P2_BOMBSARAI_TEKI_READY":
            gates["ready"] = True
        elif marker == "P2_BOMBSARAI_TEKI_SUPPLY":
            gates["supplied"] = True
        elif marker == "P2_BOMBSARAI_TEKI_JOINT_FOLLOW":
            gates["joint_follow"] = True
        elif marker == "P2_BOMBSARAI_TEKI_THROW":
            gates["thrown"] = True
            for token in tokens[1:]:
                if token.startswith("kind="):
                    kind = token[len("kind="):]
                    if kind in _THROWN_KINDS:
                        throw_kind = kind
        elif marker == "P2_BOMBSARAI_TEKI_BLAST":
            gates["blasted"] = True
            blasts += 1
            for token in tokens[1:]:
                if token.startswith("pikmin_hits="):
                    try:
                        pikmin_hits += int(token[len("pikmin_hits="):])
                    except ValueError:
                        pass
        elif marker == "P2_BOMBSARAI_TEKI_DEAD":
            gates["dead"] = True
        elif marker == "P2_BOMBSARAI_TEKI_PROBE":
            probes.append(_parse_probe(tokens[1:]))
        elif marker == "P2_BOMBSARAI_TEKI_CORPSE":
            corpse_probes.append(_parse_fields(tokens[1:], _CORPSE_FIELDS))
        elif marker == "P2_BOMBSARAI_TEKI_CORPSE_CONFIG":
            corpse_config = _parse_fields(tokens[1:], _CORPSE_CONFIG_FIELDS)
        elif marker == "P2_BOMBSARAI_TEKI_MOVE":
            moves.append(_parse_fields(tokens[1:], _MOVE_FIELDS))
        elif marker == "P2_BOMBSARAI_TEKI_HIT":
            hits.append(_parse_fields(tokens[1:], _HIT_FIELDS))
        elif marker == "P2_BOMBSARAI_TEKI_FORGET":
            forget = _parse_fields(tokens[1:], _FORGET_FIELDS)
        elif marker == "P2_BOMBSARAI_TEKI_RESET":
            _parse_fields(tokens[1:], _RESET_FIELDS)
        elif marker == "P2_BOMBSARAI_TEKI_REENTRY":
            reentry = _parse_fields(tokens[1:], _REENTRY_FIELDS)
        elif marker == "P2_BOMBSARAI_TEKI_REENTRY_PASS":
            if len(tokens) > 1 and tokens[1] == "1":
                reentry_pass = True
        elif marker in ("P2_POD_RECEIPT", "[Pikipelago]") and "bombsarai" in stripped:
            gates["corpse"] = True
            if "P2_POD_RECEIPT" in stripped:
                receipt_bombsarai = True
    ys = [p["y"] for p in probes if p["y"] is not None]
    nearests = [p["nearest"] for p in probes if p["nearest"] is not None]
    engaged = any(p["squad"] is not None and p["squad"] >= 1
                  and p["nearest"] is not None
                  and p["nearest"] <= _ENGAGED_NEAREST for p in probes)
    carrier_counts = [p["carriers"] for p in corpse_probes
                      if p["carriers"] is not None]
    moveds = [p["moved"] for p in corpse_probes if p["moved"] is not None]
    corpse_max_carriers = max(carrier_counts) if carrier_counts else 0
    states_seen = []
    for move in moves:
        state = move["state"]
        if state is not None and state not in states_seen:
            states_seen.append(state)
    damages = [h["hp_before"] - h["hp_after"] for h in hits
               if h["hp_before"] is not None and h["hp_after"] is not None]
    return {"gates": gates, "blasts": blasts, "pikmin_hits": pikmin_hits,
            "throw_kind": throw_kind, "probes": probes,
            "min_y": min(ys) if ys else None,
            "max_nearest": max(nearests) if nearests else None,
            "engaged": engaged,
            "corpse_probes": corpse_probes,
            "corpse_max_carriers": corpse_max_carriers,
            "corpse_moved": max(moveds) if moveds else None,
            "corpse_config": corpse_config,
            "transported": corpse_max_carriers >= 1 or receipt_bombsarai,
            "moves": moves,
            "move_travel": _move_travel(moves),
            "states_seen": states_seen,
            "hits": hits,
            "hit_damage": max(damages) if damages else None,
            "forget": forget,
            "reentry": reentry,
            "reentry_pass": reentry_pass}
