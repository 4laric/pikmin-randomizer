"""Extraction sweep for proxy species declarations (issue #871).

For every entry in a plan JSON (``--plan``), run the generic
:func:`experimental.pikmin2_proxy_assets.extract` into ``--out/<id>``
(a fresh directory each time) with the row's ``pose_limit`` (default 4
when the row carries none), catch every exception, and write ``--report``
JSON with one record per species.

If a species fails ONLY on a byte budget (a clip over 512 KiB of pose
bytes or a bank over 8 MiB), retry automatically with ``pose_limit`` 3
then 2 and record the limit that worked.

Plan entries may carry the declaration override fields (``asset_dir``,
``param_dir``, ``clips``); they are passed through to
:func:`experimental.pikmin2_proxy_assets.extract` via ``row=``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_proxy_assets import extract  # noqa: E402

DEFAULT_PLAN = Path(
    "C:/Users/alari/pikmin-randomizer/output/claude-orch/rows-plan.json")
DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")

WAIT = ("wait1", "wait", "wait2")
MOVE = ("move1", "move", "move2", "run1", "walk")
ATTACK = ("attack1", "attack", "attack2", "charge", "hit_start")
DEAD = ("dead", "dead1", "pdead1")


def _is_byte_budget_error(message: str) -> bool:
    return "exceeds 512 KiB" in message or "exceeds 8 MiB" in message


def _roster_assets(source_id: int, enum_name: str):
    """Return ``(model_dir, anim_dir)`` the extractor would read.

    Mirrors ``experimental.pikmin2_proxy_assets._asset_names`` without
    importing its privates: roster ``assets`` block, falling back to the
    enum name.
    """
    path = ROOT / "docs" / "PIKMIN2_ENEMY_ROSTER.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for entry in payload.get("entries", []):
        if isinstance(entry, dict) and entry.get("source_id") == source_id:
            assets = entry.get("assets", {})
            if not isinstance(assets, dict):
                assets = {}
            model = assets.get("model") or enum_name
            anim = assets.get("anim") or enum_name
            return str(model), str(anim)
    return enum_name, enum_name


def _asset_label(model: str, anim: str) -> str:
    if model == anim:
        return model
    return f"{model}+{anim}"


def _available_clip_stems(iso: Path, source_id: int, enum_name: str):
    """Best-effort clip stems from the species' enemyanimmgr.txt.

    Used only to name what a FAILED species does carry (the fix is a
    per-row clip alias a later change will add). Never raises.
    """
    try:
        from experimental.pikmin2_assets import archive_files, disc_files
        from experimental.pikmin2_sheargrub_assets import animation_rows
        model, anim = _roster_assets(source_id, enum_name)
        param_path = ROOT / "docs" / "PIKMIN2_ENEMY_ROSTER.json"
        payload = json.loads(param_path.read_text(encoding="utf-8"))
        entry = None
        for candidate in payload.get("entries", []):
            if isinstance(candidate, dict) \
                    and candidate.get("source_id") == source_id:
                entry = candidate
                break
        assets = entry.get("assets", {}) if isinstance(entry, dict) else {}
        if not isinstance(assets, dict):
            assets = {}
        # The extractor derives the param prefix from the roster ``param``
        # field (falling back to the enum name), but several rows carry an
        # empty ``param`` while the disc files live under the model/anim
        # directory. Try each candidate prefix so a FAILED species still
        # reports the clip names it does carry.
        seen = set()
        prefixes = []
        for name in (assets.get("param"), assets.get("anim_mgr"),
                     assets.get("anim"), assets.get("model"), enum_name,
                     (entry or {}).get("source_name")):
            if isinstance(name, str) and name and name.lower() not in seen:
                seen.add(name.lower())
                prefixes.append(name.lower())
        index = disc_files(iso)
        with iso.open("rb") as disc:
            at, size = index["enemy/parm/enemyParms.szs"]
            disc.seek(at)
            params = archive_files(disc.read(size))
        for prefix in prefixes:
            try:
                raw = params[prefix + "/enemyanimmgr.txt"]
            except KeyError:
                continue
            return [Path(row["file"]).stem
                    for row in animation_rows(raw.decode("shift_jis"))]
        return []
    except Exception:
        return []


def _record_from_result(row, result, pose_limit_used, seconds):
    clips = result.get("clips", [])
    converted = [c for c in clips if c.get("status") == "converted"]
    stems = [Path(c["file"]).stem for c in converted]
    stem_set = set(stems)
    poses = sum(len(c.get("poses", [])) for c in converted)
    per_clip = [sum(p.get("bytes", 0) for p in c.get("poses", []))
                for c in converted]
    unsupported = sum(len(c.get("unsupported_frames", [])) for c in clips)
    joints = result.get("joints", [])
    return {
        "source_id": row["source_id"],
        "enum_name": row["enum_name"],
        "host_teki": row["host_teki"],
        "ok": True,
        "error": None,
        "pose_limit_used": pose_limit_used,
        "clips_converted": len(converted),
        "clip_names": stems,
        "poses": poses,
        "total_bytes": result.get("total_pose_bytes", 0),
        "max_clip_bytes": max(per_clip) if per_clip else 0,
        "joints": len(joints) if isinstance(joints, list) else 0,
        "unsupported_frames": unsupported,
        "has_wait": bool(stem_set & set(WAIT)),
        "has_move": bool(stem_set & set(MOVE)),
        "has_attack": bool(stem_set & set(ATTACK)),
        "has_dead": bool(stem_set & set(DEAD)),
        "asset_dir_on_disc": _asset_label(
            *_roster_assets(row["source_id"], row["enum_name"])),
        "seconds": seconds,
    }


def _failure_record(row, error, pose_limit_used, iso, seconds):
    model, anim = _roster_assets(row["source_id"], row["enum_name"])
    return {
        "source_id": row["source_id"],
        "enum_name": row["enum_name"],
        "host_teki": row["host_teki"],
        "ok": False,
        "error": error,
        "pose_limit_used": pose_limit_used,
        "clips_converted": 0,
        "clip_names": _available_clip_stems(
            iso, row["source_id"], row["enum_name"]),
        "poses": 0,
        "total_bytes": 0,
        "max_clip_bytes": 0,
        "joints": 0,
        "unsupported_frames": 0,
        "has_wait": False,
        "has_move": False,
        "has_attack": False,
        "has_dead": False,
        "asset_dir_on_disc": _asset_label(model, anim),
        "seconds": seconds,
    }


def sweep_species(iso: Path, row: dict, out_root: Path) -> dict:
    target = out_root / str(row["source_id"])
    initial = row.get("pose_limit", 4)
    if type(initial) is not int or not 2 <= initial <= 8:
        initial = 4
    started = time.monotonic()
    last_error = "unknown error"
    last_limit = initial
    # First attempt at the row's limit, then 3, then 2 on byte budget only.
    candidates = [initial]
    for fallback in (3, 2):
        if fallback not in candidates:
            candidates.append(fallback)
    for attempt, limit in enumerate(candidates):
        if target.exists():
            shutil.rmtree(target)
        try:
            result = extract(
                iso, row["enum_name"], row["source_id"], target,
                pose_limit=limit, row=row)
        except Exception as error:  # noqa: BLE001 - sweep catches everything
            last_error = f"{type(error).__name__}: {error}"
            last_limit = limit
            if attempt == 0 and not _is_byte_budget_error(str(error)):
                break
            if not _is_byte_budget_error(str(error)):
                break
            continue
        seconds = time.monotonic() - started
        return _record_from_result(row, result, limit, seconds)
    seconds = time.monotonic() - started
    return _failure_record(row, last_error, last_limit, iso, seconds)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for row in plan:
        record = sweep_species(args.iso, row, args.out)
        records.append(record)
        status = "ok" if record["ok"] else "FAIL"
        print(f"{status} id={record['source_id']} "
              f"{record['enum_name']} limit={record['pose_limit_used']} "
              f"poses={record['poses']} bytes={record['total_bytes']} "
              f"err={record['error']}", flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(records, indent=2, sort_keys=False) + "\n",
        encoding="utf-8")
    ok_count = sum(1 for r in records if r["ok"])
    print(f"sweep done: {ok_count}/{len(records)} ok -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
