"""Pin-discovery/ownership for Houdai_light_a cargo on tutorial_2 floor 9.

Issue #782 (downstream consumer #747 p2-cave-tutorial_2-p1-later-floors).
Read-only: inspects the canonical content inventory, import lanes doc and the
decomp enemy table; never edits source. Fail-closed: any malformed or missing
input raises PinError; unclassifiable tokens are reported ABSENT with reason,
never invented.

Finding (recorded 2026-09-18): Houdai_light_a is a compound spawn token
<enemy Houdai>_<carried item light_a>: a Man-at-Legs (EnemyID_Houdai = 66)
carrying item light_a (archive light_a.szs, model eq_flashlight.bmd).
"""
import json
import re
import sys
from pathlib import Path

TOKEN = "Houdai_light_a"
CAVE_ID = "tutorial_2"
FLOOR = 9
DOWNSTREAM_ISSUE = 747
DOWNSTREAM_LANE = "p2-cave-tutorial_2-p1-later-floors"


class PinError(Exception):
    """Fail-closed refusal: malformed/missing input or unclassifiable token."""


def repo_root_from_here() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent,) + tuple(here.parents):
        if (parent / "docs" / "PIKMIN2_CONTENT_INVENTORY.json").exists():
            return parent
    raise PinError("cannot locate repo root from %s" % here)


def load_json(path: Path):
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PinError("missing input refused: %s (%s)" % (path, exc))
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PinError("malformed input refused (not utf-8): %s (%s)" % (path, exc))
    try:
        return json.loads(text), text
    except json.JSONDecodeError as exc:
        raise PinError("malformed input refused (bad JSON): %s (%s)" % (path, exc))


def line_of(text: str, needle: str, occurrence: int = 0) -> int:
    """1-based line number of the nth occurrence of needle; PinError if absent."""
    idx = -1
    for _ in range(occurrence + 1):
        idx = text.find(needle, idx + 1)
        if idx < 0:
            raise PinError("ABSENT: %r not found in source text" % needle)
    return text.count("\n", 0, idx) + 1


def find_floor_row(inventory: dict):
    caves = inventory.get("story_caves")
    if not isinstance(caves, list):
        raise PinError("malformed inventory: story_caves is not a list")
    for cave in caves:
        if not isinstance(cave, dict) or cave.get("id") != CAVE_ID:
            continue
        for row in cave.get("floors", []):
            if isinstance(row, dict) and row.get("first") == FLOOR and row.get("last") == FLOOR:
                return cave, row
        raise PinError("ABSENT: %s has no floor-%d row (reason: floors %s)"
                       % (CAVE_ID, FLOOR, [ (r.get("first"), r.get("last")) for r in cave.get("floors", []) if isinstance(r, dict)]))
    raise PinError("ABSENT: cave %r not in inventory (reason: not a known story cave)" % CAVE_ID)


def parse_enemy_table(text: str) -> dict:
    """Map internal enemy name -> (id, line). Refuses malformed tables."""
    found = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*EnemyID_(\w+)\s*=\s*(\d+)\s*,", line)
        if m:
            found[m.group(1)] = (int(m.group(2)), lineno)
    if not found:
        raise PinError("malformed enemy table: no EnemyID_<Name> = <id> rows")
    return found


def catalog_names(catalogs: dict, key: str) -> dict:
    cat = catalogs.get(key)
    if not isinstance(cat, dict) or not isinstance(cat.get("entries"), list):
        raise PinError("malformed inventory: catalog %r missing entries list" % key)
    out = {}
    for entry in cat["entries"]:
        if not isinstance(entry, dict) or "name" not in entry:
            raise PinError("malformed inventory: nameless entry in catalog %r" % key)
        out[entry["name"]] = entry
    return out


def classify(token: str, enemies: dict, items: dict, treasures: dict) -> dict:
    """Split a compound <Enemy>_<cargo> token against known tables.

    Longest enemy-name prefix wins; the remainder must exist in the item or
    treasure catalog. Anything else is refused fail-closed.
    """
    if not isinstance(token, str) or not token:
        raise PinError("missing token refused (empty/non-string)")
    for enemy in sorted(enemies, key=len, reverse=True):
        if token == enemy:
            eid, eline = enemies[enemy]
            return {"kind": "enemy", "enemy": enemy, "enemy_id": eid,
                    "enemy_line": eline, "cargo": None}
        if token.startswith(enemy + "_"):
            cargo = token[len(enemy) + 1:]
            eid, eline = enemies[enemy]
            if cargo in items:
                return {"kind": "enemy_carried_item", "enemy": enemy,
                        "enemy_id": eid, "enemy_line": eline,
                        "cargo": cargo, "cargo_catalog": "us/runtime/item",
                        "cargo_entry": items[cargo]}
            if cargo in treasures:
                return {"kind": "enemy_carried_treasure", "enemy": enemy,
                        "enemy_id": eid, "enemy_line": eline,
                        "cargo": cargo, "cargo_catalog": "us/runtime/otakara",
                        "cargo_entry": treasures[cargo]}
            raise PinError("unclassifiable cargo refused: %r base enemy %r "
                           "(id %d) is known but qualifier %r is in no item "
                           "or treasure catalog; refusing to invent" % (token, enemy, eid, cargo))
    raise PinError("unclassifiable token refused: %r matches no known enemy id" % token)


def discover(inventory_path: Path, enemyinfo_path: Path) -> dict:
    inventory, inventory_text = load_json(inventory_path)
    try:
        enemyinfo_text = enemyinfo_path.read_bytes().decode("utf-8", errors="replace")
    except OSError as exc:
        raise PinError("missing input refused: %s (%s)" % (enemyinfo_path, exc))
    if not isinstance(inventory, dict) or "story_caves" not in inventory or "catalogs" not in inventory:
        raise PinError("malformed inventory: need story_caves + catalogs")
    cave, row = find_floor_row(inventory)
    if TOKEN not in list(row.get("enemy_ids", [])):
        raise PinError("ABSENT: %r not in %s floor-%d enemy_ids %s (reason: row lists %s)"
                       % (TOKEN, CAVE_ID, FLOOR, row.get("unit_pool"), list(row.get("enemy_ids", []))))
    enemies = parse_enemy_table(enemyinfo_text)
    items = catalog_names(inventory["catalogs"], "us/runtime/item")
    treasures = catalog_names(inventory["catalogs"], "us/runtime/otakara")
    classification = classify(TOKEN, enemies, items, treasures)
    return {
        "token": TOKEN,
        "cave": CAVE_ID,
        "floor": FLOOR,
        "cave_source": cave.get("source"),
        "unit_pool": row.get("unit_pool"),
        "citations": {
            "floor_row": "%s:%d" % (inventory_path.name, line_of(inventory_text, '"%s"' % TOKEN)),
            "cave_source": "%s:%d" % (inventory_path.name, line_of(inventory_text, '"source": "%s"' % cave.get("source"))),
            "unit_pool": "%s:%d" % (inventory_path.name, line_of(inventory_text, '"%s"' % row.get("unit_pool"))),
            "enemy_id": "%s:%d" % (enemyinfo_path.name, classification["enemy_line"]),
            "cargo_entry": "%s:%d" % (inventory_path.name, line_of(inventory_text, '"name": "%s"' % classification["cargo"])),
        },
        "classification": classification,
        "downstream": {"issue": DOWNSTREAM_ISSUE, "lane": DOWNSTREAM_LANE},
    }


def main(argv=None) -> int:
    root = repo_root_from_here()
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 2:
        print("REFUSED: usage: pin_discovery [inventory.json] [enemyInfo.h]")
        return 2
    inv = Path(args[0]) if len(args) >= 1 else root / "docs" / "PIKMIN2_CONTENT_INVENTORY.json"
    einfo = Path(args[1]) if len(args) >= 2 else root / "native" / "pikmin2-research" / "include" / "Game" / "enemyInfo.h"
    try:
        packet = discover(inv, einfo)
    except PinError as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(packet, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

