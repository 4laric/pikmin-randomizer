"""Lane 05 (Installation) identity-to-runtime binding product-path probe.

Exercises the NEW path the earlier product probe does not touch: a real generated
``p2_layout`` seed -> ``runner.launch(..., p2_content=..., p2_actors=...)`` ->
``install_layout`` through the REAL Dwarf Orange adapter -> a second launch that
reploys from the session-level cache (cached=True). No GL; synthetic bank/profile.

    py -3.12 scripts/probe_p2_install_binding.py --output output/dsw/l05-out
"""
import argparse
import hashlib
import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_dwarf_orange_bank import (  # noqa: E402
    BANK_JSON, BANK_TXT, HEADER, POSE_PREFIX, PROFILE, PROFILE_JSON, PROFILE_TXT)
from experimental.pikmin2_dwarf_orange_install import sha  # noqa: E402

CLIPS = {"wait1": 75, "move1": 55, "attack": 90, "dead": 90, "flick": 80}
CHUNKS = ((32, b"material"), (34, b"texture"), (48, b"event"), (65535, b""))


def model_bytes():
    return b"".join(struct.pack(">II", tag, len(payload)) + payload for tag, payload in CHUNKS)


def make_source(content_root):
    source = content_root / "BlueKochappy"
    bank = source / "bank"
    profile = source / "profile"
    bank.mkdir(parents=True)
    profile.mkdir()
    profile_json = json.dumps({"schema": 1, "species": "BlueKochappy", "source_id": 44},
                              separators=(",", ":")).encode("ascii")
    (profile / PROFILE_JSON).write_bytes(profile_json)
    (bank / PROFILE_TXT).write_bytes(PROFILE.encode("ascii"))
    data = model_bytes()
    motions, file_sha256 = {}, {}
    rows = [HEADER]
    for name, duration in CLIPS.items():
        frames = [0, duration // 2, duration - 1]
        motions[name] = {"poses": 3, "source_frames": duration, "frames": frames,
                         "event_frames": [duration // 2]}
        rows.append(f"{name} 3 {duration} " + " ".join(map(str, frames)))
        for index in range(3):
            rel = f"{POSE_PREFIX}_{name}_{index:02}.mod"
            (bank / rel).write_bytes(data)
            file_sha256[rel] = sha(data)
    (bank / BANK_TXT).write_text("\n".join(rows) + "\n", encoding="ascii")
    (bank / BANK_JSON).write_text(json.dumps({
        "schema": 1, "species": "BlueKochappy", "source_id": 44, "health": 250,
        "motions": motions, "reference_sha256": sha(profile_json), "file_sha256": file_sha256,
    }), encoding="utf-8")
    return source


def placement_document():
    return {"schema": "p2-placement-v1",
            "slots": [{"uid": 401, "label": "bulborb-slot", "stage": 1, "terrain": "ground",
                       "radius": 300.0, "evidence": {"xyz": True, "terrain": True, "route": True}}],
            "profiles": [{"identity": "BlueKochappy", "terrains": ["ground"],
                          "accepted_gates": ["xyz"]}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    log = []

    def report(line):
        print(line, flush=True)
        log.append(line)

    import experimental.pikmin2_seed_bridge as bridge
    from randomizer import runner
    from randomizer.seed import generate

    async def fake_serve(*_a, **_k):
        pass

    runner.serve = fake_serve

    original = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: [44]
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            content_root = tmp / "content"
            make_source(content_root)
            retail = tmp / "retail"
            (retail / "dataDir" / "stages").mkdir(parents=True)

            manifest = generate("bluekochappy-binding-probe", collection_checks=True,
                                p2_enemies=True, p2_placement=placement_document())
            target = manifest["p2_layout"]["bindings"][0]["target"]
            report(f"layout: {manifest['p2_layout']['bindings']}")

            session = tmp / "sess"
            runner.launch(manifest, session, assets=retail, p2_content=content_root,
                          p2_actors={target: 211001})
            runner.launch(manifest, session, assets=retail, p2_content=content_root,
                          p2_actors={target: 211001})

            receipts = sorted((session / "runs").glob("*/p2-binding-receipt.json"))
            report(f"runs staged: {len(receipts)}")
            cached = [bool(json.loads(p.read_text()).get("cached")) for p in receipts]
            report(f"cached flags: {cached}")
            room = next((session / "runs").glob("*/assets/dataDir/courses/pikmin2room"))
            report(f"room models: {len(list(room.glob('dwarf_orange_*.mod')))}")
            assert len(receipts) == 2 and sorted(cached) == [False, True], cached
    finally:
        bridge.admitted_ids = original

    report("P2 install-binding probe passed: fresh install + session-cache replay (cached=False->True)")
    (out / "probe-install-binding.txt").write_text("\n".join(log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
