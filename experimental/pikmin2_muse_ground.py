"""Muse ground lane observer for Sokkuri79 (and ElecBug28 later) delivery (#495).

Validates the ordinary corpse-hauling chain without injecting state:

- source 79 bound at setup (P2_SOKKURI_BIND + P2_SOKKURI_DELIVERY_BIND),
- natural combat damage (P2_SOKKURI_DAMAGE) and combat-culminated death
  (P2_SOKKURI_DEAD with small prior_health),
- host corpse pellet handoff,
- ordinary Onion receipt (P2_ORDINARY_P2_RECEIPT id=onion:p2:79:...) exactly once,
- natural carry proof required before transport PASS is claimed.

Honesty contract (lane14 corrections, #495 scope):
- generator recreation (mGenType->init) / fixture forget is NOT full natural
  scene re-entry; cleanup_reentry stays UNTESTED.
- injected Transport/kill/credit, direct suckMe fallback without carry, forced
  re-bind, or synthetic markers can never close a natural gate.
- transport_reward PASS requires BOTH an ordinary receipt new=1 AND explicit
  natural-carry markers in the same run. A receipt alone (interface-level) is
  reported as interface evidence, gate stays UNTESTED.
"""

import re

SOKKURI_GEN = 346005
SOKKURI_SOURCE_ID = 79
ELECBUG_SOURCE_ID = 28
LIFE = 120.0
PRIOR_HEALTH_MAX = LIFE * 0.5

BIND = re.compile(r"P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0")
DELIVERY_BIND = re.compile(r"P2_SOKKURI_DELIVERY_BIND generator=346005 source_id=79")
DAMAGE = re.compile(
    r"P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=([\d.]+)"
)
DEAD = re.compile(
    r"P2_SOKKURI_DEAD generator=346005 source_id=79 health=0 prior_health=([\d.]+)"
)
CORPSE = re.compile(r"P2_SOKKURI_NATURAL_CORPSE pellet=1")
CORPSE_ALT = re.compile(
    r"P2_LIFECYCLE_CORPSE species=Sokkuri pellet=1 generator=346005"
)
CORPSE_MUSE = re.compile(r"P2_MUSE_GROUND_CORPSE pellet=1 tick=(\d+)")
READY_MUSE = re.compile(
    r"P2_MUSE_GROUND_READY squad=(\d+) sokkuri_gen=346005 source=79"
)
RECEIPT = re.compile(
    r"P2_ORDINARY_P2_RECEIPT seed=(\S+) id=onion:p2:79:(\d+) generator=346005 new=([01])"
)
# Natural carry proof markers (future fixture): grasp + haul + Onion endpoint
# reached by carriers. Absent today; transport stays UNTESTED without them.
CARRY_GRASP = re.compile(r"P2_SOKKURI_CARRY_GRASP generator=346005 carriers=\d+")
CARRY_HAUL = re.compile(r"P2_SOKKURI_CARRY_HAUL generator=346005 .*onion=1")
# Muse-ground fixture carry observation: the fixture tracks the corpse pellet
# position each 60 ticks and logs displacement from the death site. A
# natural=1 row means free Pikmin moved the corpse with no Transport injection
# and no suckMe fallback (the fixture has neither code path). This is observed
# haul movement, not an Onion receipt: the cargo-free arena has no Onion, so
# the haul stalls once carriers run out of route. Honest label: carry movement
# observed; reward receipt still open.
CARRY_OBSERVE = re.compile(
    r"P2_MUSE_GROUND_CARRY tick=(\d+) moved=([\d.]+) natural=([01])"
)
INJECTED_MARKERS = (
    "P2_LIFECYCLE_INJECT",
    "not_natural_combat=1",
    "injected_health",
    "mHealth=0.0f",
    "natural_carry=0",
)
WINDOW = re.compile(
    r"Experimental preview window set to 960x540 windowed and centered"
)


def _has_injected(text):
    return any(m in text for m in INJECTED_MARKERS)


def parse_receipts(text):
    """Return list of (seed, stage, new) for source-79 ordinary receipts."""
    return [
        (m.group(1), int(m.group(2)), int(m.group(3)))
        for m in RECEIPT.finditer(text)
    ]


def parse_carry_observations(text):
    """Return list of (tick, moved, natural) corpse-displacement observations."""
    return [
        (int(m.group(1)), float(m.group(2)), int(m.group(3)))
        for m in CARRY_OBSERVE.finditer(text)
    ]


def validate(text, code=0):
    """Validate a native log string. Never claims natural PASS from injection."""
    if not isinstance(text, str):
        raise ValueError("Expected a native log string")
    damages = [float(v) for v in DAMAGE.findall(text)]
    dead = DEAD.search(text)
    prior = float(dead.group(1)) if dead else None
    receipts = parse_receipts(text)
    granted = [r for r in receipts if r[2] == 1]
    # Exactly-once at interface level: at most one Granted per (id, generator).
    # Duplicate deliveries must log new=0.
    new_ones = len(granted)
    interface_once = new_ones <= 1
    carry = bool(CARRY_GRASP.search(text) and CARRY_HAUL.search(text))
    observations = parse_carry_observations(text)
    natural_rows = [row for row in observations if row[2] == 1]
    max_haul = max((row[1] for row in natural_rows), default=0.0)
    haul_observed = max_haul > 40.0
    ready = READY_MUSE.search(text)
    injected = _has_injected(text)
    checks = dict(
        identity=bool(BIND.search(text) and DELIVERY_BIND.search(text)),
        window=bool(WINDOW.search(text)),
        live_squad=int(ready.group(1)) >= 1 if ready else False,
        natural_damage=bool(damages),
        natural_death=dead is not None,
        small_prior_health=prior is not None and prior < PRIOR_HEALTH_MAX,
        no_inject=not injected,
        corpse=bool(
            CORPSE.search(text) or CORPSE_ALT.search(text) or CORPSE_MUSE.search(text)
        ),
        ordinary_receipt=bool(granted),
        interface_exactly_once=interface_once and bool(granted),
        natural_carry=carry,
        natural_haul_observed=haul_observed,
    )
    # Gate verdicts (honest): transport needs receipt + carry + no inject.
    # Observed haul movement without a receipt is recorded as carry evidence,
    # never as a transport PASS.
    if checks["ordinary_receipt"] and carry and not injected:
        transport = ("pass", "receipt new=1 plus natural carry markers")
    elif checks["ordinary_receipt"] and not carry:
        transport = (
            "untested",
            "receipt without natural-carry proof is interface-only, not natural transport",
        )
    elif haul_observed and not injected:
        transport = (
            "untested",
            "natural haul movement observed (max %.1f units) but no ordinary "
            "onion:p2:79 receipt in log" % max_haul,
        )
    else:
        transport = ("untested", "no ordinary onion:p2:79 receipt in log")
    detail = dict(
        passed=code == 0,
        checks=checks,
        damage_hits=len(damages),
        prior_health=prior,
        receipts=receipts,
        carry_observations=len(observations),
        max_natural_haul=max_haul,
        transport_gate=transport[0],
        transport_reason=transport[1],
        exit_code=code,
    )
    return detail


def gate_summary(result):
    """One-line honest summary for logs/status files."""
    c = result["checks"]
    return (
        "identity=%d damage=%d death=%d corpse=%d receipt=%d carry=%d haul=%.1f transport=%s"
        % (
            c["identity"],
            c["natural_damage"],
            c["natural_death"],
            c["corpse"],
            c["ordinary_receipt"],
            c["natural_carry"],
            result["max_natural_haul"],
            result["transport_gate"],
        )
    )
