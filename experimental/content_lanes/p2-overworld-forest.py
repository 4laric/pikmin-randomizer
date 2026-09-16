"""P0 source-audit adapter for Awakening Wood (p2-overworld-forest, #149).

Concrete source-import preparation only. Reuses the existing
``stage_cave_links`` parser (no fork); never emits runtime placements.
Metadata already catalogued in docs/PIKMIN2_CONTENT_INVENTORY.json is treated
as baseline, not reimplemented. If ``user/Abe/stages.txt`` bytes are absent,
callers get the exact missing prerequisite instead of invented values.
"""

import hashlib
import json
from pathlib import Path

from experimental.pikmin2_regional_audit import stage_cave_links

SOURCE_PATH = "user/Abe/stages.txt"
COURSE = "forest"
LABEL = "Awakening Wood"
ISSUE = 149

REQUIRED_INVENTORY = (
    "terrain/collision/water",
    "generator day schedules and regrowth",
    "buried/enemy-held treasure",
    "Onions/ship/bridges/gates",
    "all cave entrances and return anchors",
)

# Runtime framework contracts that block P1/P2 (issue refs from the lane
# entry). P0 resolves none of them; they are reported, not claimed.
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
    "bytes to decode_forest(); nothing is staged from weighted definitions."
)


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("source bytes required")
    return hashlib.sha256(bytes(data)).hexdigest()


def decode_forest(stages_text):
    """Decode stages.txt text and return forest cave links.

    Reuses the existing parser (framing, counts, tag/filename validation).
    Raises ValueError on malformed input or when the forest course is absent.
    Returns links sorted by cave_table_index with original fields preserved.
    """
    if not isinstance(stages_text, str) or not stages_text.strip():
        raise ValueError("stages.txt text is missing or empty")
    links = stage_cave_links(stages_text)
    forest = [dict(link) for link in links if link.get("course_id") == COURSE]
    if not forest:
        raise ValueError("forest course missing from stages.txt")
    forest.sort(key=lambda link: link.get("cave_table_index", 0))
    return forest


def resource_closure(forest_links, stages_sha256=None, cave_hashes=None):
    """List every source file this entry needs, with hashes where known."""
    cave_hashes = dict(cave_hashes or {})
    closure = [dict(path=SOURCE_PATH, sha256=stages_sha256,
                    status="hashed" if stages_sha256 else "hash_unvalidated")]
    for link in forest_links:
        path = link["source_path"]
        digest = cave_hashes.get(path)
        closure.append(dict(path=path, sha256=digest,
                            status="hashed" if digest else "hash_unvalidated"))
    return closure


def build_manifest(stages_text, stages_sha256=None, cave_hashes=None):
    """Build the isolated P0 metadata packet for the forest course."""
    forest = decode_forest(stages_text)
    if stages_sha256 is not None:
        if not isinstance(stages_sha256, str) or len(stages_sha256) != 64:
            raise ValueError("stages_sha256 must be 64 hex chars")
    manifest = dict(
        schema=1,
        lane="p2-overworld-forest",
        course=COURSE,
        label=LABEL,
        issue=ISSUE,
        source=SOURCE_PATH,
        stages_sha256=stages_sha256,
        cave_count=len(forest),
        cave_links=[dict(link) for link in forest],
        required_inventory=[dict(item=item, status="baseline_catalogued")
                            for item in REQUIRED_INVENTORY],
        resource_closure=resource_closure(forest, stages_sha256, cave_hashes),
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
        raise ValueError("manifest needs at least one forest cave link")
    seen = set()
    for link in links:
        if link.get("course_id") != COURSE:
            raise ValueError("non-forest link in forest manifest")
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
