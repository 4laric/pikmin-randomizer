"""Parallel Kurage57 observer-path designation preserving #498 ownership (#753).

The natural observer paths (`experimental/pikmin2_muse_kurage.py`,
`tests/test_pikmin2_muse_kurage.py`, `docs/PIKMIN2_MUSE_KURAGE_HANDOFF.md`,
`native/tools/p2_muse_kurage_fixture.cpp`) are owned by the done `muse-kurage`
lane (#498, gen 5): gate 1 (identity_spawn) closed there, files unlanded but
ownership-retained. Reusing them duplicates done scope; inventing parallel
family paths fragments group ownership.

This module designates parallel observer file paths with zero overlap against
#498, pins the exact consumer files/lines for a future Kurage57
death/transport/re-entry observer (precedent shape + Kurage57 gates), and
produces a compatibility verdict plus a concrete observer scope with
acceptance. Fail-closed on any ambiguous ownership. Read-only: no family,
shared, native, runtime, or ADMIT effects. All six gates UNTESTED here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ISSUE = 753
OWNER_ISSUE = 498
OWNER_LANE = "muse-kurage"
SOURCE_ID = 57
DOWNSTREAM = "enemies-4 / Kurage57 death/transport/re-entry observer"

# Owned by done #498 (read-only reference; never touched, never duplicated).
OWNER_PATHS = (
    "experimental/pikmin2_muse_kurage.py",
    "tests/test_pikmin2_muse_kurage.py",
    "docs/PIKMIN2_MUSE_KURAGE_HANDOFF.md",
    "native/tools/p2_muse_kurage_fixture.cpp",
)

# Precedent observer shape (armor15/mar29 published items, read-only reference).
PRECEDENT_SHAPE = (
    "experimental/pikmin2_muse_<family>.py",
    "tests/test_pikmin2_muse_<family>.py",
    "docs/PIKMIN2_MUSE_<FAMILY>_HANDOFF.md",
    "native/tools/p2_muse_<family>_fixture.cpp",
)

# Designated parallel paths: same precedent shape with the Kurage57-specific
# stem, verified free of manifest owners, claims, and existing files.
DESIGNATED_PATHS = (
    "experimental/pikmin2_kurage57_observer.py",
    "tests/test_pikmin2_kurage57_observer.py",
    "docs/PIKMIN2_KURAGE57_OBSERVER.md",
    "native/tools/p2_kurage57_observer_fixture.cpp",
)

# Consumer pins for the future observer (precedent roles + Kurage57 gates).
CONSUMER_PINS = (
    {"file": "experimental/pikmin2_muse_kurage.py",
     "role": "group-ownership reference (gate-1 identity binding, read-only)"},
    {"file": "experimental/pikmin2_muse_armor.py",
     "role": "precedent observer shape (published armor15 item, read-only)"},
    {"file": "docs/PIKMIN2_MUSE_KURAGE_HANDOFF.md",
     "role": "gate-1 evidence baseline to preserve unchanged (read-only)"},
)


class AmbiguousOwnershipError(ValueError):
    """A designated path collides; fail closed instead of fragmenting ownership."""


def check_disjoint(designated=DESIGNATED_PATHS, owned=OWNER_PATHS):
    """Prove zero overlap between designated and #498-owned paths."""
    if not designated:
        raise AmbiguousOwnershipError("no designated paths to check")
    overlap = sorted(set(designated) & set(owned))
    if overlap:
        raise AmbiguousOwnershipError("designated paths overlap #498: %s" % overlap)
    seen = set()
    for path in designated:
        if not isinstance(path, str) or not path:
            raise AmbiguousOwnershipError("designated path must be a non-empty string")
        if path in seen:
            raise AmbiguousOwnershipError("duplicate designated path: %s" % path)
        seen.add(path)
    return True


def compatibility_verdict(taken=()):
    """Verdict: compatible designation, or fail closed on any collision."""
    taken = set(taken)
    collisions = sorted(set(DESIGNATED_PATHS) & taken)
    if collisions:
        raise AmbiguousOwnershipError(
            "designated paths already taken: %s" % collisions)
    check_disjoint()
    return {
        "compatible": True,
        "owner_issue": OWNER_ISSUE,
        "owner_lane": OWNER_LANE,
        "source_id": SOURCE_ID,
        "designated_paths": list(DESIGNATED_PATHS),
        "consumer_pins": [dict(row) for row in CONSUMER_PINS],
        "downstream": DOWNSTREAM,
    }


def observer_scope():
    """Concrete observer scope with acceptance for the future lane."""
    compatibility_verdict()
    return {
        "lane": "kurage57-observer",
        "issue": "new, assigned 4laric (downstream of #753)",
        "scope": "Kurage57 death/transport/re-entry observer on the designated paths; "
                 "gate 1 taken as-is from #498, never re-closed.",
        "owned_files": list(DESIGNATED_PATHS),
        "acceptance": [
            "Natural Kurage57 death observed with corpse/disappearance evidence; "
            "no injected state, no captain-down taint",
            "Transport/reward and cleanup/re-entry observed with stale/fresh proof; "
            "gate-1 identity rows preserved byte-identical from #498",
            "Honest six-gate handoff; focused tests green; no ADMIT",
        ],
        "gates": "all six UNTESTED by this designation",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        payload = json.dumps({"verdict": compatibility_verdict(),
                              "observer_scope": observer_scope()},
                             indent=2, sort_keys=True) + "\n"
    except AmbiguousOwnershipError as exc:
        print("OWNERSHIP_AMBIGUOUS %s" % exc)
        return 4
    if args.out is None:
        print(payload, end="")
    else:
        args.out.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())