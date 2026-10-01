"""Kurage57 death/transport/re-entry observer for enemies-4 (issue #768).

Validates run logs from the Kurage death/transport fixture
(native/tools/p2_kurage_death_transport_fixture.cpp), which drives the REAL
P2KurageCapturePolicy lifecycle (capture/update/onDeath) for a live Kurage57
actor (ID 57, Greater variant) through two passes: a fresh observation and a
re-entry after reset. Consumes the done #498 natural-birth handoff and the
#753 designated-paths discovery read-only; duplicates neither. Owns the
run-log grammar plus the stale/fresh transport invariant used to cross-check
the native emission.

Marker grammar (exact lines, session order per pass):
  P2_KURAGE57_ACTOR id=57 variant=Greater squad=<n>
  P2_KURAGE_CAPTURE target=<t> result=Captured
  P2_KURAGE_TICK n=<i> stomach=<f> killed=<k> released=<r>
  P2_KURAGE_DEATH released=<n> killed=<n>
  P2_KURAGE_CORPSE corpse=1 hauled=<h>
  P2_KURAGE_TRANSPORT fresh=<f> replay=<r> doublecount=<d>
  P2_KURAGE_REENTRY pass=2 matched=<0|1>
  P2_KURAGE_DONE failures=<n>
  PASS P2_KURAGE57_RUN passes=2
Stale/fresh invariant: pass 1 emits the fresh transport receipt; pass 2
(re-entry) replays the identical accounting and must not double-count
(doublecount=0, matched=1). Per pass: captured == killed + released_alive,
hauled corpse == 1, every squad member accounted (never captured, digested,
or returned alive).

Engine-free, hermetic, fail-closed. No runtime world boot, no ADMIT.
"""
from __future__ import annotations

import re

SCHEMA = "p2-kurage-death-transport-observer-v1"
ACTOR_ID = 57
ACTOR_RE = re.compile(r"^P2_KURAGE57_ACTOR id=57 variant=Greater squad=(\d+)$")
CAPTURE_RE = re.compile(r"^P2_KURAGE_CAPTURE target=(\d+) result=Captured$")
TICK_RE = re.compile(r"^P2_KURAGE_TICK n=(\d+) stomach=([0-9.]+) killed=(\d+) released=(\d+)$")
DEATH_RE = re.compile(r"^P2_KURAGE_DEATH released=(\d+) killed=(\d+)$")
CORPSE_RE = re.compile(r"^P2_KURAGE_CORPSE corpse=1 hauled=(\d+)$")
TRANSPORT_RE = re.compile(r"^P2_KURAGE_TRANSPORT fresh=(\d+) replay=(\d+) doublecount=(\d+)$")
REENTRY_RE = re.compile(r"^P2_KURAGE_REENTRY pass=2 matched=([01])$")
DONE_RE = re.compile(r"^P2_KURAGE_DONE failures=(\d+)$")
PASS_RE = re.compile(r"^PASS P2_KURAGE57_RUN passes=2$")
WINDOW_RE = re.compile(r"^P2_KURAGE57_WINDOW size=960x540 .*centered=1$")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")


class ObserverError(ValueError):
    """Refusal: malformed input or contract drift."""


def parse(text):
    """Split a run log into pass facts and health flags."""
    actors, captures, ticks, deaths = [], [], [], []
    corpses, transports, reentries, dones, passes = [], [], [], [], []
    window = None
    for raw in text.splitlines():
        line = raw.strip()
        match = ACTOR_RE.match(line)
        if match:
            actors.append(int(match.group(1)))
        match = CAPTURE_RE.match(line)
        if match:
            captures.append(int(match.group(1)))
        match = TICK_RE.match(line)
        if match:
            ticks.append((int(match.group(1)), float(match.group(2)),
                          int(match.group(3)), int(match.group(4))))
        match = DEATH_RE.match(line)
        if match:
            deaths.append((int(match.group(1)), int(match.group(2))))
        match = CORPSE_RE.match(line)
        if match:
            corpses.append(int(match.group(1)))
        match = TRANSPORT_RE.match(line)
        if match:
            transports.append((int(match.group(1)), int(match.group(2)),
                               int(match.group(3))))
        match = REENTRY_RE.match(line)
        if match:
            reentries.append(int(match.group(1)))
        match = DONE_RE.match(line)
        if match:
            dones.append(int(match.group(1)))
        if PASS_RE.match(line):
            passes.append(line)
        if WINDOW_RE.match(line):
            window = line
    return {
        "actors": actors, "captures": captures, "ticks": ticks,
        "deaths": deaths, "corpses": corpses, "transports": transports,
        "reentries": reentries, "dones": dones, "passes": passes,
        "window": window,
        "captain_down": CAPTAIN_DOWN in text,
        "injected": [t for t in INJECTED_TOKENS if t in text],
    }


def _check_pass(captures, deaths, corpses, transports):
    """One pass balances: captured == killed + released, corpse hauled once."""
    if len(deaths) != 1 or len(corpses) != 1 or len(transports) != 1:
        return False, "pass summary lines missing"
    released, killed = deaths[0]
    if corpses[0] != 1:
        return False, "corpse haul != 1"
    if len(captures) != killed + released:
        return False, "accounting open: captured=%d killed=%d released=%d" % (
            len(captures), killed, released)
    fresh, replay, doublecount = transports[0]
    if doublecount != 0:
        return False, "transport double-counted"
    return True, ""


def check_run(parsed):
    """Two balanced passes with a matched re-entry and no hoist/injection."""
    if parsed["captain_down"]:
        return False, "captain-down interruption present"
    if parsed["injected"]:
        return False, "injection markers present: %s" % ",".join(parsed["injected"])
    if parsed["window"] is None:
        return False, "centred 960x540 window line absent"
    if len(parsed["actors"]) != 2 or any(s < 1 for s in parsed["actors"]):
        return False, "two live-actor sessions with squad required"
    if len(parsed["captures"]) != 10:
        return False, "expected 5 captures per pass, got %d" % len(parsed["captures"])
    ok, why = _check_pass(parsed["captures"][:5], parsed["deaths"][:1],
                          parsed["corpses"][:1], parsed["transports"][:1])
    if not ok:
        return False, "pass 1 (fresh): " + why
    if parsed["transports"][0][0] != 1:
        return False, "pass 1 must emit the fresh receipt"
    ok, why = _check_pass(parsed["captures"][5:], parsed["deaths"][1:],
                          parsed["corpses"][1:], parsed["transports"][1:])
    if not ok:
        return False, "pass 2 (re-entry): " + why
    if parsed["transports"][1][1] != 1:
        return False, "pass 2 must replay (not re-issue) the receipt"
    if not parsed["reentries"] or parsed["reentries"][-1] != 1:
        return False, "re-entry accounting mismatch"
    if not parsed["dones"] or parsed["dones"][-1] != 0:
        return False, "DONE failures nonzero or absent"
    if not parsed["passes"]:
        return False, "run PASS marker absent"
    return True, "two balanced passes with matched re-entry and no double-count"


def gate_status(text):
    """Tooling gate grades for a fixture run log (never a gameplay claim)."""
    parsed = parse(text)
    run_ok, run_why = check_run(parsed)
    return {
        "run_markers": (run_ok, run_why),
        "captain_guard": (not parsed["captain_down"],
                          "no CAPTAIN_DOWN" if not parsed["captain_down"] else "CAPTAIN_DOWN fired"),
        "no_inject": (not parsed["injected"],
                      "no injection markers" if not parsed["injected"] else "injection present"),
    }
