"""Lane 03 (#439) post-load resolve validator (pure Python).

The native bridge emits ``P2_SEED_RESOLVE source_id=<n> target=<uid> ...`` at
ordinary ``GenObjectTeki::birth`` whenever a generator's spawn-slot uid is bound
by the ``ENEMY_P2`` seed, and the Snow / Dwarf Orange family adapters emit a
matching ``P2_ENEMY_READY`` once they own the live actor. This module is the
root-side validator that turns a captured runtime log into a gate-1 result:

* it passes only when at least one real uid resolves to the Snow (45) /
  Dwarf Orange (44) cohort, and
* it flips to a failure the moment the ``P2_SEED_RESOLVE`` marker is stripped
  from an otherwise identical log (or any source outside the cohort appears).

It has no dependency on the native engine and no paths anywhere; callers feed it
log text (from a captured probe / fixture run, or a stored sample).
"""
from __future__ import annotations

import re

SNOW_SOURCE = 45
ORANGE_SOURCE = 44
COHORT = {SNOW_SOURCE, ORANGE_SOURCE}

_RESOLVE = re.compile(r"P2_SEED_RESOLVE\b.*?\bsource_id=(\d+)\s+target=(\d+)")
_READY = re.compile(r"P2_ENEMY_READY\b.*?\bsource_id=(\d+)")


class Validation:
    """Result of :func:`validate_log`."""

    def __init__(self, ok: bool, reason: str, targets: tuple[int, ...], sources: set[int]):
        self.ok = ok
        self.reason = reason
        self.targets = targets
        self.sources = sources

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:
        return f"Validation(ok={self.ok!r}, reason={self.reason!r})"


def parse_resolves(text: str) -> list[tuple[int, int]]:
    """Return ``(target_uid, source_id)`` pairs for every ``P2_SEED_RESOLVE`` line."""
    pairs = []
    for line in text.splitlines():
        match = _RESOLVE.search(line)
        if match:
            pairs.append((int(match.group(2)), int(match.group(1))))
    return pairs


def parse_ready(text: str) -> list[int]:
    """Return the source ids every ``P2_ENEMY_READY`` line claims to have bound."""
    return [int(match.group(1)) for line in text.splitlines() if (match := _READY.search(line))]


def validate_log(text: str, *, require_ready: bool = False) -> Validation:
    """Validate a boot/round-trip log for gate-1 seed resolution.

    Passes only when the log carries at least one ``P2_SEED_RESOLVE`` that maps a
    positive real uid to the Snow (45) / Dwarf Orange (44) cohort. Absent markers
    (the stripped case) and any non-cohort source flip the result to a failure.
    When ``require_ready`` is set, the family adapter must also have logged a
    matching ``P2_ENEMY_READY`` for every resolved source.
    """
    resolves = parse_resolves(text)
    if not resolves:
        return Validation(False, "no P2_SEED_RESOLVE marker in log", (), set())
    targets, source_ids = zip(*resolves)
    targets = tuple(targets)
    sources = set(source_ids)
    non_cohort = sorted(sources - COHORT)
    if non_cohort:
        return Validation(False, f"non-cohort source ids resolved: {non_cohort}", targets, sources)
    if any(target <= 0 for target in targets):
        return Validation(False, "resolved a non-positive target uid", targets, sources)
    if require_ready:
        ready = set(parse_ready(text))
        unbound = sorted(sources - ready)
        if unbound:
            return Validation(False, f"resolved sources without a family READY line: {unbound}", targets, sources)
    return Validation(True, f"{len(resolves)} resolve(s) on cohort sources {sorted(sources)}", targets, sources)
