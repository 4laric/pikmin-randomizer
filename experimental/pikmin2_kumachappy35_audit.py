"""P0 source audit + import contract for KumaChappy35 (Spotty Bulbear).

Lane shard-enemies-6-kumachappy35-p0, issue #613, generation 2. Concrete
source-import preparation only: no native build, no runtime, no ADMIT, no
playability claim. Issue #613 stays OPEN; this P0 does not close it.

What this module does (stdlib only, dependency-free pure functions):

- Decodes the actual KumaChappy definition from the READ-ONLY research
  checkout (`native/pikmin2-research`): the StateID and AnimID enums (C++
  auto-increment and identifier-alias semantics preserved), the general
  and proper parameter defaults declared in `KumaChappy.h`, the manager
  identity (`KumaChappyMgr.cpp` name constant plus `getEnemyTypeID`),
  general-health and carcass-motion references in `KumaChappy.cpp`, the
  dwarf-follower relation (`ChappyRelation`), and the enemyInfo identity
  row (id, flags, model bank, child relations, drop tier) parsed strictly
  from `enemyInfo.cpp` / `enemyInfo.h` (no invented values).
- Records observed sha256 for every inspected source file (validate hashes
  where available) and fails closed with exact errors on missing or
  malformed input.
- Reuses, never forks, existing importer framing: retail enemyparm text is
  parsed by `experimental.pikmin2_engine_parms.parse_parm_text` when a
  source is supplied; asset/model-bank facts are read, never restated.
- Publishes the exact P1 blockers (actor birth/manager, mesh/bank,
  receiver, corpse/carry route) with owner/issue refs.

All six runtime gates stay UNTESTED. Parent/child group ownership is
preserved: the Bulborb/Bulbear family (#120) and sibling Snow Bulborb 45
evidence are consumed read-only, never relabelled. Shared generic
providers (actor-birth-projectiles, treasure-receipts, placement-catalog,
save-progression, runtime-fixtures) belong to their provider shards.
"""
import hashlib
import re
from pathlib import Path

LANE = "shard-enemies-6-kumachappy35-p0"
ISSUE = 613
SOURCE_ID = 35
ENUM_NAME = "KumaChappy"
COMMON_NAME = "Spotty Bulbear"
SCHEMA = "kumachappy35-p0/1"

RESEARCH_ROOT = Path(
    "C:/Users/alari/pikmin-randomizer/native/pikmin2-research")

SOURCE_FILES = (
    "include/Game/Entities/KumaChappy.h",
    "src/plugProjectNishimuraU/KumaChappy.cpp",
    "src/plugProjectNishimuraU/KumaChappyMgr.cpp",
    "src/plugProjectNishimuraU/KumaChappyState.cpp",
    "src/plugProjectNishimuraU/KumaChappyAnimator.cpp",
    "src/plugProjectYamashitaU/enemyInfo.cpp",
    "include/Game/enemyInfo.h",
)

# Observed 2026-09-16 against the read-only research checkout; drift fails
# the hash test loudly rather than silently re-baselining.
OBSERVED_HASHES = {
    "include/Game/Entities/KumaChappy.h":
        "ac6df273c5c932c06ed86046b368a18f17b0d69b7ae2f467bed6b18b7692d8d4",
    "src/plugProjectNishimuraU/KumaChappy.cpp":
        "961ba9bf76980a937e3745686c024bb4640943d1de3bae329072192a0e669b81",
    "src/plugProjectNishimuraU/KumaChappyMgr.cpp":
        "66f2283fa6d34b0fa2155208995daecea20468ab1669685acb75cd9fb621ba54",
    "src/plugProjectNishimuraU/KumaChappyState.cpp":
        "2b1fe1fb83a82b3233058c918261708072c60e42e8349a38f991690b4f284713",
    "src/plugProjectNishimuraU/KumaChappyAnimator.cpp":
        "76772e3ac93dc96840a8c74bb9bdef68dc36598b8343ba822be081bbdda8d2d6",
    "src/plugProjectYamashitaU/enemyInfo.cpp":
        "305f82601d5d31ac47f490c9ba734ff33379d0572d00397adf4f9dbfbb891dbb",
    "include/Game/enemyInfo.h":
        "0e68be790e4f7f4a99a48064b4750a95367c09996b7484292a33b2969d9b44ba",
}

_STATE_BLOCK = re.compile(r"enum\s+StateID\s*\{(.*?)\};", re.S)
_ANIM_BLOCK = re.compile(r"enum\s+AnimID\s*\{(.*?)\};", re.S)
_ENUM_ENTRY = re.compile(r"([A-Z][A-Za-z0-9_]*)\s*(?:=\s*(-?\d+|[A-Za-z_][A-Za-z0-9_]*))?")
_PARM = re.compile(
    r"m(\w+)\(this,\s*'(\w{4})',\s*\"([^\"]*)\",\s*"
    r"(-?\d+(?:\.\d+)?)f?,\s*(-?\d+(?:\.\d+)?)f?,\s*(-?\d+(?:\.\d+)?)f?\)")
_MGR_CONST = re.compile(r"static\s+const\s+char\s+\w+\[\]\s*=\s*\"([^\"]+)\"")
_HEALTH_MEMBER = re.compile(r"\bm(Health|MaxHealth)\b")
# {"Name", EnemyID_X, parent, members, (flags), res x7, child, child_count, drop}
_ENEMYINFO_ROW = re.compile(
    r"\{\s*\"KumaChappy\"\s*,\s*EnemyTypeID::(EnemyID_\w+)\s*,\s*(-?\d+)\s*,\s*"
    r"(\d+)\s*,\s*\(([^)]*)\)\s*,\s*"
    r"((?:\"[^\"]*\"\s*,\s*){7})"
    r"(-?\d+)\s*,\s*(\d+)\s*,\s*(BDT_\w+)\s*\},?")
_ENUM_ID_LINE = re.compile(r"\bEnemyID_KumaChappy\s*=\s*(\d+)")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _read(root, rel):
    path = Path(root) / rel
    if not path.is_file():
        raise ValueError("missing required source: %s" % rel)
    return path.read_bytes()


def _enum_value(value, running, seen, prefix, name):
    text = (value or "").strip()
    if text == "":
        return running + 1
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    alias = text if text.startswith(prefix) else prefix + text
    if alias not in seen:
        raise ValueError("unresolved enum alias %s for %s" % (text, name))
    return seen[alias]


def parse_state_ids(header_text):
    """Return the KUMACHAPPY_* StateID map (C++ enum semantics)."""
    if not isinstance(header_text, str) or not header_text.strip():
        raise ValueError("header text is empty")
    block = _STATE_BLOCK.search(header_text)
    if not block:
        raise ValueError("no StateID enum in header")
    states = {}
    running = -1
    for name, value in _ENUM_ENTRY.findall(block.group(1)):
        if not name.startswith("KUMACHAPPY_"):
            continue
        running = _enum_value(value, running, states, "KUMACHAPPY_", name)
        states[name] = running
    if not states:
        raise ValueError("no KUMACHAPPY states decoded")
    return states


def parse_anim_ids(header_text):
    """Return the KUMACHAPPYANIM_* AnimID map (aliases resolved)."""
    block = _ANIM_BLOCK.search(header_text)
    if not block:
        raise ValueError("no AnimID enum in header")
    anims = {}
    running = -1
    for name, value in _ENUM_ENTRY.findall(block.group(1)):
        if not name.startswith("KUMACHAPPYANIM_"):
            continue
        running = _enum_value(value, running, anims, "KUMACHAPPYANIM_", name)
        anims[name] = running
    if not anims:
        raise ValueError("no KUMACHAPPYANIM entries decoded")
    return anims


def parse_proper_parms(header_text):
    """Return the ProperParms tag -> (member, comment, default/min/max)."""
    if not isinstance(header_text, str) or not header_text.strip():
        raise ValueError("header text is empty")
    parms = {}
    for member, tag, comment, default, low, high in _PARM.findall(header_text):
        if tag in parms:
            raise ValueError("duplicate proper parm tag: " + tag)
        # Declaration order is (default, min, max).
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


def parse_manager_facts(mgr_text, header_text=""):
    """Return the manager name constant and enemy type identity."""
    if not isinstance(mgr_text, str) or not mgr_text.strip():
        raise ValueError("manager text is empty")
    const = _MGR_CONST.search(mgr_text)
    combined = (header_text or "") + "\n" + mgr_text
    type_ids = re.findall(r"EnemyTypeID::(EnemyID_\w+)", combined)
    if not type_ids:
        raise ValueError("no getEnemyTypeID in manager sources")
    return {
        "manager_name_const": const.group(1) if const else None,
        "enemy_type_id": type_ids[0],
        "obj_array_member": "mObj" if "mObj" in mgr_text else None,
    }


def parse_actor_refs(cpp_text):
    """Return general-health, carcass and follower references in the actor."""
    if not isinstance(cpp_text, str) or not cpp_text.strip():
        raise ValueError("cpp text is empty")
    members = sorted(set(_HEALTH_MEMBER.findall(cpp_text)))
    if "Health" not in members or "MaxHealth" not in members:
        raise ValueError("no mHealth accessor found")
    return {
        "health_members": members,
        "carcass_motion": "startCarcassMotion" in cpp_text,
        "become_carcass": "doBecomeCarcass" in cpp_text,
        "follower_relation": "ChappyRelation" in cpp_text,
    }


def parse_enemyinfo_row(cpp_text, header_text=""):
    """Decode the KumaChappy row of enemyInfo.cpp plus its enum id."""
    if not isinstance(cpp_text, str) or not cpp_text.strip():
        raise ValueError("enemyInfo text is empty")
    match = _ENEMYINFO_ROW.search(cpp_text)
    if not match:
        raise ValueError("no KumaChappy row in enemyInfo")
    enum_id, parent, members, flags, resources, child, child_count, drop = \
        match.groups()
    resource_list = re.findall(r"\"([^\"]*)\"", resources)
    identities = _ENUM_ID_LINE.findall(header_text) if header_text else []
    if identities and identities[0] != "35":
        raise ValueError("KumaChappy enum id is not 35")
    return {
        "enum_id": enum_id,
        "numeric_id": int(identities[0]) if identities else None,
        "parent": int(parent),
        "members": int(members),
        "flags": " ".join(flags.split()),
        "resources": resource_list,
        "model_bank": resource_list[1] if len(resource_list) > 1 else None,
        "child": int(child),
        "child_count": int(child_count),
        "drop": drop,
    }


def audit_source(research_root=None):
    """Audit KumaChappy35 against the read-only research checkout."""
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
    enemyinfo = _read(root, SOURCE_FILES[5]).decode("utf-8", errors="replace")
    enumheader = _read(root, SOURCE_FILES[6]).decode("utf-8", errors="replace")

    states = parse_state_ids(header)
    anims = parse_anim_ids(header)
    parms = parse_proper_parms(header)
    manager = parse_manager_facts(mgr, header)
    actor = parse_actor_refs(cpp)
    identity = parse_enemyinfo_row(enemyinfo, enumheader)

    blockers = []
    if manager["enemy_type_id"] != "EnemyID_KumaChappy":
        blockers.append("manager enemy type id mismatch: "
                        + str(manager["enemy_type_id"]))
    if identity["numeric_id"] != SOURCE_ID:
        blockers.append("enemyInfo numeric id is not 35")
    blockers.extend([
        "P1 actor birth: no host manager registers EnemyID_KumaChappy "
        "(candidate host vehicle TEKI_Swallob 32, the P1 Spotty Bulbear, is "
        "UNVERIFIED for this role); provider shard actor-birth-projectiles "
        "owns the seam (#169/#186 coordination)",
        "mesh/bank: retail model bank %r plus anim bank not converted/installed "
        "(asset pipeline #128 / #613)" % (identity["model_bank"],),
        "receiver: damageCallBack and mouth-slot receivers need a live bound "
        "actor (#613 P1 actor acceptance)",
        "corpse/carry route: %s drop and corpse corridor unproven on P1 "
        "(#613 / reward shard)" % (identity["drop"],),
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
                            if not n.endswith("StateCount") and not n.endswith("NULL")}),
        "anims": anims,
        "anim_count": len({v for n, v in anims.items()
                           if not n.endswith("AnimCount")}),
        "proper_parms": parms,
        "manager": manager,
        "actor": actor,
        "identity": identity,
        "blockers": blockers,
        "generated": False,
        "limitations": [
            "Static source decode only; no actor, mesh, receiver or gameplay was run.",
            "Retail enemyparm values are not in the decomp; they come from disc extraction.",
            "No Pikmin counts, health instances, drop instances or spawn placement derived.",
        ],
        "reused_framing": [
            "experimental.pikmin2_engine_parms.parse_parm_text (retail enemyparm text)",
            "enemyInfo.cpp/enemyInfo.h canonical identity row (source-derived)",
        ],
    }


def main(argv=None):
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", type=Path, default=RESEARCH_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    packet = audit_source(args.research_root)
    text = json.dumps(packet, indent=2, sort_keys=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
