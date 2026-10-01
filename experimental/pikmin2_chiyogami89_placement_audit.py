"""Chiyogami89 retail placement audit (lane enemies-1-chiyogami89-placement-audit)."""
import argparse
import hashlib
import json
import sys

SOURCE_ID = 89
SCHEMA = "p2-chiyogami89-placement-audit-v1"
PACKET_SCHEMA = "p2-chiyogami89-placement-packet-v1"
GENERATOR_TOKEN = "\u5343\u4ee3\u7d19"
RESEARCH = "native/pikmin2-research"
ANCHORS = {
    "enum": {"file": RESEARCH + "/include/Game/enemyInfo.h", "line": 148,
             "text": "EnemyID_Chiyogami      = 89,  // Chigoyami paper",
             "sha256": "0e68be790e4f7f4a"},
    "info_row": {"file": RESEARCH + "/src/plugProjectYamashitaU/enemyInfo.cpp", "line": 85,
                 "flags": ["EFlag_HasNoInfo", "EFlag_CanBeSpawned", "2", "EFlag_UseOwnID"],
                 "sha256": "305f82601d5d31ac"},
    "generator_case": {"file": RESEARCH + "/src/plugProjectYamashitaU/genEnemy.cpp", "line": 551,
                       "token": GENERATOR_TOKEN, "sha256": "36a1d13fced4a43b"},
    "manager_case": {"file": RESEARCH + "/src/plugProjectYamashitaU/generalEnemyMgr.cpp", "line": 385,
                     "text": "mgr = new Chiyogami::Mgr(limit, viewNum);",
                     "sha256": "a01db128fe4cddaa"},
    "manager_impl": {"file": RESEARCH + "/src/plugProjectMorimuraU/plantsMgr.cpp", "line": 428,
                     "text": "Chiyogami::Mgr::Mgr(int objLimit, u8 modelType)",
                     "sha256": "02620aa3b9972e69"},
    "teki_read": {"file": RESEARCH + "/src/plugProjectKandoU/gameCaveInfo.cpp", "line": 66,
                  "text": "TekiInfo::read resolves the caveinfo name via getEnemyID(name, EFlag_CanBeSpawned)",
                  "sha256": "e449bf46ab24a663"},
    "gen_type": {"file": RESEARCH + "/include/Game/Cave/Info.h", "line": 40,
                 "text": "CGT_Plant, // 6", "sha256": "8d7b76ef45810f10"},
}

PLACEMENT = {
    "file": "user/Mukki/mapunits/caveinfo/yakushima_2.txt",
    "disc_offset": 770701016,
    "bytes": 6284,
    "sha256": "5a071801508a55ee5d21f5a9e5ff28c085c105a8a9af3eae1467c725c406db15",
    "floor_block_lines": [52, 74],
    "teki_block_lines": [75, 94],
    "entry_index": 7,
    "entry_lines": [92, 93],
    "entry_name": "Chiyogami",
    "weight": 2,
    "gen_type": 6,
    "gen_type_name": "CGT_Plant",
    "unit_pool": "1_units_large_toy.txt",
    "floor": 2,
    "cave_id": "yakushima_2",
    "sibling_treasures": ["g_futa_kyusyu", "cookie_m_l"],
}

CLASSIFICATION = "spawnable_plant_actor"

GATES = ("identity_spawn", "movement_animation", "attacks_receivers",
         "death_corpse", "transport_reward", "cleanup_reentry")

BLOCKERS = [
    "P1 gate scoping for 89 (future enemies-1 P1 observer lane; broad backlogs #143/#171 are not producers)",
    "Flora conversion contract (#171 lane scope) now that placement is proven",
]

KNOWN_CLASSIFICATIONS = ("spawnable_plant_actor", "scenery_usage_unconfirmed",
                         "generated_ambient", "non_actor")

def audit_row():
    """The validated per-identity audit row for source ID 89."""
    return {
        "schema": SCHEMA,
        "source_id": SOURCE_ID,
        "internal": "Chiyogami",
        "classification": CLASSIFICATION,
        "group": "flora",
        "owner_issue": 171,
        "generator_token": GENERATOR_TOKEN,
        "anchors": {k: dict(v) for k, v in ANCHORS.items()},
        "placement": dict(PLACEMENT),
        "verdict": ("89 is an ordinary spawnable plant actor: EFlag_CanBeSpawned + "
                    "EFlag_UseOwnID info row, a GENERATOR_CASE token, a real "
                    "Chiyogami::Mgr with birth, and one confirmed retail placement "
                    "as a CGT_Plant generator (weight 2) on yakushima_2 floor 2. "
                    "The prior scenery_usage_unconfirmed classification is resolved."),
        "p1_blockers": list(BLOCKERS),
        "gates": {g: "UNTESTED" for g in GATES},
    }


def validate_audit(row):
    """Return a list of refusal reasons; empty means the row is valid."""
    problems = []
    if not isinstance(row, dict):
        return ["row-must-be-dict"]
    if row.get("schema") != SCHEMA:
        problems.append("bad-schema")
    if row.get("source_id") != SOURCE_ID:
        problems.append("bad-source-id")
    if row.get("classification") not in KNOWN_CLASSIFICATIONS:
        problems.append("unknown-classification")
    anchors = row.get("anchors")
    if not isinstance(anchors, dict):
        problems.append("bad-anchors")
    else:
        for key in ("enum", "info_row", "generator_case", "manager_case",
                    "manager_impl", "teki_read", "gen_type"):
            anchor = anchors.get(key)
            if not isinstance(anchor, dict):
                problems.append("missing-anchor-" + key)
                continue
            if not anchor.get("file") or not isinstance(anchor.get("line"), int):
                problems.append("bad-anchor-" + key)
            sha = anchor.get("sha256", "")
            if not (isinstance(sha, str) and len(sha) >= 16 and
                    all(c in "0123456789abcdef" for c in sha)):
                problems.append("bad-anchor-hash-" + key)
    placement = row.get("placement")
    if not isinstance(placement, dict):
        problems.append("bad-placement")
    else:
        for key in ("file", "sha256", "floor", "entry_index", "weight",
                    "gen_type", "unit_pool", "cave_id"):
            if placement.get(key) in (None, ""):
                problems.append("missing-placement-" + key)
        if placement.get("gen_type") != 6:
            problems.append("placement-not-plant-type")
    gates = row.get("gates")
    if not isinstance(gates, dict) or set(gates) != set(GATES):
        problems.append("bad-gates")
    else:
        for gate, status in gates.items():
            if status not in ("UNTESTED", "PASS", "FAIL", "BLOCKED", "N/A"):
                problems.append("bad-gate-" + gate)
                break
    blockers = row.get("p1_blockers")
    if not isinstance(blockers, list) or not blockers or not all(
            isinstance(b, str) and b for b in blockers):
        problems.append("bad-blockers")
    return problems


def build_packet(row):
    """Machine-readable audit packet; refuses invalid rows."""
    problems = validate_audit(row)
    if problems:
        raise ValueError("refused: " + "; ".join(problems))
    return {
        "schema": PACKET_SCHEMA,
        "source_id": row["source_id"],
        "internal": row["internal"],
        "classification": row["classification"],
        "generator_token": row["generator_token"],
        "anchors": row["anchors"],
        "placement": row["placement"],
        "verdict": row["verdict"],
        "p1_blockers": row["p1_blockers"],
        "gates": row["gates"],
        "runtime_claim": False,
    }


def packet_sha256(packet):
    return hashlib.sha256(
        json.dumps(packet, indent=1, sort_keys=True).encode("utf-8")).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Chiyogami89 placement audit")
    parser.add_argument("--packet-out", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    row = audit_row()
    problems = validate_audit(row)
    if problems:
        for problem in problems:
            print("REFUSED reason=%s" % problem)
        return 1
    if args.check or args.packet_out is None:
        print("AUDIT_PASS source_id=%d classification=%s" % (SOURCE_ID, CLASSIFICATION))
    if args.packet_out:
        packet = build_packet(row)
        with open(args.packet_out, "w", encoding="utf-8") as f:
            f.write(json.dumps(packet, indent=1, sort_keys=True))
            f.write("\n")
        print("packet=%s sha256=%s" % (args.packet_out, packet_sha256(packet)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
