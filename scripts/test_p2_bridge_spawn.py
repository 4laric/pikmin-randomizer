"""Exercise the ENEMY_P2 ordinary-spawn binding resolution through the host probe.

Lane 03 (#439): the native side resolves a live generator's own identity
(``Generator::_70``, an ID32) to its bound P2 source id under the ENEMY_P2
bridge. This probe drives ``pc_randomizer_p2_source_for_id`` with the Snow
(45) / Dwarf Orange (44) cohort and asserts bound/unbound ids resolve correctly,
end to end from a real generated bootstrap.

    cmake --build <build> --target pc_randomizer_probe -j 6
    py -3.12 scripts/test_p2_bridge_spawn.py <build>/pc_randomizer_probe.exe
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_seed_bridge import build_bootstrap, resolve_layout  # noqa: E402
from randomizer.runner import NativeRun  # noqa: E402
from randomizer.seed import generate  # noqa: E402
from randomizer.session import Session  # noqa: E402

# Stable stand-ins for the Snow / Dwarf Orange dwarf generators' ID32 identity
# (`Generator::_70`). Real values come from lane 04's placement document; the
# resolver is value-agnostic, so any non-zero u32 exercises the exact seam.
SNOW_TARGET = "900000001"
ORANGE_TARGET = "900000002"


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
    manifest = generate("p2-spawn", collection_checks=True)
    layout = resolve_layout("p2-spawn", "Player1", (SNOW_TARGET, ORANGE_TARGET), (45, 44))
    bindings = {binding["target"]: binding["source_id"] for binding in layout["bindings"]}
    with tempfile.TemporaryDirectory() as tmp:
        run = bootstrap_with_p2(manifest, layout, Path(tmp) / "valid")
        probe = subprocess.run(
            [str(exe), "--randomizer-seed", str(run.bootstrap), "--enemy-p2-spawn-probe",
             "--enemy-p2-target", SNOW_TARGET, "--enemy-p2-target", ORANGE_TARGET],
            capture_output=True, text=True, timeout=30,
        )
        assert probe.returncode == 0 and "ENEMY_P2_SPAWN_PASS" in probe.stdout, (probe.stdout, probe.stderr)
        for target in (SNOW_TARGET, ORANGE_TARGET):
            line = f"P2_SPAWN_BIND target={target} source_id={bindings[target]}"
            assert line in probe.stdout, (line, probe.stdout)
    print("Native P2 spawn binding passed: Snow(45)/Dwarf Orange(44) target->source resolution "
          "plus unbound-id rejection")


if __name__ == "__main__":
    main()
