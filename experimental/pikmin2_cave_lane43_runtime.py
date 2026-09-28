"""Lane 43 (#481) live cave-generator runtime harness.

Lane 41 left the runtime hook compile-verified only. This module exercises it in
a real ``nectar.exe --experimental-pikmin2-room`` run:

1. reconcile the frozen lane-40 spike table and run the *standalone* native
   ``p2_cave_generator_test`` to get the reference layout;
2. boot the built game executable in a prepared 960x540 room overlay with
   ``PIKMIN_CAVE_GENERATOR_TABLE`` / ``PIKMIN_CAVE_GENERATOR_OUT`` set, capture
   the ``P2_CAVE_GEN`` marker and the layout written from the running process;
3. boot the same executable with the generator env unset as the control;
4. hand all three artifacts to :mod:`experimental.pikmin2_cave_lane43_live`.

The harness only orchestrates; the generator and the comparison are the native
engine's and lane 43's validator respectively. Both runs are bounded by a
timeout and the child is killed afterwards, so no window is left running.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from experimental.pikmin2_cave_lane41_generator import verify as verify_lane41
from experimental.pikmin2_cave_lane43_live import check_live_generation, check_unset_env

MINGW_BIN = r"C:\msys64\mingw64\bin"
ROOM_WINDOW = "960x540"


def _child_env(extra=None) -> dict:
    env = dict(os.environ)
    env["PATH"] = MINGW_BIN + os.pathsep + env.get("PATH", "")
    env["PIKMIN_P2_ROOM_WINDOW"] = ROOM_WINDOW
    env["PYTHONUTF8"] = "1"
    for key in ("PIKMIN_CAVE_GENERATOR_TABLE", "PIKMIN_CAVE_GENERATOR_OUT"):
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


def _run_capture(exe: Path, cwd: Path, log_path: Path, env: dict, timeout: float) -> dict:
    """Run a child, stream stdout/stderr to ``log_path``, kill it on timeout."""
    with log_path.open("wb") as log:
        process = subprocess.Popen([str(exe), "--experimental-pikmin2-room"], cwd=str(cwd),
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait()
    return {"exit_code": code, "timed_out": timed_out, "log": str(log_path)}


def run_standalone(tool: Path, spike_table: Path, out_dir: Path) -> dict:
    """Generate the reference native layout for the frozen spike table."""
    layout = out_dir / "p2-cave-observed-layout.json"
    table = out_dir / "p2-cave-floor-table.txt"
    source = json.loads(spike_table.read_text(encoding="utf-8"))
    report = verify_lane41(tool, source, layout, table)
    return {"report": report, "table": str(table), "layout": str(layout)}


def run_live(exe: Path, run_dir: Path, table: Path, layout: Path, log: Path, timeout: float) -> dict:
    env = _child_env({"PIKMIN_CAVE_GENERATOR_TABLE": str(table), "PIKMIN_CAVE_GENERATOR_OUT": str(layout)})
    return _run_capture(exe, run_dir, log, env, timeout)


def run_control(exe: Path, run_dir: Path, log: Path, timeout: float) -> dict:
    return _run_capture(exe, run_dir, log, _child_env(), timeout)


def prepare_overlay(assets: Path, converted: Path, output: Path) -> Path:
    from scripts.preview_pikmin2_room import prepare

    return prepare(assets.resolve(), converted.resolve(), output.resolve())


def pipeline(exe: Path, tool: Path, spike_table: Path, out_dir: Path, run_dir=None,
             assets=None, converted=None, live_timeout: float = 45.0,
             control_timeout: float = 45.0) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PATH"] = MINGW_BIN + os.pathsep + os.environ.get("PATH", "")
    standalone = run_standalone(Path(tool), Path(spike_table), out_dir / "standalone")

    if run_dir is None:
        if assets is None or converted is None:
            raise ValueError("run_dir or assets+converted is required")
        run_dir = prepare_overlay(Path(assets), Path(converted), out_dir / "overlay")
    run_dir = Path(run_dir)

    live_layout = out_dir / "live-layout.json"
    live = run_live(Path(exe), run_dir, Path(standalone["table"]), live_layout, out_dir / "live-run.log",
                    live_timeout)
    control = run_control(Path(exe), run_dir, out_dir / "control-run.log", control_timeout)

    live_log_text = Path(live["log"]).read_text(encoding="utf-8", errors="replace")
    control_log_text = Path(control["log"]).read_text(encoding="utf-8", errors="replace")
    live_layout_json = json.loads(live_layout.read_text(encoding="utf-8")) if live_layout.exists() else {}
    standalone_layout = json.loads(Path(standalone["layout"]).read_text(encoding="utf-8"))

    generation = check_live_generation(live_log_text, live_layout_json, standalone_layout)
    controls = check_unset_env(control_log_text)
    controls["room_ready"] = "P2_ROOM_READY" in control_log_text
    controls["window_960x540"] = "960x540" in control_log_text

    report = {
        "pass": bool(generation["pass"] and controls["pass"] and controls["room_ready"]
                     and controls["window_960x540"]),
        "generation": generation,
        "control": controls,
        "standalone": standalone,
        "live": live,
        "control_run": control,
        "run_dir": str(run_dir),
        "exe": str(exe),
        "tool": str(tool),
    }
    (out_dir / "lane43-live-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                                     encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True, help="built nectar.exe with the lane-41 hook")
    parser.add_argument("--tool", required=True, help="built p2_cave_generator_test executable")
    parser.add_argument("--table", required=True, help="lane 34/40 table JSON (the spike table)")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-dir", default=None, help="existing prepared room overlay")
    parser.add_argument("--assets", default=None, help="P1 asset root for a fresh overlay")
    parser.add_argument("--converted", default=None, help="converted P2 room directory")
    parser.add_argument("--live-timeout", type=float, default=45.0)
    parser.add_argument("--control-timeout", type=float, default=45.0)
    args = parser.parse_args(argv)

    report = pipeline(Path(args.exe), Path(args.tool), Path(args.table), Path(args.out_dir),
                      run_dir=args.run_dir, assets=args.assets, converted=args.converted,
                      live_timeout=args.live_timeout, control_timeout=args.control_timeout)
    summary = {
        "pass": report["pass"],
        "marker": report["generation"]["marker"],
        "standalone_matches": report["generation"]["standalone_matches"],
        "control_markers": report["control"]["markers"],
        "report": str(Path(args.out_dir) / "lane43-live-report.json"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
