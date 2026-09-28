"""Exercise the ENEMY_P2 ordinary-spawn binding resolution through the host probe.

Binds the real lane-04 target uids for the Snow (45) / Dwarf Orange (44) cohort
to their lane-02 source ids, writes a native bootstrap, and asserts the
``--enemy-p2-spawn-probe`` reads back the SAME uids the seed bound (identical
sources). The only source of targets is ``binding_targets_for_sources([45, 44])``;
no target is invented here.

    cmake --build <build> --target pc_randomizer_probe -j 6
    py -3.12 scripts/test_p2_bridge_spawn.py <build>/pc_randomizer_probe.exe
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe_env():
    """Match the probe's MinGW runtime environment (same mechanism as the session probe)."""
    env = dict(os.environ)
    mingw = Path(r"C:\msys64\mingw64\bin")
    if mingw.is_dir():
        env["PATH"] = str(mingw) + os.pathsep + env.get("PATH", "")
    return env

from experimental.pikmin2_seed_bridge import build_bootstrap, resolve_layout  # noqa: E402
from randomizer.p2_placement_catalog import binding_targets_for_sources  # noqa: E402
from randomizer.runner import NativeRun  # noqa: E402
from randomizer.seed import generate  # noqa: E402
from randomizer.session import Session  # noqa: E402

BIND_LINE = re.compile(r"P2_SPAWN_BIND target=(\d+) source_id=(\d+)")
ROUNDTRIP_LINE = re.compile(r"P2_ROUNDTRIP_BIND target=(\d+) source_id=(\d+)")


def bootstrap_with_p2(manifest, layout, directory):
    run = NativeRun(Session(manifest, directory))
    text = run.bootstrap.read_text(encoding="ascii")
    assert text.rstrip().endswith("END"), text
    run.bootstrap.write_text(text[:text.rfind("END")] + build_bootstrap(layout) + "END\n", encoding="ascii")
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    exe = parser.parse_args().exe.resolve(strict=True)

    targets = binding_targets_for_sources([45, 44])
    assert targets, "Snow/Dwarf Orange cohort resolved to an empty lane-04 target set"

    layout = resolve_layout("p2-spawn", "Player1", targets, (45, 44))
    assert len(layout["bindings"]) == len(targets), (len(layout["bindings"]), len(targets))

    native_bindings = {int(b["target"]): b["source_id"] for b in layout["bindings"]}
    assert set(native_bindings) == {int(t) for t in targets}, "native_bindings keys mismatch targets"

    parsed = {}
    roundtripped = {}
    with tempfile.TemporaryDirectory() as tmp:
        run = bootstrap_with_p2(generate("p2-spawn", collection_checks=True), layout, Path(tmp) / "valid")
        probe = subprocess.run(
            [str(exe), "--randomizer-seed", str(run.bootstrap), "--enemy-p2-spawn-probe"],
            capture_output=True, text=True, timeout=120, env=probe_env(),
        )
        assert probe.returncode == 0 and "ENEMY_P2_SPAWN_PASS" in probe.stdout, (probe.stdout, probe.stderr)
        for line in probe.stdout.splitlines():
            match = BIND_LINE.search(line)
            if match:
                parsed[int(match.group(1))] = int(match.group(2))
    assert parsed == native_bindings, (parsed, native_bindings)
    # The same seed must survive a byte-for-byte ramMode/cache (SLT1) round trip:
    # every bound spawn-slot uid recovers its source after a cache reload.
    with tempfile.TemporaryDirectory() as tmp:
        run = bootstrap_with_p2(generate("p2-spawn", collection_checks=True), layout, Path(tmp) / "roundtrip")
        probe = subprocess.run(
            [str(exe), "--randomizer-seed", str(run.bootstrap), "--enemy-p2-roundtrip-probe"],
            capture_output=True, text=True, timeout=120, env=probe_env(),
        )
        assert probe.returncode == 0 and "ENEMY_P2_ROUNDTRIP_PASS" in probe.stdout, (probe.stdout, probe.stderr)
        for line in probe.stdout.splitlines():
            match = ROUNDTRIP_LINE.search(line)
            if match:
                roundtripped[int(match.group(1))] = int(match.group(2))
    assert roundtripped == native_bindings, (roundtripped, native_bindings)
    print(f"Native P2 spawn binding passed: {len(targets)} real lane-04 uids resolve to the "
          "seed's Snow/Dwarf Orange sources and survive a ramMode/cache round trip")


if __name__ == "__main__":
    main()
