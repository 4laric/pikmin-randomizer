"""White Pikmin species-identity/fidelity + ship-storage pin audit (#820).

Downstream consumer: p2-challenge-ch-mat-crawler-p1 (#562, #131 gap).
Read-only: inspects the canonical port + research trees, never edits.
Fail-closed: missing/malformed inputs raise PinError; verdicts cite exact
file:line evidence or record ABSENT with reason. Nothing invented.

Recorded finding (2026-09-18): species identity/fidelity PRESENT (pc_port
species layer + flag carriers + birth/pluck/sprout propagation + enemy
callbacks + UI counters); ship/storage persistence for White/Purple ABSENT
(memoryCard persists Red/Yellow/Blue only; pikiMgr has no species handling).
"""
import json
import re
import sys
from pathlib import Path


class PinError(Exception):
    """Fail-closed refusal."""


def repo_root_from_here() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent,) + tuple(here.parents):
        if (parent / "docs" / "PIKMIN2_CONTENT_INVENTORY.json").exists():
            return parent
    raise PinError("cannot locate repo root from %s" % here)


def load_text(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PinError("missing input refused: %s (%s)" % (path, exc))
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PinError("malformed input refused (not utf-8): %s (%s)" % (path, exc))


def find_lines(text: str, pattern: str):
    return [(i + 1, l.strip()[:160]) for i, l in enumerate(text.splitlines())
            if re.search(pattern, l)]


def cite(path: Path, lineno: int) -> str:
    return "%s:%d" % (path.name, lineno)


MUST_HAVE = [
    ("native/pc_port/pc_p2_species.cpp", r"mP2White", "species get/set incl White"),
    ("native/include/Piki.h", r"bool mP2White", "Piki White flag carrier"),
    ("native/include/PikiHeadItem.h", r"bool mP2White", "sprout White flag carrier"),
    ("native/pikmin2-research/include/Game/EnemyBase.h", r"eatWhitePikminCallBack",
     "enemy White-eaten callback"),
    ("native/pikmin2-research/include/og/Screen/MapCounter.h", r"mShipWhitePikmin",
     "ship/leader White UI counters"),
]

PROPAGATION = [
    ("native/src/plugPikiKando/piki.cpp", r"mP2White\s*="),
    ("native/src/plugPikiKando/pikiheadItem.cpp", r"mP2White"),
    ("native/src/plugPikiKando/navi.cpp", r"mP2White"),
    ("native/src/plugPikiKando/naviState.cpp", r"mP2White"),
    ("native/src/plugPikiKando/pikiState.cpp", r"mP2White\s*="),
    ("native/pc_port/pc_whistle_pluck.cpp", r"mP2White"),
]

ABSENT_CHECKS = [
    ("native/src/plugPikiColin/memoryCard.cpp",
     r"White|Purple|mWhitePikiCount|mPurplePikiCount",
     "ship/storage persistence covers White/Purple"),
    ("native/src/plugPikiKando/pikiMgr.cpp",
     r"mP2White|mP2Purple|species|Species|White|Purple",
     "pikiMgr species handling"),
]


def audit(root: Path) -> dict:
    found, absent = [], []
    for rel, pattern, label in MUST_HAVE:
        text = load_text(root / rel)
        hits = find_lines(text, pattern)
        if not hits:
            raise PinError("unclassifiable: expected %s in %s but found none" % (label, rel))
        found.append({"file": rel, "label": label,
                      "citations": [cite(root / rel, n) for n, _ in hits[:4]],
                      "count": len(hits)})
    for rel, pattern in PROPAGATION:
        text = load_text(root / rel)
        hits = find_lines(text, pattern)
        if not hits:
            raise PinError("unclassifiable: expected propagation in %s but found none" % rel)
        found.append({"file": rel, "label": "birth/pluck/sprout propagation",
                      "citations": [cite(root / rel, n) for n, _ in hits[:4]],
                      "count": len(hits)})
    for rel, pattern, label in ABSENT_CHECKS:
        text = load_text(root / rel)
        hits = find_lines(text, pattern)
        if hits:
            raise PinError("unexpected: %s present in %s (audit assumption broken)" % (label, rel))
        total = len(text.splitlines())
        absent.append({"file": rel, "label": label,
                       "verdict": "ABSENT",
                       "reason": "zero matches in %d lines" % total,
                       "checked_through_line": total})
    return {
        "subject": "White Pikmin species identity/fidelity + ship storage",
        "verdict": "FOUND_PARTIAL",
        "found": found,
        "absent": absent,
        "ownership": {
            "species_layer": "pc_port family modules (existing owners; read-only here)",
            "ship_storage_gap": "save-progression/engine owner (memoryCard three-color persistence)",
        },
        "downstream": {"issue": 562, "lane": "p2-challenge-ch-mat-crawler-p1",
                       "check": ("guarded staged crawler boot "
                                 "content-loading-verify/fixture.exe --experimental-pikmin2-room; "
                                 "expected SELECTED/SPAWN_COVERED/READY/LIVE/PASS markers")},
    }


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("REFUSED: usage: pin_audit [repo-root]")
        return 2
    try:
        root = Path(args[0]) if args else repo_root_from_here()
        packet = audit(root)
    except PinError as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(packet, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

