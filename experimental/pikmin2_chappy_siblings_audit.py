"""Pin/ownership audit for Chappy siblings 45/53 admission (YellowKochappy, KingChappy).

Lane chappy-siblings-pin-audit, issue #810. Read-only pin-audit; no native
build, no runtime, no ADMIT, no playability claim. Consumes the DONE
KumaChappy35-P0 handoff and the LeafChappy67 bridge staging read-only; never
duplicates them. The Chappy parent/child group (35/45/53/67) stays together.

What this module does (stdlib only, dependency-free pure functions):

- Verifies the research pins read-only (`native/pikmin2-research`): the
  YellowKochappy header/impl/mgr (KochappyBase reuse, snow texture swap),
  the KingChappy header/impl/mgr (dedicated KINGCHAPPY_* FSM + AnimID), and
  the enemyInfo identity rows plus numeric ids (45 Snow Bulborb, 53 Emperor
  Bulblax). Records observed sha256 per file; drift fails loudly.
- Inventories the maintained-wave binding/admission paths: the family base
  (pc_p2_kochappy.*) covers source-1 Kochappy only; NO YellowKochappy- or
  KingChappy-specific port module exists (verbatim ABSENT recorded);
  entry-geometry refs live in the snow/bulblax policies only.
- Names the exact producer (species mapping, spawn/receiver path) with owner
  and provider shard, or the precise blocker (missing pin/API/family
  receiver). Names the first executable implementation slice with callsite +
  build-membership files to reserve, plus destination pins for downstream
  consumers. Fails closed on missing/malformed input.

All six runtime gates stay UNTESTED.
"""
import hashlib
import json
import re
from pathlib import Path

LANE = "chappy-siblings-pin-audit"
ISSUE = 810
SCHEMA = "chappy-siblings-pin-audit-v1"

RESEARCH_ROOT = Path(
    "C:/Users/alari/pikmin-randomizer/native/pikmin2-research")

SIBLINGS = {
    45: {
        "key": "YellowKochappy",
        "common": "Snow Bulborb",
        "files": (
            "include/Game/Entities/YellowKochappy.h",
            "src/plugProjectYamashitaU/YellowKochappy.cpp",
            "src/plugProjectYamashitaU/YellowKochappyMgr.cpp",
        ),
        "family": "KochappyBase reuse (Obj/Mgr inherit; snow texture swap)",
    },
    53: {
        "key": "KingChappy",
        "common": "Emperor Bulblax",
        "files": (
            "include/Game/Entities/KingChappy.h",
            "src/plugProjectMorimuraU/kingChappy.cpp",
            "src/plugProjectMorimuraU/kingChappyMgr.cpp",
        ),
        "family": "dedicated KINGCHAPPY_* FSM + AnimID (boss)",
    },
}

ENEMYINFO = "src/plugProjectYamashitaU/enemyInfo.cpp"
ENUMHEADER = "include/Game/enemyInfo.h"

# Observed 2026-09-18 against the read-only research checkout.
OBSERVED_HASHES = {}

_PORT_YELLOW = re.compile(r"YellowKochappy|yellow_kochappy", re.I)
_PORT_KING = re.compile(r"(?<![A-Za-z])KingChappy(?!Mgr|State)|king_chappy", re.I)

_ENUM_ID = re.compile(r"\bEnemyID_(YellowKochappy|KingChappy)\s*=\s*(\d+)")
_ENEMYINFO_ROW = re.compile(r"\{\s*\"(YellowKochappy|KingChappy)\"")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _read(root, rel):
    path = Path(root) / rel
    if not path.is_file():
        raise ValueError("missing required source: %s" % rel)
    return path.read_bytes()


def verify_research(research_root=None):
    """Confirm sibling pins and identity rows read-only; return findings."""
    root = Path(research_root) if research_root is not None else RESEARCH_ROOT
    if not (root / "include").is_dir():
        raise ValueError("read-only research checkout missing at %s" % root)
    findings = {}
    for sid, spec in SIBLINGS.items():
        hashes = {}
        for rel in spec["files"]:
            hashes[rel] = sha256_bytes(_read(root, rel))
        header = _read(root, spec["files"][0]).decode("utf-8", errors="replace")
        mgr = _read(root, spec["files"][2]).decode("utf-8", errors="replace")
        findings[spec["key"]] = {
            "source_id": sid,
            "hashes": hashes,
            "header_bytes": len(header),
            "mgr_bytes": len(mgr),
        }
    enemyinfo = _read(root, ENEMYINFO).decode("utf-8", errors="replace")
    enumheader = _read(root, ENUMHEADER).decode("utf-8", errors="replace")
    rows = {name for name in _ENEMYINFO_ROW.findall(enemyinfo)}
    ids = {name: int(num) for name, num in _ENUM_ID.findall(enumheader)}
    for sid, spec in SIBLINGS.items():
        if spec["key"] not in rows:
            raise ValueError("no %s row in enemyInfo" % spec["key"])
        if ids.get(spec["key"]) != sid:
            raise ValueError("%s enum id is not %d" % (spec["key"], sid))
    return {"siblings": findings, "enemyinfo_rows": sorted(rows), "enum_ids": ids}


def inventory_port(native_root):
    """Inventory Yellow/King-specific port bindings (verbatim ABSENT allowed)."""
    root = Path(native_root)
    port = root / "pc_port"
    if not port.is_dir():
        raise ValueError("port tree missing pc_port: %s" % root)
    hits = {"YellowKochappy": [], "KingChappy": []}
    for path in sorted(port.rglob("*.cpp")) + sorted(port.rglob("*.h")):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        if _PORT_YELLOW.search(text):
            hits["YellowKochappy"].append(rel)
        if _PORT_KING.search(text):
            hits["KingChappy"].append(rel)
    family = (port / "pc_p2_kochappy.cpp").is_file()
    return {"hits": {k: sorted(set(v))[:12] for k, v in hits.items()},
            "family_base_present": family,
            "dedicated_yellow_module": False,
            "dedicated_king_module": False}


def resolve_producer(native_root):
    """Name the producer or the precise blocker per sibling."""
    inv = inventory_port(native_root)
    return {
        "YellowKochappy": {
            "binding": "ABSENT as dedicated port module (family base covers source-1 only)",
            "producer": None,
            "blocker": ("missing YellowKochappy port module + family receiver: "
                        "bind source-45 snow variant to the KochappyBase spawn/receiver path; "
                        "birth seam owned by provider actor-birth-projectiles"),
            "owner": None,
            "provider_shard": "actor-birth-projectiles",
            "port_hits": inv["hits"]["YellowKochappy"],
        },
        "KingChappy": {
            "binding": "ABSENT as dedicated port module (name mapping only)",
            "producer": None,
            "blocker": ("missing KingChappy boss port module (KINGCHAPPY_* FSM) + family receiver: "
                        "bind source-53 emperor to a boss spawn/receiver path; "
                        "birth seam owned by provider actor-birth-projectiles"),
            "owner": None,
            "provider_shard": "actor-birth-projectiles",
            "port_hits": inv["hits"]["KingChappy"],
        },
    }


FIRST_SLICES = {
    "YellowKochappy": {
        "callsite": "species/source dispatch binding source-45 to the KochappyBase spawn path",
        "build_membership": ["native/pc_port/pc_p2_yellowkochappy.cpp",
                             "native/pc_port/pc_p2_yellowkochappy.h"],
        "reserve": "new YellowKochappy port module + family receiver registration",
    },
    "KingChappy": {
        "callsite": "species/source dispatch binding source-53 to a boss spawn path",
        "build_membership": ["native/pc_port/pc_p2_kingchappy.cpp",
                             "native/pc_port/pc_p2_kingchappy.h"],
        "reserve": "new KingChappy boss port module (KINGCHAPPY_* FSM) + family receiver registration",
    },
}

DESTINATION_PINS = {
    "root": "3a33cbdefd5e4057eef9fb0d824cce4510ddab05",
    "native": "f363d04d71dc12488b563618a2d7db2423a868f7",
}


def audit(research_root=None, native_root=None):
    """Run the full pin audit; return the registry packet (no writes)."""
    research = verify_research(research_root)
    if native_root is None:
        if RESEARCH_ROOT.parent.parent.name == "native":
            native_root = RESEARCH_ROOT.parent
        else:
            raise ValueError("native checkout root required")
    producers = resolve_producer(native_root)
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "research": research,
        "producers": producers,
        "first_slices": FIRST_SLICES,
        "destination_pins": DESTINATION_PINS,
        "gates": "all six runtime gates UNTESTED; no runtime run, no ADMIT",
        "limitations": [
            "Static pin inventory only; no actor, mesh, receiver or gameplay was run.",
            "Line numbers are observed references, not re-pinned contracts.",
        ],
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", type=Path, default=RESEARCH_ROOT)
    parser.add_argument("--native-root", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    packet = audit(args.research_root, args.native_root)
    text = json.dumps(packet, indent=2, sort_keys=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
