"""Pose density of a prepared P2 content root, and the "is this cache dense" policy (#970).

#943/#950 raised the extraction default to ``DEFAULT_POSE_LIMIT`` (24) baked
poses per clip. Content roots and per-enum cache entries extracted before that
hold 3-12 poses per clip, and the loaders accept them silently, so a smoke
package built from a stale cache plays with visibly choppy animation. This
module gives the smoke and dev tooling one place to decide:

* ``prepared.json`` at a content root records the ``pose_limit`` it was
  extracted with (``p2_prepare_content.prepare_content_root``).
* A per-enum entry copied into a reusable cache carries a ``density.json``
  sidecar (``write_entry_marker``) with that limit.
* ``entry_is_dense`` accepts an entry only when one of those records says the
  limit was at least ``DEFAULT_POSE_LIMIT``. Anything else is sparse/unknown.

CLI: ``py -3.12 scripts/p2_content_density.py <content-root> [--markdown|--json]``
prints measured poses per clip per species (files named ``<stem>_<NN>.mod``).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental.pikmin2_animation import DEFAULT_POSE_LIMIT  # noqa: E402

MARKER = "density.json"

# Converter revisions a cache entry must carry (#960). Pose density alone does not
# say which converter wrote the bake: the dense cache built before #973 still held
# Jellyfloat meshes whose alpha-blended bell wrote depth and drew in the opaque
# pass, so the Onion beam and the carry numbers were hidden behind them. A species
# listed here is reused only when its marker records every listed revision;
# otherwise it is re-extracted like a sparse entry.
TRANSLUCENT_REVISION = "translucent-973"
# #972: Jellyfloat entries carry the sampled pose bank (<clip>_<NN>.mod + per-pose
# Proom rows) beside the static fallback visuals; an entry extracted before it
# animates from one static mesh per clip.
BANK_REVISION = "bank-972"
REQUIRED_REVISIONS = {
    "Kurage": (TRANSLUCENT_REVISION, BANK_REVISION),
    "OniKurage": (TRANSLUCENT_REVISION, BANK_REVISION),
    "MiniHoudai": (TRANSLUCENT_REVISION,),
}
POSE_RE = re.compile(r"^(?P<stem>.+)_(?P<idx>\d+)\.mod$")


def prepared_summary(root):
    path = Path(root) / "prepared.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def root_pose_limit(root):
    """The pose limit a content root was prepared with, or None if unrecorded."""
    summary = prepared_summary(root)
    limit = summary.get("pose_limit") if summary else None
    return limit if type(limit) is int else None


def write_entry_marker(entry_dir, pose_limit, source=None, revisions=None):
    """Record the extraction pose limit (and converter revisions) inside a cache entry.
    ``revisions`` defaults to every revision the species requires: the entry was
    just extracted with the current converter."""
    if revisions is None:
        revisions = REQUIRED_REVISIONS.get(Path(entry_dir).name, ())
    payload = {"pose_limit": int(pose_limit), "source": source, "revisions": sorted(revisions)}
    (Path(entry_dir) / MARKER).write_text(json.dumps(payload) + "\n", encoding="utf-8")


def entry_pose_limit(cache_dir, enum):
    """Pose limit recorded for ``cache_dir/enum`` (entry marker first, then the
    cache root's prepared.json when it lists the enum), or None."""
    cache_dir = Path(cache_dir)
    marker = cache_dir / enum / MARKER
    if marker.is_file():
        try:
            limit = json.loads(marker.read_text(encoding="utf-8")).get("pose_limit")
        except (OSError, ValueError, AttributeError):
            limit = None
        if type(limit) is int:
            return limit
    summary = prepared_summary(cache_dir)
    if summary and enum in (summary.get("extracted_enums") or []):
        limit = summary.get("pose_limit")
        if type(limit) is int:
            return limit
    return None


def entry_is_dense(cache_dir, enum, required=DEFAULT_POSE_LIMIT):
    limit = entry_pose_limit(cache_dir, enum)
    return limit is not None and limit >= required


def entry_revisions(cache_dir, enum):
    marker = Path(cache_dir) / enum / MARKER
    try:
        revs = json.loads(marker.read_text(encoding="utf-8")).get("revisions")
    except (OSError, ValueError, AttributeError):
        return ()
    return tuple(revs) if isinstance(revs, list) else ()


def entry_is_current(cache_dir, enum):
    """True when the entry carries every converter revision its species requires."""
    required = REQUIRED_REVISIONS.get(enum, ())
    have = set(entry_revisions(cache_dir, enum))
    return all(r in have for r in required)


def species_density(species_dir):
    """{clip stem: pose count} for one species directory."""
    clips = {}
    for path in Path(species_dir).rglob("*.mod"):
        match = POSE_RE.match(path.name)
        if not match:
            continue
        key = str(path.parent.relative_to(species_dir)) + "/" + match.group("stem")
        clips[key] = clips.get(key, 0) + 1
    return clips


def content_density(root):
    """{enum: {clips, min, median, max, total}} for every species under ``root``."""
    rows = {}
    for entry in sorted(Path(root).iterdir()):
        if not entry.is_dir():
            continue
        clips = species_density(entry)
        if not clips:
            continue
        counts = sorted(clips.values())
        rows[entry.name] = {"clips": len(counts), "min": counts[0],
                            "median": statistics.median(counts), "max": counts[-1],
                            "total": sum(counts)}
    return rows


def markdown_table(rows):
    lines = ["| species | clips | min | median | max | total poses |", "|---|---|---|---|---|---|"]
    for enum, r in rows.items():
        lines.append(f"| {enum} | {r['clips']} | {r['min']} | {r['median']:g} | {r['max']} | {r['total']} |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    rows = content_density(args.root)
    print(json.dumps(rows, indent=1) if args.json else markdown_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
