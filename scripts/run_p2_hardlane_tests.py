"""Compile and run the hard-lane (BombSarai/Fuefuki/BigTreasure) unit tests.

Lane 01 Batch A (#437/#244/#245/#246). Standalone header/module tests with the
exact module sets each test needs; this is the affected-gate repeat short of the
real-GL runtime fixtures.

    py -3.12 scripts/run_p2_hardlane_tests.py --native output/lane01-native
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = {
    "p2_fuefuki_binding_test": [],
    "p2_fuefuki_fsm_test": [],
    "p2_fuefuki_interference_policy_test": [],
    "p2_fuefuki_suspend_fallback_test": [],
    "p2_bigtreasure_test": ["pc_port/pc_p2_bigtreasure.cpp"],
    "p2_bigtreasure_attacks_test": ["pc_port/pc_p2_bigtreasure_attacks.cpp", "pc_port/pc_p2_bigtreasure.cpp"],
    "p2_bigtreasure_fsm_test": ["pc_port/pc_p2_bigtreasure_fsm.cpp"],
    "p2_bigtreasure_host_test": ["pc_port/pc_p2_bigtreasure_host.cpp", "pc_port/pc_p2_bigtreasure.cpp",
                                 "pc_port/pc_p2_bigtreasure_attacks.cpp"],
    "p2_bigtreasure_motion_test": ["pc_port/pc_p2_bigtreasure_motion.cpp"],
    "p2_bombsarai_blast_test": ["pc_port/pc_p2_bombsarai_blast.cpp"],
    "p2_bombsarai_bomb_test": ["pc_port/pc_p2_bombsarai_bomb.cpp"],
    "p2_bombsarai_clock_test": [],
    "p2_bombsarai_fsm_test": ["pc_port/pc_p2_bombsarai_fsm.cpp"],
    "p2_bombsarai_hover_test": ["pc_port/pc_p2_bombsarai_hover.cpp"],
    "p2_bombsarai_induction_test": ["pc_port/pc_p2_bombsarai_fsm.cpp", "pc_port/pc_p2_bombsarai_bomb.cpp",
                                    "pc_port/pc_p2_bombsarai_terrain.cpp"],
    "p2_bombsarai_terrain_test": ["pc_port/pc_p2_bombsarai_terrain.cpp", "pc_port/pc_p2_bombsarai_bomb.cpp"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, default=Path("native"))
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--flags", nargs="*", default=None)
    args = parser.parse_args()
    native = args.native
    if not (native / "tools").is_dir():
        print(f"native source not found at {native}", file=sys.stderr)
        return 2
    flags = args.flags or ["-std=gnu++17", f"-I{native / 'pc_port'}", f"-I{native / 'include'}"]
    out = args.out or Path(tempfile.mkdtemp(prefix="p2-hardlane-tests-"))
    out.mkdir(parents=True, exist_ok=True)

    failures = []
    for name, modules in TESTS.items():
        source = native / "tools" / f"{name}.cpp"
        if not source.is_file():
            failures.append(f"{name}: source missing")
            continue
        exe = out / f"{name}.exe"
        command = [args.cxx, *flags, str(source), *[str(native / m) for m in modules], "-o", str(exe)]
        build = subprocess.run(command, capture_output=True, text=True)
        if build.returncode != 0:
            failures.append(f"{name}: compile failed")
            print(f"FAIL {name}: compile failed\n{build.stderr[-400:]}")
            continue
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        status = "PASS" if run.returncode == 0 else "FAIL"
        if run.returncode != 0:
            failures.append(f"{name}: exit {run.returncode}")
        print(f"{status} {name}")

    print(f"\n{len(TESTS) - len(failures)}/{len(TESTS)} hard-lane tests passed")
    if failures:
        for failure in failures:
            print("  -", failure)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
