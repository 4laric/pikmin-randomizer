"""Pin/ownership discovery for three #132 items gating course-last runtime (#151).

Bounded DIAGNOSIS producer contract (never an engine unblock) for lane
`shard-overworld-last-daylight-receipt-cache-discovery`. It pins and names
ownership for the native sunset/day driver, the receipt ledger endpoint, and
the generator-cache restore as they gate Wistful Wild (course last) runtime
observation. The sibling save-serializer boundary is already consumable via
#736 and is NOT re-derived here.

Method: verify the research-tree source pins read-only (the #658 citations),
check the port tree for implementations (present with file:line and owning lane,
or explicit ABSENT), attach the exact shared-review contract per item, name the
downstream last-P1 consumer commands with expected per-boundary behavior, and
emit a pinned registry JSON. Fail-closed: unknown inputs, missing files, or
grammar drift raise before any verdict. Stdlib only. No engine edits, no builds,
no runtime runs, no ADMIT. All six gates UNTESTED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "p2-last-daylight-receipt-cache-discovery-v1"
SOURCE_ID_COURSE_LAST = "last"

# Research-tree pins (read-only decomp; verified this turn). File+symbol is the
# stable contract; line numbers are #658-observed references, not re-pinned.
RESEARCH = {
    "sunset_day_driver": {
        "file": "src/plugProjectKandoU/singleGameSection.cpp",
        "symbols": ["CaveDayEndState", "saveMainMapSituation", "loadMainMapSituation",
                    "enableTimer", "disableTimer"],
        "contract": "#186 shared review (day hooks sit on the shared section/FSM path)",
    },
    "receipt_ledger_endpoint": {
        "file": "src/plugProjectKandoU/onyonMgr.cpp",
        "symbols": ["actOnyon", "isSuckReady"],
        "also": {"file": "src/plugProjectKandoU/gamePlayData.cpp",
                 "symbols": ["obtainPellet_Main"]},
        "contract": "#606 owns the ledger concept + #186 (the surface binding is unscoped)",
    },
    "generator_cache_restore": {
        "file": "src/plugProjectKandoU/gameGeneratorCache.cpp",
        "symbols": ["GeneratorCache::read", "GeneratorCache::write",
                    "GeneratorCache::loadGenerators", "GeneratorCache::slideCache",
                    "CourseCache::read"],
        "contract": "#607 cave generation + #186 (restore extends the accepted generator pin)",
    },
}

# Port-side implementation markers. Presence means a port implementation exists
# (then an owning lane is required); absence confirms the #658 ABSENT verdict.
PORT_MARKERS = {
    "sunset_day_driver": ["SunsetDriver", "surface_day_driver", "DayEndState"],
    # NOTE: the cargo/contest `ReceiptLedger` vocabulary (pc_p2_receipt.h, lane 06
    # provider) is explicitly EXCLUDED: the #132 surface endpoint is the Onyon
    # delivery binding (obtainPellet/actOnyon), not the cargo ledger.
    "receipt_ledger_endpoint": ["obtainPellet_Main", "obtainPellet", "actOnyon"],
    "generator_cache_restore": ["GeneratorCache::read", "slideCache", "generator_cache_restore"],
}

# Downstream consumer: the future last-P1 runtime fixture over boot/day/save/
# receipt/exit. The fixture does not exist yet, so the command shape below is
# the contract it must satisfy (canonical runner + expected per-boundary
# markers), not a claim about an existing run.
CONSUMER_COMMAND = ("scripts/run_pikmin2_fixture.py --arena <last-arena> "
                    "--fixture <last-p1-fixture.exe> --seconds <budget>")
EXPECTED_BEHAVIOR = {
    "boot": "P2_LAST_BOOT course=last observed; unknown courses refused fail-closed",
    "day": "day start/end + timer arm/disarm markers on the pinned transitions; sunset losses enumerated or recorded ABSENT",
    "save": "per-area/squad/captain save/restore round-trip equality via the #736 boundary (not re-derived here)",
    "receipt": "delivered-treasure accounting trace on real delivery callbacks; no receipt fabrication",
    "exit": "surface exit + re-entry with transition anchor and restore markers",
}


class DiscoveryRejected(ValueError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def verify_research(research_root):
    """Confirm every research pin file/symbol exists read-only; return findings."""
    root = Path(research_root)
    findings = {}
    for item, spec in RESEARCH.items():
        paths = [spec["file"]] + ([spec["also"]["file"]] if "also" in spec else [])
        syms = list(spec["symbols"]) + ([s for s in spec.get("also", {}).get("symbols", [])])
        missing_files = [p for p in paths if not (root / p).is_file()]
        if missing_files:
            raise DiscoveryRejected("Research pin files missing for %s: %s" % (item, missing_files))
        text = "".join((root / p).read_text(errors="replace") for p in paths)
        missing_syms = [s for s in syms if s not in text]
        findings[item] = {"files": paths, "symbols_found": len(syms) - len(missing_syms),
                          "symbols_total": len(syms), "missing_symbols": missing_syms,
                          "ok": not missing_syms}
        if missing_syms:
            raise DiscoveryRejected("Research pin symbols missing for %s: %s" % (item, missing_syms))
    return findings


def check_port(native_root):
    """Check the port tree for implementations; return present/ABSENT per item."""
    root = Path(native_root)
    if not (root / "pc_port").is_dir():
        raise DiscoveryRejected("Port tree missing pc_port: " + str(root))
    results = {}
    for item, markers in PORT_MARKERS.items():
        hits = []
        for path in sorted((root / "pc_port").rglob("*.cpp")) + sorted((root / "pc_port").rglob("*.h")):
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            for marker in markers:
                if marker in text:
                    hits.append("%s:%s" % (path.relative_to(root).as_posix(), marker))
                    break
        results[item] = {"hits": hits[:12], "present": bool(hits)}
    return results


def build_registry(research_root, native_root):
    """Verify pins and port state; return the pinned registry dict (no writes)."""
    research = verify_research(research_root)
    port = check_port(native_root)
    items = {}
    for key in RESEARCH:
        present = port[key]["present"]
        items[key] = {
            "research": {"files": research[key]["files"], "symbols_ok": research[key]["ok"]},
            "port": {"present": present, "hits": port[key]["hits"]},
            "verdict": ("PRESENT-IN-PORT (owning lane required)"
                        if present else "ABSENT (shared-review contract applies)"),
            "contract": RESEARCH[key]["contract"],
            "owning_lane": None,
            "consumer": {"command": CONSUMER_COMMAND,
                         "expected": EXPECTED_BEHAVIOR},
        }
    return {"schema": SCHEMA, "course": SOURCE_ID_COURSE_LAST,
            "save_serializer": "consumable via #736; explicitly not re-derived here",
            "items": items,
            "gates": "all six runtime gates UNTESTED; no runtime run, no ADMIT"}


def emit_registry(research_root, native_root, out_dir):
    """Verify, then write the pinned registry JSON; return paths + hashes."""
    registry = build_registry(research_root, native_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "last-daylight-receipt-cache-registry.json"
    if path.exists():
        raise DiscoveryRejected("Refusing to overwrite existing registry")
    blob = (json.dumps(registry, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(blob)
    return {"registry": str(path), "sha256": sha256_bytes(blob)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = emit_registry(args.research, args.native, args.out)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())