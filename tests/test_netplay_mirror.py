import asyncio
import hashlib
import inspect
import json
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from randomizer.catalog import ITEM_IDS, item_pool
from randomizer.netplay_mirror import (
    MirrorStore,
    export_client_bundle,
    initial_mirror_data,
    mirror_dir_for,
    parse_mirror_line,
    validate_mirror_data,
)
from randomizer.overlay import snapshot as overlay_snapshot
from randomizer.runner import NativeRun, NetplayClientRun, serve_netplay_client
from randomizer.seed import fingerprint, generate
from randomizer.session import Session, load_session_data, resolve_session_file
from randomizer.tracker import TrackerModel


def make_host(manifest, root):
    session = Session(manifest, root)
    run = NativeRun(session)
    return session, run


def make_client(manifest, host_dir, run_token=None):
    host_run = sorted((host_dir / "runs").glob("*/bootstrap.txt"))[-1]
    host_text = host_run.read_text(encoding="ascii")
    token = run_token or secrets.token_hex(32)
    lines = [(f"SESSION {token}" if line.startswith("SESSION ") else line)
             for line in host_text.splitlines()]
    return NetplayClientRun(manifest, mirror_dir_for(host_dir, manifest),
                            "\n".join(lines) + "\n", run_token=token)


class NetplayMirrorTests(unittest.TestCase):
    def test_client_never_opens_socket(self):
        manifest = generate("m4c-no-socket", "ap")
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            session, run = make_host(manifest, host_dir)
            before = {p.relative_to(host_dir): p.read_bytes()
                      for p in list(host_dir.glob("session.json")) + list(host_dir.glob("runs/*/checks.txt"))}
            norm = lambda files: sorted(f.replace("\\", "/") for f in files)
            before_files = norm(str(p.relative_to(host_dir)) for p in host_dir.rglob("*") if p.is_file())
            import websockets
            with mock.patch.object(websockets, "connect",
                                   side_effect=AssertionError("client opened a socket")):
                client = make_client(manifest, host_dir)
                item = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
                name = next(iter(manifest["locations"]))
                (client.directory / "mirror-events.txt").write_text(
                    f"FRAME 1 RECEIVED {item}\nFRAME 2 CHECKED {name}\n", encoding="ascii")
                self.assertEqual(client.poll(), (2, 0))
                with self.assertRaises(asyncio.TimeoutError):
                    asyncio.run(asyncio.wait_for(serve_netplay_client(manifest, client), 0.5))
            for source in (inspect.getsource(NetplayClientRun),
                           inspect.getsource(serve_netplay_client)):
                for marker in ("import websockets", "websockets.", "ap_connect(", "serve(session"):
                    self.assertNotIn(marker, source)
            after_files = norm(str(p.relative_to(host_dir)) for p in host_dir.rglob("*") if p.is_file())
            host_writes = [f for f in after_files if not f.startswith("netplay/")]
            self.assertEqual(host_writes, before_files)
            for rel, content in before.items():
                self.assertEqual((host_dir / rel).read_bytes(), content)
            self.assertFalse((host_dir / "runner.lock").exists())

    def test_events_ingest_idempotently(self):
        manifest = generate("m4c-idem", "ap", death_link=True, goal_mode="emperor_bulblax")
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            client = make_client(manifest, host_dir)
            item = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
            names = list(manifest["locations"])[:2]
            digest = "ab" * 32
            events = (f"FRAME 1 RECEIVED {item}\nFRAME 2 CHECKED {names[0]}\n"
                      f"FRAME 3 DEATHS 4\nFRAME 4 DEATHLINK 2\nFRAME 5 EMPEROR\n"
                      f"FRAME 6 SAVE_RESULT 9 {digest}\nFRAME 7 CHECKED {names[1]}\n")
            (client.directory / "mirror-events.txt").write_text(events, encoding="ascii")
            applied, _ = client.poll()
            self.assertEqual(applied, 7)
            data = client.mirror.load()
            self.assertEqual(data["received"], [item])
            self.assertEqual(data["checked"], names)
            self.assertEqual(data["pikmin_deaths"], 4)
            self.assertEqual(data["death_links_received"], 2)
            self.assertTrue(data["emperor_defeated"])
            self.assertEqual(client.checkpoint["gen"], 9)
            first = (client.directory / "mirror.json").read_bytes()
            self.assertEqual(client.poll(), (0, 0))
            self.assertEqual((client.directory / "mirror.json").read_bytes(), first)
            with (client.directory / "mirror-events.txt").open("a", encoding="ascii") as handle:
                handle.write(f"FRAME 1 RECEIVED {item}\nFRAME 2 CHECKED {names[0]}\n")
            applied, duplicates = client.poll()
            self.assertEqual(applied, 0)
            self.assertEqual(duplicates, 2)
            self.assertEqual((client.directory / "mirror.json").read_bytes(), first)
            self.assertEqual(client.mirror.load()["received"], [item])

    def test_malformed_and_unknown_lines_rejected(self):
        manifest = generate("m4c-malformed", "ap")
        bad = ["FRAME x RECEIVED 1", "FRAME 1 BOGUS 2", "FRAME 1 RECEIVED",
               "RECEIVED 1", "FRAME 1 EMPEROR x", "FRAME 1 SAVE_RESULT 3 NOTHEX",
               "FRAME 4294967296 RECEIVED 1", "FRAME 1 CHECKED ", "FRAME 1 DEATHS -1",
               "frame 1 EMPEROR", "FRAME 1 SAVE_FAIL", "FRAME 1 RECEIVED 1 2",
               "FRAME  1 EMPEROR", "FRAME 1 SAVE_RESULT 1 " + "AB" * 32,
               "FRAME 1 RECEIVED １", "X" * 257]
        for line in bad:
            with self.subTest(line=line[:40]):
                with self.assertRaises(ValueError):
                    parse_mirror_line(line)
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            client = make_client(manifest, host_dir)
            before = (client.directory / "mirror.json").read_bytes()
            (client.directory / "mirror-events.txt").write_text("FRAME 1 FROBNICATE 2\n", encoding="ascii")
            with self.assertRaises(ValueError):
                client.poll()
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)
            item = max({ITEM_IDS[n] for n in item_pool(manifest)}) + 1
            (client.directory / "mirror-events.txt").write_text(f"FRAME 1 RECEIVED {item}\n", encoding="ascii")
            with self.assertRaises(ValueError):
                client.poll()
            (client.directory / "mirror-events.txt").write_text(
                "FRAME 1 CHECKED Pikmin: Main Engine\n", encoding="ascii")
            with self.assertRaises(ValueError):
                client.poll()
            (client.directory / "mirror-events.txt").write_text("FRAME 1 DEATHS 2\n", encoding="ascii")
            with self.assertRaises(ValueError):
                client.poll()
            (client.directory / "mirror-events.txt").write_text("FRAME 1 EMPEROR\n", encoding="ascii")
            with self.assertRaises(ValueError):
                client.poll()

    def test_mirror_json_validates_against_session_schema(self):
        for seed, mode, extra in (("m4c-schema-solo", "solo", {}),
                                  ("m4c-schema-ap", "ap", {"death_link": True})):
            manifest = generate(seed, mode, **extra)
            with self.subTest(seed=seed):
                with tempfile.TemporaryDirectory() as tmp:
                    host_dir = Path(tmp) / "host"
                    host_dir.mkdir()
                    make_host(manifest, host_dir)
                    client = make_client(manifest, host_dir)
                    lines = []
                    if mode == "ap":
                        item = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
                        lines.append(f"FRAME 1 RECEIVED {item}")
                        lines.append("FRAME 2 DEATHS 10")
                        lines.append("FRAME 3 DEATHLINK 1")
                    lines.append(f"FRAME 4 CHECKED {next(iter(manifest['locations']))}")
                    if manifest.get("goal_mode") == "emperor_bulblax":
                        lines.append("FRAME 5 EMPEROR")
                    (client.directory / "mirror-events.txt").write_text(
                        "\n".join(lines) + "\n", encoding="ascii")
                    client.poll()
                    data = json.loads((client.directory / "mirror.json").read_text(encoding="utf-8"))
                    self.assertTrue(validate_mirror_data(manifest, data))
                    probe = Path(tmp) / "probe"
                    probe.mkdir()
                    (probe / "session.json").write_text(json.dumps(data), encoding="utf-8")
                    reloaded = Session(manifest, probe)
                    self.assertEqual(reloaded.data, data)
                    self.assertEqual(resolve_session_file(client.directory).name, "mirror.json")
                    self.assertEqual(load_session_data(client.directory), data)

    def test_overlay_tracker_snapshot_matches_host(self):
        for seed, mode in (("m4c-snap-solo", "solo"), ("m4c-snap-ap", "ap")):
            manifest = generate(seed, mode)
            with self.subTest(seed=seed):
                with tempfile.TemporaryDirectory() as tmp:
                    host_dir = Path(tmp) / "host"
                    host_dir.mkdir()
                    session, _ = make_host(manifest, host_dir)
                    names = list(manifest["locations"])[:2]
                    if mode == "solo":
                        for name in names:
                            session.collect(name)
                    else:
                        session.bind_ap("room", 0, 1)
                        items = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[:3]
                        session.receive(0, items)
                        for name in names:
                            session.collect(name)
                    host_data = json.loads((host_dir / "session.json").read_text(encoding="utf-8"))
                    client = make_client(manifest, host_dir)
                    lines = [f"FRAME {i + 1} CHECKED {name}" for i, name in enumerate(names)]
                    if mode == "ap":
                        lines += [f"FRAME {100 + i} RECEIVED {item}"
                                  for i, item in enumerate(host_data["received"])]
                    (client.directory / "mirror-events.txt").write_text(
                        "\n".join(lines) + "\n", encoding="ascii")
                    client.poll()
                    mirror_data = json.loads((client.directory / "mirror.json").read_text(encoding="utf-8"))
                    self.assertEqual(overlay_snapshot(manifest, mirror_data),
                                     overlay_snapshot(manifest, host_data))
                    model = TrackerModel(manifest)
                    host_snap, mirror_snap = model.snapshot(host_data), model.snapshot(mirror_data)
                    self.assertEqual(mirror_snap["inventory"], host_snap["inventory"])
                    self.assertEqual(mirror_snap["summary"], host_snap["summary"])
                    self.assertEqual(mirror_snap["rows"], host_snap["rows"])
                    self.assertEqual(model.snapshot_from_dir(client.directory), mirror_snap)

    def test_export_helper_restamps_session_only(self):
        manifest = generate("m4c-export")
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            _, run = make_host(manifest, host_dir)
            peer = secrets.token_hex(32)
            campaign = host_dir / "campaign"
            campaign.mkdir()
            payload = b"C" * 100
            (campaign / ("0" * 19 + "7")).with_suffix(".sav").write_bytes(payload)
            before = sorted(str(p.relative_to(host_dir)) for p in host_dir.rglob("*") if p.is_file())
            bundle = export_client_bundle(manifest, host_dir, peer)
            host_text = (run.directory / "bootstrap.txt").read_text(encoding="ascii")
            self.assertEqual(bundle["bootstrap_text"].splitlines(),
                             [f"SESSION {peer}" if line.startswith("SESSION ") else line
                              for line in host_text.splitlines()])
            self.assertIn(f"SESSION {peer}\n", bundle["bootstrap_text"])
            self.assertNotIn(f"SESSION {run.token}\n", bundle["bootstrap_text"])
            self.assertEqual(bundle["fingerprint"], fingerprint(manifest))
            self.assertEqual(bundle["checkpoint_gen"], 7)
            self.assertEqual(bundle["checkpoint_hash"], hashlib.sha256(payload).hexdigest())
            self.assertTrue(bundle["checkpoint_path"].endswith(".sav"))
            after = sorted(str(p.relative_to(host_dir)) for p in host_dir.rglob("*") if p.is_file())
            self.assertEqual(after, before)
            empty = Path(tmp) / "empty"
            (empty / "runs" / "x").mkdir(parents=True)
            with self.assertRaises(ValueError):
                export_client_bundle(manifest, empty, peer)


if __name__ == "__main__":
    unittest.main()
