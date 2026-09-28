"""P0 import-contract adapter for p1-challenge-spring (lane p1-challenge-spring, #566).

Isolated P1 Challenge source contract. Reads the P1 stage-info table
(dataDir/stages/stages.ini) and the Spring challenge stage definition
(dataDir/stages/chal3.ini) from a local legal asset tree, decodes both
with a small local tokenizer that follows the engine's own field names
(engine/src/plugPikiColin/game.cpp parses stages.ini new_map blocks;
newPikiGame.cpp createMapObjects reads map_file, day_multiply and
dayMgr), reuses experimental.levels for the level-key to area mapping,
and validates against the catalogued contract: stage_info_index 19 is
Challenge 3, id 3, chid 3, file stages/chal3.ini; level_key
challenge:spring; native_area_id 3.

No preview/runtime is started, no placements are emitted, and no shared
file is edited. Fail-closed: absent inputs raise FileNotFoundError,
malformed definitions and unknown top-level keys raise ValueError,
contract drift is reported as mismatches.
"""
from pathlib import Path

from experimental.levels import BY_KEY

LANE = "p1-challenge-spring"
LEVEL_KEY = "challenge:spring"
NATIVE_AREA_ID = 3
STAGE_INFO_INDEX = 19
STAGE_INFO_TABLE = "dataDir/stages/stages.ini"
STAGE_INI = "dataDir/stages/chal3.ini"
STAGE_NAME = "Challenge 3"
STAGE_ID = 3
STAGE_CHAL_ID = 3
STAGE_FILE = "stages/chal3.ini"
EXPECTED_GEOMETRY = "courses/stage3/yakusima.mod"
EXPECTED_NAVI_START = (0.0, 0.0)
EXPECTED_DAY_MULTIPLY = 1.4
EXPECTED_NUMSETTINGS = 5
EXPECTED_TIMESETTING_LABELS = ("night", "morning", "day", "evening", "movie")
EXPECTED_NEW_ROOM = {"index": 0, "radius": 4.0, "centre": (0.0, 0.0)}
GEN_SUFFIX = ".gen"


def _tokens(text):
    """Tokenize a P1 ini/CmdStream text: strip // comments, split braces."""
    out = []
    for line in text.splitlines():
        line = line.split("//")[0]
        i = 0
        while i < len(line):
            ch = line[i]
            if ch.isspace():
                i += 1
                continue
            if ch in "{}":
                out.append(ch)
                i += 1
                continue
            if ch in ('"', "'"):
                j = line.find(ch, i + 1)
                if j < 0:
                    raise ValueError("Unterminated quoted string")
                out.append(line[i + 1:j])
                i = j + 1
                continue
            j = i
            while j < len(line) and not line[j].isspace() and line[j] not in '{}"':
                j += 1
            out.append(line[i:j])
            i = j
    return out


def _float(token, what):
    try:
        value = float(token)
    except (TypeError, ValueError):
        raise ValueError("Malformed numeric field: " + what)
    if value != value:
        raise ValueError("Invalid numeric field: " + what)
    return value


def _expect(tokens, pos, token):
    if pos >= len(tokens) or tokens[pos] != token:
        got = tokens[pos] if pos < len(tokens) else "EOF"
        raise ValueError("Expected " + token + ", got " + got)
    return pos + 1


def parse_stage_table(text):
    """Decode dataDir/stages/stages.ini into ordered new_map records.

    Mirrors engine/src/plugPikiColin/game.cpp: each new_map token opens a
    record at an incrementing mStageIndex, followed by a visibility token
    and a brace block carrying name, id, chid, file and an optional
    generator block. Challenge records carry chid; campaign records carry
    a generator block.
    """
    tokens = _tokens(text)
    pos, records = 0, []
    while pos < len(tokens):
        if tokens[pos] != "new_map":
            pos += 1
            continue
        pos += 1
        if pos >= len(tokens):
            raise ValueError("Truncated new_map header")
        visible = tokens[pos] == "visible"
        pos += 1
        pos = _expect(tokens, pos, "{")
        record = {"index": len(records), "visible": visible, "name": None,
                  "id": None, "chal_id": None, "file": None, "generators": []}
        while pos < len(tokens) and tokens[pos] != "}":
            key = tokens[pos]
            pos += 1
            if key == "name":
                if pos >= len(tokens):
                    raise ValueError("Truncated name field")
                record["name"] = tokens[pos]
                pos += 1
            elif key == "id":
                if pos >= len(tokens):
                    raise ValueError("Truncated id field")
                record["id"] = int(_float(tokens[pos], "id"))
                pos += 1
            elif key == "chid":
                if pos >= len(tokens):
                    raise ValueError("Truncated chid field")
                record["chal_id"] = int(_float(tokens[pos], "chid"))
                pos += 1
            elif key == "file":
                if pos >= len(tokens):
                    raise ValueError("Truncated file field")
                record["file"] = tokens[pos]
                pos += 1
            elif key == "generator":
                pos = _expect(tokens, pos, "{")
                while pos < len(tokens) and tokens[pos] != "}":
                    if tokens[pos] != "genfile":
                        raise ValueError("Unknown generator key: " + tokens[pos])
                    if pos + 4 >= len(tokens):
                        raise ValueError("Truncated genfile row")
                    record["generators"].append({
                        "name": tokens[pos + 1],
                        "first": int(_float(tokens[pos + 2], "genfile first")),
                        "last": int(_float(tokens[pos + 3], "genfile last")),
                        "total": int(_float(tokens[pos + 4], "genfile total")),
                    })
                    pos += 5
                pos = _expect(tokens, pos, "}")
            else:
                raise ValueError("Unknown stage-table key: " + key)
        pos = _expect(tokens, pos, "}")
        records.append(record)
    if not records:
        raise ValueError("No new_map records in stage table")
    return records


def _light_block(tokens, pos):
    fields = {"type": None, "attach": None, "fov": None, "position": None,
              "direction": None, "colour": None}
    while pos < len(tokens) and tokens[pos] != "}":
        key = tokens[pos]
        pos += 1
        if key == "colour":
            if pos + 4 > len(tokens):
                raise ValueError("Truncated light colour")
            fields["colour"] = [int(_float(t, "colour")) for t in tokens[pos:pos + 4]]
            pos += 4
        elif key == "position":
            if pos + 3 > len(tokens):
                raise ValueError("Truncated light position")
            fields["position"] = [_float(t, "position") for t in tokens[pos:pos + 3]]
            pos += 3
        elif key == "direction":
            if pos + 3 > len(tokens):
                raise ValueError("Truncated light direction")
            fields["direction"] = [_float(t, "direction") for t in tokens[pos:pos + 3]]
            pos += 3
        elif key in ("type", "attach", "fov"):
            if pos >= len(tokens):
                raise ValueError("Truncated light field: " + key)
            fields[key] = _float(tokens[pos], key)
            pos += 1
        else:
            raise ValueError("Unknown light key: " + key)
    pos = _expect(tokens, pos, "}")
    if fields["type"] is None or fields["attach"] is None or fields["colour"] is None:
        raise ValueError("Incomplete light block")
    return fields, pos


def _timesetting_block(tokens, pos):
    pos = _expect(tokens, pos, "timesetting")
    if pos >= len(tokens):
        raise ValueError("Truncated timesetting")
    index = int(_float(tokens[pos], "timesetting index"))
    pos += 1
    pos = _expect(tokens, pos, "{")
    lights, ambient, fog = [], None, None
    while pos < len(tokens) and tokens[pos] != "}":
        key = tokens[pos]
        pos += 1
        if key == "light":
            if pos >= len(tokens):
                raise ValueError("Truncated light index")
            light_index = int(_float(tokens[pos], "light index"))
            pos += 1
            pos = _expect(tokens, pos, "{")
            fields, pos = _light_block(tokens, pos)
            fields["index"] = light_index
            lights.append(fields)
        elif key == "ambient":
            pos = _expect(tokens, pos, "{")
            ambient = {}
            while pos < len(tokens) and tokens[pos] != "}":
                if tokens[pos] != "colour":
                    raise ValueError("Unknown ambient key: " + tokens[pos])
                pos += 1
                if pos + 4 > len(tokens):
                    raise ValueError("Truncated ambient colour")
                ambient["colour"] = [int(_float(t, "ambient colour")) for t in tokens[pos:pos + 4]]
                pos += 4
            pos = _expect(tokens, pos, "}")
        elif key == "fog":
            pos = _expect(tokens, pos, "{")
            fog = {}
            while pos < len(tokens) and tokens[pos] != "}":
                if tokens[pos] == "colour":
                    if pos + 5 > len(tokens):
                        raise ValueError("Truncated fog colour")
                    fog["colour"] = [int(_float(t, "fog colour")) for t in tokens[pos + 1:pos + 5]]
                    pos += 5
                elif tokens[pos] == "dist":
                    if pos + 3 > len(tokens):
                        raise ValueError("Truncated fog dist")
                    fog["dist"] = [_float(t, "fog dist") for t in tokens[pos + 1:pos + 3]]
                    pos += 3
                else:
                    raise ValueError("Unknown fog key: " + tokens[pos])
            pos = _expect(tokens, pos, "}")
        else:
            raise ValueError("Unknown timesetting key: " + key)
    pos = _expect(tokens, pos, "}")
    if ambient is None or fog is None or not lights:
        raise ValueError("Incomplete timesetting block")
    return {"index": index, "lights": lights, "ambient": ambient, "fog": fog}, pos


def parse_stage_ini(text):
    """Decode dataDir/stages/chal3.ini into a structured stage definition."""
    tokens = _tokens(text)
    pos = 0
    result = {"navi_start": None, "map_file": None, "day_multiply": None,
              "numsettings": None, "timesettings": [], "new_rooms": []}
    while pos < len(tokens):
        key = tokens[pos]
        pos += 1
        if key == "navi_start":
            if pos + 2 > len(tokens):
                raise ValueError("Truncated navi_start")
            result["navi_start"] = tuple(_float(t, "navi_start") for t in tokens[pos:pos + 2])
            pos += 2
        elif key == "map_file":
            if pos >= len(tokens):
                raise ValueError("Truncated map_file")
            result["map_file"] = tokens[pos]
            pos += 1
        elif key == "day_multiply":
            if pos >= len(tokens):
                raise ValueError("Truncated day_multiply")
            result["day_multiply"] = _float(tokens[pos], "day_multiply")
            pos += 1
        elif key == "dayMgr":
            pos = _expect(tokens, pos, "{")
            if pos >= len(tokens) or tokens[pos] != "numsettings":
                raise ValueError("Missing dayMgr numsettings")
            pos += 1
            if pos >= len(tokens):
                raise ValueError("Truncated numsettings")
            count = int(_float(tokens[pos], "numsettings"))
            pos += 1
            if count < 0 or count > 32:
                raise ValueError("Unreasonable numsettings")
            result["numsettings"] = count
            for _ in range(count):
                block, pos = _timesetting_block(tokens, pos)
                result["timesettings"].append(block)
            pos = _expect(tokens, pos, "}")
        elif key == "new_room":
            pos = _expect(tokens, pos, "{")
            room = {"index": None, "radius": None, "centre": None}
            while pos < len(tokens) and tokens[pos] != "}":
                sub = tokens[pos]
                pos += 1
                if sub == "index":
                    room["index"] = int(_float(tokens[pos], "room index"))
                    pos += 1
                elif sub == "radius":
                    room["radius"] = _float(tokens[pos], "room radius")
                    pos += 1
                elif sub == "centre":
                    room["centre"] = tuple(_float(t, "room centre") for t in tokens[pos:pos + 2])
                    pos += 2
                else:
                    raise ValueError("Unknown new_room key: " + sub)
            pos = _expect(tokens, pos, "}")
            if room["index"] is None or room["radius"] is None or room["centre"] is None:
                raise ValueError("Incomplete new_room block")
            result["new_rooms"].append(room)
        else:
            raise ValueError("Unknown top-level stage key: " + key)
    return result


def read_asset(assets, rel):
    """Read one asset file; missing inputs fail closed."""
    path = Path(assets) / rel
    if not path.is_file():
        raise FileNotFoundError("Missing asset: " + rel)
    return path.read_bytes()


def _timesetting_label(text, index):
    """Recover the source comment label for one timesetting block."""
    prefix = "timesetting " + str(index)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix) and stripped[len(prefix):len(prefix) + 1] in (" ", chr(9)):
            if "//" in line:
                return line.split("//", 1)[1].strip()
            return None
    return None


def decode(assets):
    """Decode the stage table and the Spring challenge stage definition."""
    import hashlib
    table_blob = read_asset(assets, STAGE_INFO_TABLE)
    ini_blob = read_asset(assets, STAGE_INI)
    table_text = table_blob.decode("shift_jis", errors="replace")
    ini_text = ini_blob.decode("shift_jis", errors="replace")
    table = parse_stage_table(table_text)
    stage = parse_stage_ini(ini_text)
    labels = [_timesetting_label(ini_text, block["index"]) for block in stage["timesettings"]]
    hashes = {
        STAGE_INFO_TABLE: hashlib.sha256(table_blob).hexdigest(),
        STAGE_INI: hashlib.sha256(ini_blob).hexdigest(),
    }
    return {"table": table, "stage": stage, "labels": labels, "hashes": hashes}


def check_contract(table, stage, labels):
    """Validate the catalogued contract; return mismatch strings."""
    mismatches = []
    level = BY_KEY.get(LEVEL_KEY)
    if level is None:
        mismatches.append("catalogued level missing: " + LEVEL_KEY)
    else:
        if level.area_id != NATIVE_AREA_ID:
            mismatches.append("level area_id %r, expected %d" % (level.area_id, NATIVE_AREA_ID))
        if level.stage_file != STAGE_FILE:
            mismatches.append("level stage_file %r, expected %s" % (level.stage_file, STAGE_FILE))
    if STAGE_INFO_INDEX >= len(table):
        mismatches.append("stage table has %d records, expected index %d"
                          % (len(table), STAGE_INFO_INDEX))
        return mismatches
    record = table[STAGE_INFO_INDEX]
    for field, want in (("name", STAGE_NAME), ("id", STAGE_ID),
                        ("chal_id", STAGE_CHAL_ID), ("file", STAGE_FILE),
                        ("visible", True), ("generators", [])):
        if record[field] != want:
            mismatches.append("stage_info[%d].%s is %r, expected %r"
                              % (STAGE_INFO_INDEX, field, record[field], want))
    if stage["navi_start"] != EXPECTED_NAVI_START:
        mismatches.append("navi_start is %r, expected %r"
                          % (stage["navi_start"], EXPECTED_NAVI_START))
    if stage["map_file"] != EXPECTED_GEOMETRY:
        mismatches.append("map_file is %r, expected %s"
                          % (stage["map_file"], EXPECTED_GEOMETRY))
    if stage["day_multiply"] != EXPECTED_DAY_MULTIPLY:
        mismatches.append("day_multiply is %r, expected %r"
                          % (stage["day_multiply"], EXPECTED_DAY_MULTIPLY))
    if stage["numsettings"] != EXPECTED_NUMSETTINGS:
        mismatches.append("numsettings is %r, expected %d"
                          % (stage["numsettings"], EXPECTED_NUMSETTINGS))
    if len(stage["timesettings"]) != EXPECTED_NUMSETTINGS:
        mismatches.append("decoded timesettings %d, expected %d"
                          % (len(stage["timesettings"]), EXPECTED_NUMSETTINGS))
    if tuple(labels) != EXPECTED_TIMESETTING_LABELS:
        mismatches.append("timesetting labels %r, expected %r"
                          % (labels, list(EXPECTED_TIMESETTING_LABELS)))
    if len(stage["new_rooms"]) != 1:
        mismatches.append("new_room count %d, expected 1" % len(stage["new_rooms"]))
    else:
        room = stage["new_rooms"][0]
        for field in ("index", "radius", "centre"):
            if room[field] != EXPECTED_NEW_ROOM[field]:
                mismatches.append("new_room.%s is %r, expected %r"
                                  % (field, room[field], EXPECTED_NEW_ROOM[field]))
    return mismatches


def check_closure(assets, stage):
    """Resource closure for the stage: geometry plus generator files."""
    missing = []
    geometry = Path(assets) / "dataDir" / stage["map_file"]
    if not geometry.is_file():
        missing.append(stage["map_file"])
    directory = Path(assets) / "dataDir" / "stages" / "chal3"
    for name in ("default.gen", "plants.gen"):
        if not (directory / name).is_file():
            missing.append("dataDir/stages/chal3/" + name)
    return sorted(missing)


def generator_hashes(assets):
    """sha256 of every generator file in the stage directory."""
    import hashlib
    directory = Path(assets) / "dataDir" / "stages" / "chal3"
    result = {}
    for path in sorted(directory.glob("*" + GEN_SUFFIX)):
        result["dataDir/stages/chal3/" + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def build_packet(level, table, stage, labels, hashes, generators, mismatches,
                 missing):
    """Assemble the P0 metadata packet (definitions only, never runtime)."""
    record = table[STAGE_INFO_INDEX] if STAGE_INFO_INDEX < len(table) else None
    return {
        "schema": 1, "lane": LANE,
        "level_key": LEVEL_KEY, "native_area_id": NATIVE_AREA_ID,
        "stage_info_index": STAGE_INFO_INDEX,
        "stage_info_table": STAGE_INFO_TABLE,
        "stage_ini": STAGE_INI,
        "stage_record": record,
        "navi_start": list(stage["navi_start"]) if stage["navi_start"] else None,
        "map_file": stage["map_file"],
        "day_multiply": stage["day_multiply"],
        "numsettings": stage["numsettings"],
        "timesetting_labels": labels,
        "timesettings": stage["timesettings"],
        "new_rooms": [{"index": r["index"], "radius": r["radius"],
                       "centre": list(r["centre"])} for r in stage["new_rooms"]],
        "source_sha256": hashes,
        "generator_sha256": generators,
        "contract_mismatches": mismatches,
        "missing_closure": missing,
        "tracks": [
            "Story destination contract #100 (shared area id 3 must stay qualified by level key).",
            "Timed/scored AP campaign contract #52 (separate mode and check surface).",
        ],
        "blockers": [
            "P1 runtime import needs the existing framework owners #52 "
            "(timed AP campaign), #100 (story destinations) and #6.",
            "Preview-only startup evidence already exists for all five "
            "layouts and is deliberately not repeated; travel/save/check "
            "logic remains unproven.",
        ],
        "generated": False,
        "limitations": [
            "Stage definitions only: no geometry, actor, route or timer run.",
            "No placements or completion state are produced from this metadata.",
        ],
    }


def run(assets, output_dir):
    """End-to-end P0 slice: read, decode, validate, write packet.json."""
    import json
    assets = Path(assets)
    decoded = decode(assets)
    mismatches = check_contract(decoded["table"], decoded["stage"], decoded["labels"])
    missing = check_closure(assets, decoded["stage"])
    generators = generator_hashes(assets)
    level = BY_KEY.get(LEVEL_KEY)
    packet = build_packet(level, decoded["table"], decoded["stage"],
                          decoded["labels"], decoded["hashes"], generators,
                          mismatches, missing)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "packet.json").write_text(json.dumps(packet, indent=2) + "\n",
                                            encoding="utf-8")
    return packet