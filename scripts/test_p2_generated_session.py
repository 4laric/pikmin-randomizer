"""Generated-session product-path probe for lanes 02/03/05.

Exercises the real generator -> manifest validation -> NativeRun bootstrap ->
native ENEMY_P2 parser, plus lane 05 session content staging (fresh and cached).
The lane 02 admission gate is monkeypatched to a fixed reviewed cohort because the
live roster admits nothing yet; the product code path itself is unchanged.

    cmake --build <build> --target pc_randomizer_probe -j 6
    py -3.12 scripts/test_p2_generated_session.py <build>/pc_randomizer_probe.exe
"""
import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import experimental.pikmin2_seed_bridge as bridge  # noqa: E402
from experimental.pikmin2_staging import build_manifest, dump_manifest, stage_session_content  # noqa: E402
from randomizer.runner import NativeRun  # noqa: E402
from randomizer.seed import generate  # noqa: E402
from randomizer.session import Session  # noqa: E402

COHORT = (79, 15)  # Sokkuri + Armor (lane 14 ground candidates)


def placement_document():
    """Minimal lane 04 document accepting one ground slot each for two identities."""
    def slot(uid, label):
        return {"uid": uid, "label": label, "stage": 1, "terrain": "ground", "radius": 300.0,
                "evidence": {"xyz": True, "terrain": True, "route": True}}
    return {
        "schema": "p2-placement-v1",
        "slots": [slot(401, "sokkuri-slot"), slot(402, "armor-slot")],
        "profiles": [
            {"identity": "Sokkuri", "terrains": ["ground"], "accepted_gates": ["xyz"]},
            {"identity": "Armor", "terrains": ["ground"], "accepted_gates": ["xyz"]},
        ],
    }


def write_content_manifest(tmp):
    source = tmp / "source"
    source.mkdir(parents=True, exist_ok=True)
    entries = []
    for index in range(2):
        data = f"blob-{index}".encode()
        name = f"asset{index}.bin"
        (source / name).write_bytes(data)
        entries.append(dict(id=f"asset{index}", kind="model", source=f"source/{name}",
                            destination=f"tree/{name}", sha256=hashlib.sha256(data).hexdigest()))
    path = tmp / "content-manifest.json"
    dump_manifest(build_manifest(1, entries, notes="synthetic"), path)
    return path


def run_probe(exe, bootstrap, *args):
    env = dict(os.environ)
    mingw = Path(r"C:\msys64\mingw64\bin")
    if mingw.is_dir():  # MinGW runtime DLLs for the private probe build.
        env["PATH"] = str(mingw) + os.pathsep + env.get("PATH", "")
    return subprocess.run([str(exe), "--randomizer-seed", str(bootstrap), *args],
                          capture_output=True, text=True, timeout=30, env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    exe = parser.parse_args().exe.resolve(strict=True)

    original_admitted = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: list(COHORT)
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            manifest = generate("p2-native", collection_checks=True,
                                p2_enemies=True, p2_placement=placement_document())
            session = Session(manifest, tmp / "sess")
            run = NativeRun(session)
            bootstrap = run.bootstrap.read_text(encoding="ascii")
            assert f"ENEMY_P2 1 {manifest['p2_layout']['roster_revision']} 2 " in bootstrap

            probe = run_probe(exe, run.bootstrap, "--enemy-p2-probe",
                              "--enemy-p2-expect", "79", "--enemy-p2-expect", "15")
            assert probe.returncode == 0 and "ENEMY_P2_PASS" in probe.stdout, (probe.stdout, probe.stderr)

            content = write_content_manifest(tmp)
            fresh = stage_session_content(content, session.directory, cache_dir=tmp / "cache")
            cached = stage_session_content(content, session.directory, cache_dir=tmp / "cache")
            assert fresh["cached"] is False and cached["cached"] is True
            assert (session.directory / "content" / "tree" / "asset0.bin").read_bytes() == b"blob-0"

            # A separately valid P1 layout must not become accepted merely by
            # following a valid P2 block (the native parser reads sequentially).
            legacy_manifest = generate("legacy-mix", collection_checks=True, per_spawn_enemies=True)
            legacy_run = NativeRun(Session(legacy_manifest, tmp / "legacy"))
            legacy_text = legacy_run.bootstrap.read_text(encoding="ascii")
            legacy_layout = legacy_text[legacy_text.index("ENEMY_SLOTS"):]
            mixed_run = NativeRun(Session(manifest, session.directory))
            mixed_text = mixed_run.bootstrap.read_text(encoding="ascii")
            mixed_run.bootstrap.write_text(mixed_text.rsplit("END", 1)[0] + legacy_layout, encoding="ascii")
            mixed = run_probe(exe, mixed_run.bootstrap)
            assert mixed.returncode == 2 and "cannot mix" in mixed.stderr, (mixed.stdout, mixed.stderr)
            assert not (mixed_run.directory / "hello.txt").exists()

            first, second = manifest["p2_layout"]["bindings"]
            revision = manifest["p2_layout"]["roster_revision"]
            cases = {
                "unknown-id": (f"{first['target']} {first['source_id']}", f"{first['target']} 999"),
                "wrong-revision": (revision, "0" * 64),
                "duplicate-target": (second["target"], first["target"]),
                "bad-count": (f"ENEMY_P2 1 {revision} 2", f"ENEMY_P2 1 {revision} 3"),
            }
            for name, (old, new) in cases.items():
                fresh_run = NativeRun(Session(manifest, session.directory))
                text = fresh_run.bootstrap.read_text(encoding="ascii")
                assert old in text, (name, old)
                fresh_run.bootstrap.write_text(text.replace(old, new, 1), encoding="ascii")
                result = run_probe(exe, fresh_run.bootstrap)
                assert result.returncode == 2, (name, result.returncode, result.stdout, result.stderr)
                assert not (fresh_run.directory / "hello.txt").exists(), name
    finally:
        bridge.admitted_ids = original_admitted
    print("P2 generated-session path passed: real bootstrap ENEMY_P2, native parse/bind, "
          "content stage+cache, and 5 rejection cases")


if __name__ == "__main__":
    main()
