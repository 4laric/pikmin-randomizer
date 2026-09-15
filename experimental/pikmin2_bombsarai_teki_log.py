"""Root-side marker validator for the lane-27 BombSarai teki carrier binding.

Parses the ``P2_BOMBSARAI_TEKI_*`` marker stream emitted by
``pc_port/pc_p2_bombsarai_teki.cpp`` plus the Pod corpse receipt into a set of
per-marker flip flags used to gate the slice-4 acceptance. Dependency-free.
"""

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


def validate_teki_markers(log_text):
    """Parse the teki marker stream into per-marker flip flags.

    Returns ``{"gates": {...bool...}, "blasts": int, "pikmin_hits": int,
    "throw_kind": str|None}``. Empty log -> all-false. Unknown/malformed lines
    are ignored; a recognized marker with a missing generator value degrades
    silently (its gate stays False) rather than raising.
    """
    gates = dict(_PASS_GATE_DEFAULTS)
    blasts = 0
    pikmin_hits = 0
    throw_kind = None
    if not log_text:
        return {"gates": gates, "blasts": 0, "pikmin_hits": 0, "throw_kind": None}
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
        elif marker in ("P2_POD_RECEIPT", "[Pikipelago]") and "bombsarai" in stripped:
            gates["corpse"] = True
    return {"gates": gates, "blasts": blasts, "pikmin_hits": pikmin_hits,
            "throw_kind": throw_kind}
