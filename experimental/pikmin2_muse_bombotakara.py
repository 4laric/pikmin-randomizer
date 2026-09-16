"""Muse l61 BombOtakara93 natural observer (#501, parent #447).

Validates a captured native log for the two remaining BombOtakara93 gates
without staging, injecting, or launching anything:

* identity_spawn: a real family generator identity chain --
  ``P2_OTAKARA_BIND generator=<n> source_id=93`` plus
  ``P2_ENEMY_READY species=BombOtakara ... attack=payload_delegated``,
  and an observed ``otakara``-joint attachment
  (``P2_BOMBOTAKARA_ATTACH ... joint=otakara natural=1``).
* attacks_receivers: an observed blast routed through the shared lane-20
  primitive to live receivers (``P2_BOMBOTAKARA_BLAST ... shared_primitive=1``
  with receivers>=1, hits>=1, pikmin_hits>=1) plus a real InteractBomb
  delivery (``P2_BOMBOTAKARA_BOMB_HIT ... interaction=InteractBomb``).

Any log line carrying an injection marker (``P2_BOMBOTAKARA_INJECT``,
``p2-bombotakara-inject``, ``injection=1``, fixture guard Pikmin,
``*_DEATH_INJECT``) is reported as injected diagnostic evidence and fails
the natural checks. The sidecar ``p2-bombotakara-native.txt`` profile and
the ``P2_OTAKARA_DISCHARGE_NONE payload_delegated=1`` line are context only:
they prove the lane-22 delegation boundary, not a natural PASS.

No GL, assets, saves, or runtime are touched. The coordinator owns launches;
this module only classifies logs.
"""
from __future__ import annotations

import re

INJECTED_MARKERS = (
    "P2_BOMBOTAKARA_INJECT",
    "p2-bombotakara-inject",
    "injection=1",
    "P2_BOMBOTAKARA_FIXTURE_GUARD_PIKMIN",
    "P2_BOMBOTAKARA_DEATH_INJECT",
    "P2_OTAKARA_DEATH_INJECT",
)

BIND_RE = re.compile(r"P2_OTAKARA_BIND generator=(\d+) source_id=93\b")
READY_RE = re.compile(r"P2_ENEMY_READY species=BombOtakara\b.*attack=payload_delegated")
ATTACH_RE = re.compile(
    r"P2_BOMBOTAKARA_ATTACH generator=(\d+) payload=(\d+) joint=otakara natural=1")
BLAST_RE = re.compile(
    r"P2_BOMBOTAKARA_BLAST generator=(\d+) payload=(\d+) .*receivers=(\d+) "
    r"hits=(\d+) pikmin_hits=(\d+).*shared_primitive=1")
BOMB_HIT_RE = re.compile(
    r"P2_BOMBOTAKARA_BOMB_HIT generator=(\d+) payload=(\d+) .*accepted=1 "
    r".*interaction=InteractBomb")
DISCHARGE_NONE_RE = re.compile(
    r"P2_OTAKARA_DISCHARGE_NONE generator=(\d+) source_id=93 payload_delegated=1")


def validate(text: str, code: int = 0) -> dict:
    """Classify one captured log. Pure; never launches or stages."""
    lines = text.splitlines()
    injected = any(marker in line for line in lines for marker in INJECTED_MARKERS)

    bind = None
    for line in lines:
        match = BIND_RE.search(line)
        if match and int(match.group(1)) != 0:
            bind = match.group(0)
            break
    ready = any(READY_RE.search(line) for line in lines)
    attach_match = None
    for line in lines:
        match = ATTACH_RE.search(line)
        if match:
            attach_match = match
            break
    blast_match = None
    for line in lines:
        match = BLAST_RE.search(line)
        if match:
            receivers, hits, pikmin = (int(match.group(3)), int(match.group(4)),
                                       int(match.group(5)))
            if receivers >= 1 and hits >= 1 and pikmin >= 1:
                blast_match = match
                break
    bomb_hit = any(BOMB_HIT_RE.search(line) for line in lines)
    discharge_none = any(DISCHARGE_NONE_RE.search(line) for line in lines)

    natural = code == 0 and not injected
    checks = {
        "completion": code == 0,
        "no_injection": not injected,
        "identity_bind": bind is not None,
        "ready_delegated": ready,
        "attach": attach_match is not None,
        "blast_routed": blast_match is not None,
        "bomb_hit": bomb_hit,
        "discharge_none_context": discharge_none,
        "identity_spawn": natural and bind is not None and ready and attach_match is not None,
        "attacks_receivers": natural and blast_match is not None and bomb_hit,
    }
    gates = {
        "identity_spawn": "pass_natural" if checks["identity_spawn"] else "blocked",
        "attacks_receivers": "pass_natural" if checks["attacks_receivers"] else "blocked",
    }
    passed = checks["identity_spawn"] and checks["attacks_receivers"]
    return {
        "passed": passed,
        "failed": sorted(name for name, ok in checks.items() if not ok),
        "checks": checks,
        "gates": gates,
        "injected": injected,
        "exit_code": code,
        "scope": ("BombOtakara93 natural attach/blast observer; sidecar profile + "
                  "inject triggers are labeled injections and never count as natural"),
    }
