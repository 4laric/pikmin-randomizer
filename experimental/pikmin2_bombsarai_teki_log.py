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


_PROBE_FIELDS = (("tick", _as_int), ("y", _as_float),
                 ("nearest", _as_float), ("squad", _as_int))


def _parse_probe(tokens):
    fields = {name: None for name, _ in _PROBE_FIELDS}
    for token in tokens:
        key, sep, value = token.partition("=")
        if not sep:
            continue
        for name, parse in _PROBE_FIELDS:
            if key == name:
                fields[name] = parse(value)
                break
    return fields


def validate_teki_markers(log_text):
    """Parse the teki marker stream into per-marker flip flags.

    Returns ``{"gates": {...bool...}, "blasts": int, "pikmin_hits": int,
    "throw_kind": str|None, "probes": [...], "min_y": float|None,
    "max_nearest": float|None, "engaged": bool}``. Empty log -> all-false.
    Unknown/malformed lines are ignored; a recognized marker with a missing
    generator value degrades silently (its gate stays False) rather than
    raising. Per-probe numeric fields that are missing or malformed parse to
    ``None`` without raising; ``min_y``/``max_nearest`` ignore those ``None``
    values. ``engaged`` is True iff at least one probe has ``squad >= 1`` and
    ``nearest <= 60.0``.
    """
    gates = dict(_PASS_GATE_DEFAULTS)
    blasts = 0
    pikmin_hits = 0
    throw_kind = None
    probes = []
    if not log_text:
        return {"gates": gates, "blasts": 0, "pikmin_hits": 0,
                "throw_kind": None, "probes": [], "min_y": None,
                "max_nearest": None, "engaged": False}
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
        elif marker in ("P2_POD_RECEIPT", "[Pikipelago]") and "bombsarai" in stripped:
            gates["corpse"] = True
    ys = [p["y"] for p in probes if p["y"] is not None]
    nearests = [p["nearest"] for p in probes if p["nearest"] is not None]
    engaged = any(p["squad"] is not None and p["squad"] >= 1
                  and p["nearest"] is not None
                  and p["nearest"] <= _ENGAGED_NEAREST for p in probes)
    return {"gates": gates, "blasts": blasts, "pikmin_hits": pikmin_hits,
            "throw_kind": throw_kind, "probes": probes,
            "min_y": min(ys) if ys else None,
            "max_nearest": max(nearests) if nearests else None,
            "engaged": engaged}
