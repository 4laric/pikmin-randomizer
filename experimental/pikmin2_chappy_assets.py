"""Own-identity source pose assets for the Chappy family (inst-chappy, #871).

Thin family extractor over the proven generic
:mod:`experimental.pikmin2_proxy_assets` sampler. Each Chappy-family species
extracts from the US GPVE01 rev 0 disc into its identity-keyed
``<out>/<Enum>/`` tree (``proxy.json`` plus the ``px_<Enum>_<clip>_<ii>.mod``
pose meshes) with the exact row overrides the species previously declared as
a proxy (asset_dir/param_dir/missing_normals), so extraction output is
byte-identical to the retired proxy extraction. What changes is ownership:
the ``chappy`` family installer (:mod:`experimental.pikmin2_chappy_content`)
stages these trees into the run instead of the shared proxy installer, and
the native ``pc_p2_chappy`` module (not the proxy visual) binds them.

Species (in lane order): 2 Chappy, 33 FireChappy, 35 KumaChappy,
43 YellowChappy, 53 KingChappy, 67 LeafChappy, 76 KumaKochappy.

Deterministic: hashed disc reads via the generic extractor, fixed clip
order, no timestamps. Nothing is fabricated: unconvertible frames are
recorded ``unsupported`` by the generic extractor, never placeholder poses.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experimental.pikmin2_animation import DEFAULT_POSE_LIMIT, POSE_LIMIT_MAX

# Row overrides carried over verbatim from the retired
# ``randomizer/p2_proxy/<id>_<Enum>.json`` declarations, so extraction stays
# byte-identical after the proxy row is removed. Keys mirror
# ``pikmin2_proxy_assets._row_overrides`` (asset_dir/param_dir/clips/
# param_files/missing_normals); only set keys travel with the call.
CHAPPY_ROWS = {
    2: {"enum_name": "Chappy", "pose_limit": DEFAULT_POSE_LIMIT},
    33: {"enum_name": "FireChappy", "pose_limit": DEFAULT_POSE_LIMIT},
    35: {"enum_name": "KumaChappy", "pose_limit": DEFAULT_POSE_LIMIT},
    43: {"enum_name": "YellowChappy", "pose_limit": DEFAULT_POSE_LIMIT,
        "asset_dir": "Chappy", "param_dir": "chappy"},
    53: {"enum_name": "KingChappy", "pose_limit": DEFAULT_POSE_LIMIT,
        "missing_normals": "compute"},
    67: {"enum_name": "LeafChappy", "pose_limit": DEFAULT_POSE_LIMIT},
    76: {"enum_name": "KumaKochappy", "pose_limit": DEFAULT_POSE_LIMIT,
        "asset_dir": "Kochappy", "param_dir": "kochappy"},
}

CHAPPY_IDS = tuple(CHAPPY_ROWS)
ENUM_FOR_ID = {source_id: row["enum_name"] for source_id, row in CHAPPY_ROWS.items()}
ID_FOR_ENUM = {row["enum_name"]: source_id for source_id, row in CHAPPY_ROWS.items()}


def row_for(source_id):
    """Return the extraction row for one Chappy-family source id."""
    try:
        row = CHAPPY_ROWS[source_id]
    except KeyError:
        raise ValueError(f"not a Chappy-family source id: {source_id!r}") from None
    return dict(row)


def extract(iso, enum_name, source_id, output, pose_limit=None, row=None):
    """Extract one Chappy-family species via the generic proxy sampler.

    ``row`` defaults to the carried-over declaration row for ``source_id``
    (so callers that pass nothing still extract the audited disc paths);
    an explicit mapping overrides it. ``pose_limit=None`` takes the row's
    ``pose_limit``. Output is the ``<output>/`` tree holding ``proxy.json``
    plus the ``px_<Enum>_<clip>_<ii>.mod`` pose meshes, exactly as the
    retired proxy extraction produced.
    """
    from experimental import pikmin2_proxy_assets as proxy

    if type(source_id) is not int or isinstance(source_id, bool):
        raise ValueError(f"Chappy source id must be an int: {source_id!r}")
    if source_id not in CHAPPY_ROWS:
        raise ValueError(f"not a Chappy-family source id: {source_id!r}")
    declared = row_for(source_id)
    if row is not None:
        if not isinstance(row, dict):
            raise ValueError(f"Chappy row override must be a mapping: {row!r}")
        declared.update(row)
    if enum_name != declared["enum_name"]:
        raise ValueError(
            f"Chappy enum mismatch for source {source_id}: "
            f"{enum_name!r} != {declared['enum_name']!r}")
    if pose_limit is None:
        pose_limit = declared["pose_limit"]
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    proxy_row = {key: declared[key] for key in
                 ("asset_dir", "param_dir", "clips", "param_files", "missing_normals")
                 if key in declared}
    proxy.extract(iso, enum_name, source_id, output,
                  pose_limit=pose_limit, row=proxy_row or None)
    return Path(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--enum", required=True)
    parser.add_argument("--source-id", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pose-limit", type=int, default=None)
    args = parser.parse_args(argv)
    extract(args.iso, args.enum, args.source_id, args.out,
            pose_limit=args.pose_limit)
    print(str(Path(args.out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
