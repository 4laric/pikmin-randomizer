"""P0 import-contract adapter for P1 Challenge Navel (issue #563).

Lane p1-challenge-navel, generation 3. Concrete source-import preparation
only: no native build, no runtime, no ADMIT, no playability claim. The full
issue #563 stays open for P1/P2.

What this module does (stdlib only, dependency-free pure functions):

- Parses the retail P1 stage definition `stages/chal2.ini`: top-level keys
  (navi_start, map_file, day_multiply) and the dayMgr block with its 5
  timesettings (the five challenge layouts). Malformed input fails closed
  with exact errors.
- Decodes the `1.0v` generator blobs (`default.gen`, `plants.gen`) into
  records (tag, generator id, name, position, type byte) and names enemy
  type bytes against the P1 host TEKI roster where the port documents
  them; unmapped bytes are reported numerically, never guessed.
- Audits resource closure against a supplied asset root: ini plus both gen
  blobs hashed, referenced map file presence-checked, unsupported
  references collected. Nothing is invented when the source is absent:
  `locate_source` returns the exact missing prerequisite instead.
- Keeps the two consumer tracks separate by construction: the adapter only
  reports the shared level identity (`challenge:navel`, area 2); the
  story-destination (#100) versus timed-campaign (#52) split is recorded
  as metadata, never merged.

Level identity constants mirror the #531 lane spec. Timestamps, saves,
checks, travel logic and the timed campaign are explicitly out of scope
(they remain open per the issue) and no placement or spawn is derived here.
"""
import hashlib
import re
import struct
from pathlib import Path

LANE = "p1-challenge-navel"
ISSUE = 563
SOURCE_ID = "navel"
SOURCE_INI = "stages/chal2.ini"
SCHEMA = "p1-challenge-navel-p0/1"
LEVEL_KEY = "challenge:navel"
NATIVE_AREA_ID = 2
STAGE_INFO_INDEX = 18
EXPECTED_TIMESETTINGS = 5

TRACK_STORY_DESTINATION = "Optional story destination #100"
TRACK_TIMED_CAMPAIGN = "Separate timed/scored AP campaign #52"

TEKI_NAMES = {
    0: "Frog", 1: "Iwagen", 2: "Iwagon", 3: "Chappy", 4: "Swallow",
    5: "Mizigen", 6: "Qurione", 7: "Palm", 8: "Collec", 9: "Kinoko",
    10: "Shell", 11: "Napkid", 12: "Hollec", 13: "Pearl", 14: "Rocpe",
    15: "Tank", 16: "Mar", 17: "Beatle", 18: "KabekuiA", 19: "KabekuiB",
    20: "KabekuiC", 21: "Tamago", 22: "Dororo", 23: "HibaA", 24: "Miurin",
    25: "Otama", 30: "Namazu", 31: "Chappb", 32: "Swallob", 33: "Frow",
}

GEN_FILES = ("default.gen", "plants.gen")


def _day_mgr_body(text):
    match = re.search(r"dayMgr\s*\{", text)
    if not match:
        raise ValueError("stage ini has no dayMgr block")
    depth = 0
    cursor = match.end() - 1
    while cursor < len(text):
        char = text[cursor]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[match.end():cursor]
        cursor += 1
    raise ValueError("unbalanced dayMgr block")


def parse_stage_ini(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("stage ini is empty")
    keys = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if "{" in stripped or "}" in stripped:
            continue
        head = stripped.split()
        if len(head) >= 2:
            keys.setdefault(head[0], head[1:])
    body = _day_mgr_body(text)
    settings = re.search(r"numsettings\s+(\d+)", body)
    if not settings:
        raise ValueError("dayMgr has no numsettings")
    count = int(settings.group(1))
    found = len(re.findall(r"timesetting\s+\d+", body))
    if found != count:
        raise ValueError("timesetting block count mismatch")
    return {
        "keys": keys,
        "numsettings": count,
        "timesettings": count,
        "map_file": (keys.get("map_file") or [None])[0],
        "navi_start": keys.get("navi_start"),
        "day_multiply": keys.get("day_multiply"),
    }


def decode_generators(blob):
    if not isinstance(blob, (bytes, bytearray)) or bytes(blob)[:4] != b"1.0v":
        raise ValueError("expected v0.1 generator blob")
    if len(blob) < 24:
        raise ValueError("truncated generator header")
    count = struct.unpack_from(">I", bytes(blob), 20)[0]
    starts = [m.start() for m in re.finditer(b"    0.0v", bytes(blob))]
    if not starts or starts[0] != 24 or len(starts) != count:
        raise ValueError("generator record framing mismatch")
    records = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(blob)
        row = bytes(blob[start:end])
        tag = row[72:76].decode("ascii", errors="replace")
        typed = row[80] if len(row) > 80 else None
        records.append({
            "generator": struct.unpack_from("<I", row, 8)[0],
            "name": row[16:48].split(b"\x00")[0].decode("ascii", errors="replace"),
            "tag": tag,
            "type_byte": typed,
            "teki": TEKI_NAMES.get(typed) if tag == "iket" else None,
        })
    return records


def _sha256(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def locate_source(asset_roots):
    for root in asset_roots or []:
        candidate = Path(root) / "dataDir" / SOURCE_INI
        if candidate.is_file():
            return {"available": True, "root": str(Path(root)),
                    "ini": str(candidate), "prerequisite": None}
    return {"available": False, "root": None, "ini": None,
            "prerequisite": "Retail P1 asset tree holding dataDir/%s "
                            "(read-only input; no asset redistribution)."
                            % SOURCE_INI}


def audit_level(assets_root):
    found = locate_source([assets_root])
    if not found["available"]:
        raise ValueError(found["prerequisite"])
    root = Path(found["root"])
    ini_path = root / "dataDir" / SOURCE_INI
    ini_bytes = ini_path.read_bytes()
    try:
        ini_text = ini_bytes.decode("utf-8")
    except UnicodeDecodeError:
        ini_text = ini_bytes.decode("shift_jis")
    ini = parse_stage_ini(ini_text)
    if ini["timesettings"] != EXPECTED_TIMESETTINGS:
        raise ValueError("expected %d timesettings, found %d"
                         % (EXPECTED_TIMESETTINGS, ini["timesettings"]))
    stage_dir = root / "dataDir" / "stages" / "chal2"
    gens = {}
    for name in GEN_FILES:
        path = stage_dir / name
        if not path.is_file():
            raise ValueError("missing generator blob: %s" % name)
        gens[name] = decode_generators(path.read_bytes())
    map_path = root / "dataDir" / (ini["map_file"] or "")
    unsupported = []
    if not ini["map_file"] or not map_path.is_file():
        unsupported.append("map file missing: %r" % (ini["map_file"],))
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "source_id": SOURCE_ID,
        "level_key": LEVEL_KEY,
        "native_area_id": NATIVE_AREA_ID,
        "stage_info_index": STAGE_INFO_INDEX,
        "tracks": [TRACK_STORY_DESTINATION, TRACK_TIMED_CAMPAIGN],
        "source_path": SOURCE_INI,
        "hashes": {
            "stages/chal2.ini": _sha256(ini_path),
            "stages/chal2/default.gen": _sha256(stage_dir / "default.gen"),
            "stages/chal2/plants.gen": _sha256(stage_dir / "plants.gen"),
        },
        "ini": {
            "bytes": len(ini_bytes),
            "timesettings": ini["timesettings"],
            "navi_start": ini["navi_start"],
            "map_file": ini["map_file"],
            "day_multiply": ini["day_multiply"],
        },
        "generators": {
            name: {"records": len(records),
                   "by_tag": {tag: sum(1 for r in records if r["tag"] == tag)
                              for tag in sorted({r["tag"] for r in records})}}
            for name, records in gens.items()
        },
        "enemy_types": sorted(
            {r["type_byte"] for r in gens["default.gen"] if r["tag"] == "iket"}),
        "map_present": not unsupported,
        "unsupported": unsupported,
        "generated": False,
        "limitations": [
            "Timesettings are day-phase layouts, not spawn instances or placements.",
            "Travel/save/check logic and the timed AP campaign are open per the issue.",
            "No Pikmin counts, scores, retries or remote-upgrade behavior derived.",
        ],
    }
