"""P1 runtime import path for ch_ABEM_LeafChappy (issue #550).

Extends the P0 adapter
(`experimental.content_lanes.p2_challenge_ch_abem_leafchappy`, underscores)
without forking any parser: it reuses `decode_source`,
`validate_floor_coverage`, `read_iso_entry`, `sha256_bytes` and
`verify_source_hash` verbatim, then maps the decoded stage onto the
integrated host-mode module contract
(`native/pc_port/pc_p2_challenge_mode.h` `p2challenge::StageEntry`) and the
challenge framework consumer map
(`experimental.pikmin2_challenge_framework_contract.compute_score`).

Authoritative reference sets below are verified, not assumed: enemy bases
against research `enemyInfo.h/enemyInfo.cpp` (LeafChappy 67, FireChappy 33,
Kochappy 1, BlueKochappy 44, YellowKochappy 45, Egg 37); treasure tokens
against the disc pellet catalog (all but `key`, which follows the sibling
P0 convention for the stage key). Nothing here boots an engine, spawns an
actor, or claims a gate: runtime observation belongs to the guarded run,
which reports exactly what it sees.
"""
import hashlib
import json
from pathlib import Path

from experimental.content_lanes.p2_challenge_ch_abem_leafchappy import (
    BASELINE_METADATA,
    EXPECTED_FLOORS,
    SOURCE_PATH,
    SOURCE_SHA256,
    STAGE_ID,
    UI_INDEX,
    decode_source,
    read_iso_entry,
    sha256_bytes,
    validate_floor_coverage,
    verify_source_hash,
)
from experimental.pikmin2_challenge_framework_contract import compute_score

SCHEMA = "p2-challenge-import-p1-1"

# Research-verified enemy bases (enemyInfo.h enum + enemyInfo.cpp rows).
ENEMY_IDS = frozenset({
    "LeafChappy", "FireChappy", "Kochappy", "BlueKochappy",
    "YellowKochappy", "Egg",
})

# Disc pellet-catalog tokens, plus the stage `key` per sibling P0 convention.
TREASURE_IDS = frozenset({
    "key", "kouseki_suisyou", "bell_yellow", "apple", "leaf_kare",
    "diamond_blue_l", "be_dama_red", "be_dama_blue", "be_dama_yellow",
})

STARTING_SQUAD_TOTAL = 30


def stage_manifest(raw_bytes=None, iso_path=None):
    """Decode the real stage into a validated P1 manifest.

    Exactly one of `raw_bytes` / `iso_path` must be supplied. The source
    hash is verified against the P0 pin; floor coverage must be complete.
    """
    if (raw_bytes is None) == (iso_path is None):
        raise ValueError("supply exactly one of raw_bytes / iso_path")
    if raw_bytes is None:
        raw_bytes = read_iso_entry(iso_path)
    verify_source_hash(bytes(raw_bytes))
    text = bytes(raw_bytes).decode("shift_jis")
    parsed = decode_source(text, ENEMY_IDS, TREASURE_IDS)
    coverage = validate_floor_coverage(parsed)
    roster = BASELINE_METADATA["pikmin_by_native_color_and_maturity"]
    return {
        "schema": SCHEMA,
        "stage_id": STAGE_ID,
        "source": SOURCE_PATH,
        "source_sha256": sha256_bytes(bytes(raw_bytes)),
        "floors": parsed["floors"],
        "coverage": coverage,
        "ui_index": UI_INDEX,
        "floor_seconds": list(BASELINE_METADATA["floor_seconds"]),
        "starting_roster": [list(row) for row in roster],
        "starting_squad": sum(sum(row) for row in roster),
        "bitter_sprays": BASELINE_METADATA["bitter_sprays"],
        "spicy_sprays": BASELINE_METADATA["spicy_sprays"],
        "treasure_count_field": BASELINE_METADATA["treasure_count_field"],
    }

def host_stage_entry(manifest):
    """Map the manifest onto the native `p2challenge::StageEntry` shape.

    Field order and widths mirror `pc_p2_challenge_mode.h`: `floorSeconds`
    is padded to 8, `roster` is the 7x3 native color/maturity matrix.
    Values only; no engine contact.
    """
    roster = manifest["starting_roster"]
    if len(roster) != 7 or any(len(row) != 3 for row in roster):
        raise ValueError("starting roster must be a 7x3 matrix")
    seconds = [float(v) for v in manifest["floor_seconds"]]
    if len(seconds) != len(manifest["floors"]):
        raise ValueError("floor seconds must cover every floor")
    entry = {
        "caveId": manifest["stage_id"],
        "uiIndex": int(manifest["ui_index"]),
        "floorCount": int(len(manifest["floors"])),
        "floorSeconds": seconds + [0.0] * (8 - len(seconds)),
        "roster": [[int(v) for v in row] for row in roster],
        "bitterSprays": int(manifest["bitter_sprays"]),
        "spicySprays": int(manifest["spicy_sprays"]),
    }
    if entry["floorCount"] != EXPECTED_FLOORS:
        raise ValueError("entry floor count differs from the stage")
    return entry


def reference_score(manifest, pokos=0):
    """Expected score for a zero-receipt state via the framework formula."""
    time_left = int(sum(manifest["floor_seconds"]))
    return compute_score(int(pokos), time_left, STARTING_SQUAD_TOTAL)


def stage_run_layout(manifest, out_dir):
    """Stage a private run layout: stage entry, squad, expectations.

    Writes `stage.json`, `squad.json` and `expected.json` (markers plus the
    reference score). Never touches engine inputs or saves.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    entry = host_stage_entry(manifest)
    squad = {
        "total": manifest["starting_squad"],
        "roster": manifest["starting_roster"],
        "window": "960x540",
    }
    expected = {
        "markers": ["P2_CHALLENGE_MODE_BOOT", "P2_CHALLENGE_MODE_TICK",
                    "P2_CHALLENGE_MODE_DONE"],
        "reference_score_zero_receipt": reference_score(manifest),
        "captain_down": "P2_FIXTURE_CAPTAIN_DOWN",
    }
    (out / "stage.json").write_text(json.dumps(entry, indent=2) + "\n",
                                    encoding="utf-8")
    (out / "squad.json").write_text(json.dumps(squad, indent=2) + "\n",
                                    encoding="utf-8")
    (out / "expected.json").write_text(json.dumps(expected, indent=2) + "\n",
                                       encoding="utf-8")
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                             encoding="utf-8")
    return {"stage": str(out / "stage.json"), "squad": str(out / "squad.json"),
            "expected": str(out / "expected.json"),
            "manifest": str(manifest_path)}


def validate_room_boot_log(text):
    """Check the generic room-preview baseline (no challenge markers)."""
    checks = {
        "window_960x540": "960x540" in text,
        "centered": "center" in text.lower(),
        "no_extinction": "extinction" not in text.lower(),
    }
    return checks


def validate_host_markers(text, manifest):
    """Check a host-mode marker chain against the staged expectations.

    Returns UNTESTED-style verdicts when the runner is not wired (the
    current state): missing markers are reported, never synthesized.
    """
    kinds = []
    for line in text.splitlines():
        if line.startswith("P2_CHALLENGE_MODE_"):
            kinds.append(line.split(" ", 1)[0])
        elif line.startswith("P2_FIXTURE_CAPTAIN_DOWN"):
            kinds.append("P2_FIXTURE_CAPTAIN_DOWN")
    has = {name: (name in kinds) for name in
           ("P2_CHALLENGE_MODE_BOOT", "P2_CHALLENGE_MODE_TICK",
            "P2_CHALLENGE_MODE_DONE", "P2_FIXTURE_CAPTAIN_DOWN")}
    correlated = (has["P2_CHALLENGE_MODE_BOOT"] and has["P2_CHALLENGE_MODE_TICK"]
                  and has["P2_CHALLENGE_MODE_DONE"]
                  and not has["P2_FIXTURE_CAPTAIN_DOWN"])
    return {"markers": has, "correlated": correlated,
            "stage": manifest["stage_id"]}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, default=None)
    parser.add_argument("--stages", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = None
    if args.stages is not None:
        raw = Path(args.stages).read_bytes()
    manifest = stage_manifest(raw_bytes=raw, iso_path=args.iso)
    paths = stage_run_layout(manifest, args.output)
    print(json.dumps({"manifest": manifest["source_sha256"],
                      "paths": paths,
                      "reference_score": reference_score(manifest)},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())