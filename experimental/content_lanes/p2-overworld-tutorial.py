"""P0 source-audit adapter for Valley of Repose (p2-overworld-tutorial, #148).

Concrete source-import preparation only. Reuses the existing
``stage_cave_links`` parser (no fork); never emits runtime placements.
Metadata already catalogued in docs/PIKMIN2_CONTENT_INVENTORY.json is treated
as baseline, not reimplemented. If ``user/Abe/stages.txt`` bytes are absent,
callers get the exact missing prerequisite instead of invented values.

The tutorial course carries three cave links (t_01..t_03, sibling shard
caves-tutorial) plus one `test` row pointing at caveinfo.txt; all four are
decoded and recorded, none omitted.
"""
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_regional_audit import stage_cave_links

SOURCE_PATH = "user/Abe/stages.txt"
COURSE = "tutorial"
LABEL = "Valley of Repose"
ISSUE = 148

REQUIRED_INVENTORY = (
    "terrain/collision/water",
    "generator day schedules and regrowth",
    "buried/enemy-held treasure",
    "Onions/ship/bridges/gates",
    "all cave entrances and return anchors",
)

BLOCKERS = (
    {"issue": 128, "contract": "actor/asset source closure"},
    {"issue": 130, "contract": "actor/asset source closure"},
    {"issue": 131, "contract": "actor/asset source closure"},
    {"issue": 132, "contract": "surface days, saves and progression identity"},
    {"issue": 140, "contract": "actor/asset/species source closure"},
    {"issue": 144, "contract": "actor/asset/species source closure"},
    {"issue": 145, "contract": "actor/asset/species source closure"},
    {"issue": 146, "contract": "actor/asset/species source closure"},
)

MISSING_PREREQUISITE = (
    "Legal US Pikmin 2 disc image (GPVE01 rev 0) or an extracted "
    "'user/Abe/stages.txt' file decoded as shift_jis. Provide the file "
    "bytes to decode_tutorial(); nothing is staged from weighted definitions."
)


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("source bytes required")
    return hashlib.sha256(bytes(data)).hexdigest()


def decode_tutorial(stages_text):
    if not isinstance(stages_text, str) or not stages_text.strip():
        raise ValueError("stages.txt text is missing or empty")
    links = stage_cave_links(stages_text)
    tutorial = [dict(link) for link in links if link.get("course_id") == COURSE]
    if not tutorial:
        raise ValueError("tutorial course missing from stages.txt")
    tutorial.sort(key=lambda link: link.get("cave_table_index", 0))
    return tutorial


def resource_closure(tutorial_links, stages_sha256=None, cave_hashes=None):
    cave_hashes = dict(cave_hashes or {})
    closure = [dict(path=SOURCE_PATH, sha256=stages_sha256,
                    status="hashed" if stages_sha256 else "hash_unvalidated")]
    for link in tutorial_links:
        path = link["source_path"]
        digest = cave_hashes.get(path)
        closure.append(dict(path=path, sha256=digest,
                            status="hashed" if digest else "hash_unvalidated"))
    return closure


def build_manifest(stages_text, stages_sha256=None, cave_hashes=None):
    tutorial = decode_tutorial(stages_text)
    if stages_sha256 is not None:
        if not isinstance(stages_sha256, str) or len(stages_sha256) != 64:
            raise ValueError("stages_sha256 must be 64 hex chars")
    manifest = dict(
        schema=1,
        lane="p2-overworld-tutorial",
        course=COURSE,
        label=LABEL,
        issue=ISSUE,
        source=SOURCE_PATH,
        stages_sha256=stages_sha256,
        cave_count=len(tutorial),
        cave_links=[dict(link) for link in tutorial],
        required_inventory=[dict(item=item, status="baseline_catalogued")
                            for item in REQUIRED_INVENTORY],
        resource_closure=resource_closure(tutorial, stages_sha256, cave_hashes),
        blockers=[dict(entry) for entry in BLOCKERS],
        placement_policy=("no runtime placements emitted; weighted definitions "
                          "stay source data, never actor counts"),
        playable=False,
    )
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a dict")
    if manifest.get("schema") != 1:
        raise ValueError("unsupported manifest schema")
    if manifest.get("course") != COURSE or manifest.get("source") != SOURCE_PATH:
        raise ValueError("manifest course/source mismatch")
    links = manifest.get("cave_links")
    if not isinstance(links, list) or not links:
        raise ValueError("manifest needs at least one tutorial cave link")
    seen = set()
    for link in links:
        if link.get("course_id") != COURSE:
            raise ValueError("non-tutorial link in tutorial manifest")
        tag = link.get("cave_tag")
        path = link.get("source_path")
        if not tag or not path:
            raise ValueError("cave link missing tag/path")
        if tag in seen:
            raise ValueError("duplicate cave tag in manifest")
        seen.add(tag)
        if not path.startswith("user/Mukki/mapunits/caveinfo/"):
            raise ValueError("unexpected cave source path: " + str(path))
    if manifest.get("cave_count") != len(links):
        raise ValueError("cave_count disagrees with cave_links")
    inventory = manifest.get("required_inventory")
    if [row.get("item") for row in inventory] != list(REQUIRED_INVENTORY):
        raise ValueError("required_inventory mismatch")
    if manifest.get("playable") is not False:
        raise ValueError("P0 manifest must not claim playability")
    return True


DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")


def locate_source(iso_path=None):
    iso = Path(iso_path) if iso_path is not None else DEFAULT_ISO
    if not iso.is_file():
        return {"available": False, "iso": None,
                "prerequisite": MISSING_PREREQUISITE}
    return {"available": True, "iso": str(iso), "prerequisite": None}


def decode_source_file(path):
    raw = Path(path).read_bytes()
    return build_manifest(raw.decode("shift_jis"), sha256_bytes(raw))


def missing_prerequisite():
    return MISSING_PREREQUISITE


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stages", type=Path, default=None,
                        help="path to extracted user/Abe/stages.txt")
    parser.add_argument("--output", type=Path, default=None,
                        help="write manifest JSON here (otherwise stdout)")
    args = parser.parse_args(argv)
    if args.stages is None:
        raise SystemExit("missing prerequisite: " + MISSING_PREREQUISITE)
    raw = args.stages.read_bytes()
    text = raw.decode("shift_jis")
    manifest = build_manifest(text, sha256_bytes(raw))
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
