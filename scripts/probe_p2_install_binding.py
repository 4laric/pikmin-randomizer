"""Lane 05 (Installation) identity-to-runtime binding product-path probe.

Exercises the NEW launcher path: a real generated ``p2_layout`` seed binding TWO
admitted identities (Dwarf Orange + Snow) -> ``runner.launch --p2-content`` ->
``install_layout`` through the REAL adapters -> a second launch that replays from
the session-level cache (cached=True). Also proves wrong-source rejection at the
launcher level leaves no private asset tree. No GL; synthetic banks.

    py -3.12 scripts/probe_p2_install_binding.py --output <out>   # out is the lane's ignored evidence dir
"""
import argparse
import json
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_dwarf_orange_bank import (  # noqa: E402
    BANK_JSON, BANK_TXT, HEADER, POSE_PREFIX, PROFILE, PROFILE_JSON, PROFILE_TXT)
from experimental.pikmin2_dwarf_orange_install import sha  # noqa: E402
from experimental.pikmin2_staging import StagingError  # noqa: E402

CLIPS = {"wait1": 75, "move1": 55, "attack": 90, "dead": 90, "flick": 80}
CHUNKS = ((32, b"material"), (34, b"texture"), (48, b"event"), (65535, b""))


def model_bytes():
    return b"".join(struct.pack(">II", tag, len(payload)) + payload for tag, payload in CHUNKS)


def make_dwarf_orange(content_root):
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


def make_snow(content_root):
    source = content_root / "YellowKochappy"
    source.mkdir(parents=True)
    data = model_bytes()
    motions = {}
    rows = ["P2_SNOW_2"]
    for name, duration in CLIPS.items():
        frames = [0, duration // 2, duration - 1]
        motions[name] = {"poses": 3, "source_frames": duration, "frames": frames}
        rows.append(f"{name} 3 {duration} 0 {duration // 2} {duration - 1}")
        for index in range(3):
            (source / f"snow_{name}_{index:02}.mod").write_bytes(data)
    (source / "p2-snow.txt").write_text("\n".join(rows) + "\n", encoding="ascii")
    (source / "snow.json").write_text(json.dumps(
        {"schema": 1, "species": "YellowKochappy", "motions": motions}), encoding="utf-8")
    return source


def placement_document():
    return {"schema": "p2-placement-v1",
            "slots": [{"uid": 401, "label": "orange-slot", "stage": 1, "terrain": "ground",
                       "radius": 300.0, "evidence": {"xyz": True, "terrain": True, "route": True}},
                      {"uid": 402, "label": "snow-slot", "stage": 1, "terrain": "ground",
                       "radius": 300.0, "evidence": {"xyz": True, "terrain": True, "route": True}}],
            "profiles": [{"identity": "BlueKochappy", "terrains": ["ground"], "accepted_gates": ["xyz"]},
                         {"identity": "YellowKochappy", "terrains": ["ground"], "accepted_gates": ["xyz"]}]}


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
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            content_root = tmp / "content"
            make_dwarf_orange(content_root)
            make_snow(content_root)
            retail = tmp / "retail"
            (retail / "dataDir" / "stages").mkdir(parents=True)

            bridge.admitted_ids = lambda roster: [44, 45]
            manifest = generate("dwarf-snow-binding-probe", collection_checks=True,
                                p2_enemies=True, p2_placement=placement_document())
            report(f"layout bindings: {manifest['p2_layout']['bindings']}")
            bindings = manifest["p2_layout"]["bindings"]
            by_enum = {b["enum_name"]: b for b in bindings}
            actors = {b["target"]: (211001 if b["enum_name"] == "BlueKochappy" else 211045)
                      for b in bindings}
            assert set(by_enum) == {"BlueKochappy", "YellowKochappy"}, by_enum

            session = tmp / "sess"
            runner.launch(manifest, session, assets=retail, p2_content=content_root,
                          p2_actors=actors)
            runner.launch(manifest, session, assets=retail, p2_content=content_root,
                          p2_actors=actors)

            receipts = sorted((session / "runs").glob("*/p2-binding-receipt.json"))
            report(f"runs staged: {len(receipts)}")
            cached = [bool(json.loads(p.read_text()).get("cached")) for p in receipts]
            report(f"cached flags: {cached}")
            room = next((session / "runs").glob("*/assets/dataDir/courses/pikmin2room"))
            report(f"room models: dwarf_orange={len(list(room.glob('dwarf_orange_*.mod')))} "
                   f"snow={len(list(room.glob('snow_*.mod')))}")
            actors_files = sorted((session / "runs").glob("*/p2-*-actors.txt"))
            report(f"actor files: {[p.name for p in actors_files]}")
            assert len(receipts) == 2 and sorted(cached) == [False, True], cached
            assert len(list(room.glob("dwarf_orange_*.mod"))) == 15
            assert len(list(room.glob("snow_*.mod"))) == 15
            assert {p.name for p in actors_files} == {"p2-dwarf-orange-actors.txt", "p2-snow-actors.txt"}

            # Wrong-source rejection at the launcher level: tamper the Dwarf Orange
            # bank's reference hash; the launch must fail closed and leave no private
            # asset tree in any run.
            bank_json = content_root / "BlueKochappy" / "bank" / BANK_JSON
            metadata = json.loads(bank_json.read_text(encoding="utf-8"))
            metadata["reference_sha256"] = "0" * 64
            bank_json.write_text(json.dumps(metadata), encoding="utf-8")

            bad_session = tmp / "bad-sess"
            try:
                runner.launch(manifest, bad_session, assets=retail,
                              p2_content=content_root, p2_actors=actors)
                raise SystemExit("wrong-source launch unexpectedly succeeded")
            except StagingError as exc:
                report(f"wrong-source rejected: {exc}")
            report(f"bad-session run dirs: {len(list((bad_session / 'runs').iterdir()))}")
            assert list((bad_session / "runs").iterdir()) == []
    finally:
        bridge.admitted_ids = original

    report("P2 install-binding probe passed: two-identity launcher staging + session-cache "
           "replay (cached=False->True) + wrong-source fail-closed (no asset tree)")
    (out / "probe-install-binding.txt").write_text("\n".join(log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
