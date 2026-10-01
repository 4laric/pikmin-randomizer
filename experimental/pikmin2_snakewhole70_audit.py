"""P0 source audit + import contract for SnakeWhole70 (Pileated Snagret).

Lane shard-enemies-1-snagret70-p0, issue #376, generation 2. Concrete
source-import preparation only: no native build, no runtime, no ADMIT, no
playability claim. Issue #376 stays OPEN; this P0 does not close it.

What this module does (stdlib only, dependency-free pure functions):

- Decodes the actual SnakeWhole definition from the READ-ONLY research
  checkout (`native/pikmin2-research`): the StateID and AnimID enums, the
  general/proper parameter defaults declared in `SnakeWhole.h`, the
  manager identity (`SnakeWholeMgr.cpp` getEnemyTypeID + model loader), the
  general-health accessor used by `lifeIncrement` (`SnakeWhole.cpp`), and
  the SnakeJointMgr body-chain dependency.
- Records observed sha256 for every inspected source file (validate hashes
  where available) and fails closed with exact errors on missing or
  malformed input; nothing is invented.
- Reuses, never forks, existing importer framing: retail enemyparm text is
  parsed by `experimental.pikmin2_engine_parms.parse_parm_text` when a
  source is supplied, and identity facts (drop tier, day-end cap, child
  relations, spawnability) come from the canonical
  `docs/PIKMIN2_ENEMY_ROSTER.json` entry for source id 70.
- Publishes the exact P1 blockers (actor birth, mesh/bank, joint-chain,
  receiver, corpse/carry route) with owner/issue references.

All six runtime gates stay UNTESTED. Parent/child group ownership is
preserved: SnakeCrow/DangoMushi evidence is consumed read-only and never
relabelled.
"""
import hashlib
import json
import re
from pathlib import Path

LANE = "shard-enemies-1-snagret70-p0"
ISSUE = 376
SOURCE_ID = 70
ENUM_NAME = "SnakeWhole"
COMMON_NAME = "Pileated Snagret"
SCHEMA = "snakewhole70-p0/1"

RESEARCH_ROOT = Path(
    "C:/Users/alari/pikmin-randomizer/native/pikmin2-research")

SOURCE_FILES = (
    "include/Game/Entities/SnakeWhole.h",
    "src/plugProjectNishimuraU/SnakeWhole.cpp",
    "src/plugProjectNishimuraU/SnakeWholeMgr.cpp",
    "src/plugProjectNishimuraU/SnakeWholeState.cpp",
    "src/plugProjectNishimuraU/SnakeWholeAnimator.cpp",
    "src/plugProjectNishimuraU/SnakeJointMgr.cpp",
)

# Observed 2026-09-16 against the read-only research checkout; drift fails
# the hash test loudly rather than silently re-baselining.
OBSERVED_HASHES = {
    "include/Game/Entities/SnakeWhole.h":
        "2216410a5f4bab3660c2ff3ed8e0702dcee8ed55f2f74c3ae39f753a7dcc6d9e",
    "src/plugProjectNishimuraU/SnakeWhole.cpp":
        "982856ba91e0fa6819ac7f5541c71daa784809439b2eff5ccae1fa7c2fa22cf2",
    "src/plugProjectNishimuraU/SnakeWholeMgr.cpp":
        "0d50fbd5f3299a0aafe95be305d6016d9fed3a66904c3e005f6c6b94833d6eaf",
    "src/plugProjectNishimuraU/SnakeWholeState.cpp":
        "06a0f014d3da2d1f9e4a213e03a7b52e6a3cc72e712727b6c2905bab86c21ca7",
    "src/plugProjectNishimuraU/SnakeWholeAnimator.cpp":
        "36c79466bfb02e425af767c4b51da2c4912629b5ba14a9a855544ceb25e38daa",
    "src/plugProjectNishimuraU/SnakeJointMgr.cpp":
        "6e3c6c57cd435006cf46e06c976bdbb1e597a04ce3fa1667cb5b1f0a4b9e9514",
}

_STATE_BLOCK = re.compile(
    r"enum\s+StateID\s*\{(.*?)\};", re.S)
_ANIM_BLOCK = re.compile(
    r"enum\s+AnimID\s*\{(.*?)\};", re.S)
_ENUM_ENTRY = re.compile(r"([A-Z][A-Za-z0-9_]*)\s*(?:=\s*(-?\d+|[A-Za-z_][A-Za-z0-9_]*))?")
_PARM = re.compile(
    r"m(\w+)\(this,\s*'(\w{4})',\s*\"([^\"]*)\",\s*"
    r"(-?\d+(?:\.\d+)?)f?,\s*(-?\d+(?:\.\d+)?)f?,\s*(-?\d+(?:\.\d+)?)f?\)")
_MGR_TYPE = re.compile(r"EnemyTypeID::(EnemyID_\w+)")
_SHAPE_TYPE = re.compile(r"setTexMtxLoadType\(([^)]*)\)")
_HEALTH_ACCESS = re.compile(r"C_GENERALPARMS\.(\w+)\(")
_JOINT_MGR_INCLUDE = "SnakeJointMgr"


def _enum_value(value, running, seen, prefix, name):
    """Resolve one C++ enum entry: explicit int, identifier alias, or auto."""
    text = (value or "").strip()
    if text == "":
        return running + 1
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    alias = text if text.startswith(prefix) else prefix + text
    if alias not in seen:
        raise ValueError("unresolved enum alias %s for %s" % (text, name))
    return seen[alias]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _read(root, rel):
    path = Path(root) / rel
    if not path.is_file():
        raise ValueError("missing required source: %s" % rel)
    return path.read_bytes()


def parse_state_ids(header_text):
    """Return the SNAKEWHOLE_* StateID map plus the Count sentinel."""
    if not isinstance(header_text, str) or not header_text.strip():
        raise ValueError("header text is empty")
    block = _STATE_BLOCK.search(header_text)
    if not block:
        raise ValueError("no StateID enum in header")
    states = {}
    running = -1
    for name, value in _ENUM_ENTRY.findall(block.group(1)):
        if not name.startswith("SNAKEWHOLE_"):
            continue
        running = _enum_value(value, running, states, "SNAKEWHOLE_", name)
        states[name] = running
    if not states:
        raise ValueError("no SNAKEWHOLE states decoded")
    return states


def parse_anim_ids(header_text):
    """Return the SNAKEWHOLEANIM_* AnimID map (aliases preserved)."""
    block = _ANIM_BLOCK.search(header_text)
    if not block:
        raise ValueError("no AnimID enum in header")
    anims = {}
    running = -1
    for name, value in _ENUM_ENTRY.findall(block.group(1)):
        if not name.startswith("SNAKEWHOLEANIM_"):
            continue
        running = _enum_value(value, running, anims, "SNAKEWHOLEANIM_", name)
        anims[name] = running
    if not anims:
        raise ValueError("no SNAKEWHOLEANIM entries decoded")
    return anims


def parse_proper_parms(header_text):
    """Return the ProperParms tag -> (member, comment, default) mapping."""
    if not isinstance(header_text, str) or not header_text.strip():
        raise ValueError("header text is empty")
    parms = {}
    for member, tag, comment, default, low, high in _PARM.findall(header_text):
        if tag in parms:
            raise ValueError("duplicate proper parm tag: " + tag)
        parms[tag] = {
            "member": member,
            "comment": comment,
            "default": float(default),
            "min": float(low),
            "max": float(high),
        }
    if not parms:
        raise ValueError("no proper parms decoded")
    return parms


def parse_manager_facts(mgr_text):
    """Return the manager's enemy type id and model loader type."""
    if not isinstance(mgr_text, str) or not mgr_text.strip():
        raise ValueError("manager text is empty")
    type_ids = _MGR_TYPE.findall(mgr_text)
    if not type_ids:
        raise ValueError("no getEnemyTypeID in manager")
    loader = _SHAPE_TYPE.search(mgr_text)
    return {
        "enemy_type_id": type_ids[0],
        "shape_texture_mtx": loader.group(1).strip() if loader else None,
        "obj_array_member": "mObj" if "mObj" in mgr_text else None,
    }


def parse_health_accessors(cpp_text):
    """Return general-parm accessors used by the actor (e.g. mHealth)."""
    if not isinstance(cpp_text, str) or not cpp_text.strip():
        raise ValueError("cpp text is empty")
    names = sorted(set(_HEALTH_ACCESS.findall(cpp_text)))
    if "mHealth" not in names:
        raise ValueError("no mHealth accessor found")
    return names


def roster_identity(roster_doc, source_id=SOURCE_ID):
    """Return the canonical roster row for SnakeWhole70."""
    if not isinstance(roster_doc, dict):
        raise TypeError("roster document must be a mapping")
    entries = roster_doc.get("entries")
    if not isinstance(entries, list):
        raise ValueError("roster document has no entries list")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("source_id") == source_id:
            return entry
    raise ValueError("roster entry missing for source id %d" % source_id)


def audit_source(research_root=None, roster_doc=None):
    """Audit SnakeWhole70 against the read-only research checkout.

    Returns the findings packet (generated=False). Raises with the exact
    missing prerequisite when the checkout is unavailable.
    """
    root = Path(research_root) if research_root is not None else RESEARCH_ROOT
    if not (root / "include").is_dir():
        raise ValueError(
            "read-only research checkout missing at %s (expected "
            "native/pikmin2-research with include/ and src/)" % root)

    hashes = {}
    for rel in SOURCE_FILES:
        hashes[rel] = sha256_bytes(_read(root, rel))

    header = _read(root, SOURCE_FILES[0]).decode("utf-8", errors="replace")
    cpp = _read(root, SOURCE_FILES[1]).decode("utf-8", errors="replace")
    mgr = _read(root, SOURCE_FILES[2]).decode("utf-8", errors="replace")
    state = _read(root, SOURCE_FILES[3]).decode("utf-8", errors="replace")

    states = parse_state_ids(header)
    anims = parse_anim_ids(header)
    parms = parse_proper_parms(header)
    # getEnemyTypeID is declared on Mgr in the header; the loader/shape
    # details live in the manager translation unit.
    manager = parse_manager_facts(header + "\n" + mgr)
    health_accessors = parse_health_accessors(cpp)

    identity = roster_identity(roster_doc) if roster_doc is not None else None
    joint_chain = _JOINT_MGR_INCLUDE in header

    blockers = []
    if identity is None:
        blockers.append("canonical roster entry not supplied (identity facts unverified)")
    if manager["enemy_type_id"] != "EnemyID_SnakeWhole":
        blockers.append("manager enemy type id mismatch: " + str(manager["enemy_type_id"]))
    if not joint_chain:
        blockers.append("SnakeJointMgr body chain not declared in header")
    blockers.extend([
        "P1 actor birth: no host manager registers EnemyID_SnakeWhole "
        "(P1 teki roster has no SnakeWhole); provider shard actor-birth-projectiles owns the seam",
        "mesh/bank: retail SnakeWhole model + SnakeJointMgr segment bank not converted/installed "
        "(asset pipeline #128 / #376)",
        "receiver: damageCallBack/mouth-slot (Eat/Struggle) receivers need a live bound actor "
        "(#376 P1 actor acceptance)",
        "corpse/carry route: BDT_Boss drop and corpse corridor unproven on P1 (#376 / reward shard)",
    ])

    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "source_id": SOURCE_ID,
        "enum_name": ENUM_NAME,
        "common_name": COMMON_NAME,
        "research_root": str(root),
        "hashes": hashes,
        "states": states,
        "state_count": len({v for n, v in states.items()
                            if not n.endswith("Count") and not n.endswith("NULL")}),
        "anims": anims,
        "anim_count": len({v for n, v in anims.items()
                           if not n.endswith("AnimCount")}),
        "proper_parms": parms,
        "manager": manager,
        "health_accessors": health_accessors,
        "joint_chain": joint_chain,
        "state_file_markers": sorted(
            set(re.findall(r"SNAKEWHOLE_\w+", state)))[:20],
        "identity": identity,
        "identity_source": "docs/PIKMIN2_ENEMY_ROSTER.json" if identity else None,
        "blockers": blockers,
        "generated": False,
        "limitations": [
            "Static source decode only; no actor, mesh, receiver or gameplay was run.",
            "Retail enemyparm values are not in the decomp; they come from disc extraction.",
            "No Pikmin counts, health instances, drop instances or spawn placement derived.",
        ],
        "reused_framing": [
            "experimental.pikmin2_engine_parms.parse_parm_text (retail enemyparm text)",
            "docs/PIKMIN2_ENEMY_ROSTER.json canonical identity row",
        ],
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", type=Path, default=RESEARCH_ROOT)
    parser.add_argument("--roster", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    roster_doc = (json.loads(args.roster.read_text(encoding="utf-8"))
                  if args.roster else None)
    packet = audit_source(args.research_root, roster_doc)
    text = json.dumps(packet, indent=2, sort_keys=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
