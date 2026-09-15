"""Exercise the native ENEMY_P2 parser and binder through the host probe.

Builds a valid schema-9 bootstrap, injects a P2 layout on the same roster
revision the native header was generated from, and asserts the probe reads it.
Rejected variants must exit 2 without creating a handshake, mirroring
``scripts/test_native_protocol.py``.

    cmake --build <build> --target pc_randomizer_probe -j 6
    py -3.12 scripts/test_p2_bridge_native.py <build>/pc_randomizer_probe.exe
"""
import argparse
import os
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
from randomizer.runner import NativeRun  # noqa: E402
from randomizer.seed import generate  # noqa: E402
from randomizer.session import Session  # noqa: E402


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
    manifest = generate("p2-native", collection_checks=True)
    layout = resolve_layout("p2-native", "Player1", ("gen-001", "gen-002"), (79, 30))
    first, second = layout["bindings"]
    revision = layout["roster_revision"]
    cases = {
        "unknown-id": (f"{first['target']} {first['source_id']}", f"{first['target']} 999"),
        "wrong-revision": (revision, "0" * 64),
        "duplicate-target": (second["target"], first["target"]),
        "bad-count": (f"ENEMY_P2 1 {revision} 2", f"ENEMY_P2 1 {revision} 3"),
    }
    with tempfile.TemporaryDirectory() as tmp:
        run = bootstrap_with_p2(manifest, layout, Path(tmp) / "valid")
        probe = subprocess.run([str(exe), "--randomizer-seed", str(run.bootstrap), "--enemy-p2-probe",
                                "--enemy-p2-expect", "79", "--enemy-p2-expect", "30"],
                               capture_output=True, text=True, timeout=30, env=probe_env())
        assert probe.returncode == 0 and "ENEMY_P2_PASS" in probe.stdout, (probe.stdout, probe.stderr)
        for name, (old, new) in cases.items():
            fresh = bootstrap_with_p2(manifest, layout, Path(tmp) / name)
            text = fresh.bootstrap.read_text(encoding="ascii")
            assert old in text, (name, old)
            fresh.bootstrap.write_text(text.replace(old, new, 1), encoding="ascii")
            result = subprocess.run([str(exe), "--randomizer-seed", str(fresh.bootstrap)],
                                    capture_output=True, text=True, timeout=30, env=probe_env())
            assert result.returncode == 2, (name, result.returncode, result.stdout, result.stderr)
            assert not (fresh.directory / "hello.txt").exists(), name
    print("Native P2 bridge passed: parse/bind, unknown id, wrong revision, duplicate target, bad count")


if __name__ == "__main__":
    main()
