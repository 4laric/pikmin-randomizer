import asyncio
import hashlib
import inspect
import json
import secrets
import subprocess
import sys
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


def write_hello(manifest, client):
    parts = ["PIKMIN_HELLO", str(manifest["schema"]), client.token,
             fingerprint(manifest), *manifest["capabilities"], "END"]
    (client.directory / "hello.txt").write_text(" ".join(parts) + "\n", encoding="ascii", newline="\n")


def make_client(manifest, host_dir, peer_token=None):
    """Build a client through the real host export (peer token stable)."""
    bundle = export_client_bundle(manifest, host_dir, peer_token or secrets.token_hex(32))
    client = NetplayClientRun(manifest, mirror_dir_for(host_dir, manifest),
                              bundle["bootstrap_text"])
    write_hello(manifest, client)
    return client, bundle


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
                client, _ = make_client(manifest, host_dir)
                item = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
                name = next(iter(manifest["locations"]))
                (client.directory / "mirror-events.txt").write_text(
                    f"FRAME 1 RECEIVED 0 {item}\nFRAME 2 CHECKED {name}\n", encoding="ascii", newline="\n")
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

    def test_client_cli_end_to_end_no_socket(self):
        """Drive __main__ --netplay-client with an export-bundle bootstrap."""
        from randomizer import __main__ as cli
        manifest = generate("m4c-cli-socket", "ap")
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            peer = secrets.token_hex(32)
            bundle = export_client_bundle(manifest, host_dir, peer)
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            bootstrap_path = Path(tmp) / "peer.bootstrap"
            bootstrap_path.write_text(bundle["bootstrap_text"], encoding="ascii", newline="\n")
            mirror_dir = mirror_dir_for(host_dir, manifest)
            before_files = sorted(str(p.relative_to(host_dir)) for p in host_dir.rglob("*") if p.is_file())
            import websockets
            seen = {}

            async def fake_serve(manifest_arg, run, process=None):
                seen["dir"] = run.directory
                # Prove the client path polls without a socket.
                self.assertEqual(run.poll(), (0, 0))
                return None

            argv = ["randomizer", "run", str(manifest_path), "--session-dir", str(host_dir),
                    "--netplay-client", "--bootstrap", str(bootstrap_path)]
            with mock.patch.object(websockets, "connect",
                                   side_effect=AssertionError("client opened a socket")), \
                 mock.patch.object(sys, "argv", argv), \
                 mock.patch("randomizer.runner.serve_netplay_client", side_effect=fake_serve):
                cli.main()
            self.assertEqual(seen["dir"], mirror_dir / "runs" / peer)
            self.assertTrue((mirror_dir / "runs" / peer / "bootstrap.txt").is_file())
            after_files = sorted(str(p.relative_to(host_dir)) for p in host_dir.rglob("*") if p.is_file())
            host_writes = [f for f in after_files if not f.replace("\\", "/").startswith("netplay/")]
            self.assertEqual(host_writes, before_files)

    def test_client_fresh_interpreter_imports_no_websocket(self):
        script = (
            "import sys, tempfile, secrets; "
            "from pathlib import Path; "
            "from randomizer.seed import generate; "
            "from randomizer.session import Session; "
            "from randomizer.runner import NativeRun, NetplayClientRun; "
            "from randomizer.netplay_mirror import export_client_bundle, mirror_dir_for; "
            "from randomizer.catalog import ITEM_IDS, item_pool; "
            "m = generate('m4c-fresh-ws', 'ap'); "
            "t = tempfile.TemporaryDirectory(); "
            "h = Path(t.name)/'host'; h.mkdir(); "
            "s = Session(m, h); r = NativeRun(s); "
            "b = export_client_bundle(m, h, secrets.token_hex(32)); "
            "c = NetplayClientRun(m, mirror_dir_for(h, m), b['bootstrap_text']); "
            "assert 'websockets' not in sys.modules, 'client imports websockets'; "
            "print('NO_WEBSOCKET_OK')"
        )
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                              text=True, timeout=120, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr[-2000:])
        self.assertIn("NO_WEBSOCKET_OK", proc.stdout)

    def test_events_ingest_idempotently(self):
        manifest = generate("m4c-idem", "ap", death_link=True, goal_mode="emperor_bulblax")
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            client, _ = make_client(manifest, host_dir)
            items = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[:2]
            names = list(manifest["locations"])[:2]
            digest = "ab" * 32
            events = (f"FRAME 1 RECEIVED 0 {items[0]}\nFRAME 2 CHECKED {names[0]}\n"
                      f"FRAME 3 DEATHS 4\nFRAME 4 DEATHLINK 2\nFRAME 5 EMPEROR\n"
                      f"FRAME 6 SAVE_RESULT 9 {digest}\nFRAME 7 CHECKED {names[1]}\n"
                      f"FRAME 8 RECEIVED 1 {items[1]}\n")
            (client.directory / "mirror-events.txt").write_text(events, encoding="ascii", newline="\n")
            applied, _ = client.poll()
            self.assertEqual(applied, 8)
            data = client.mirror.load()
            self.assertEqual(data["received"], items)
            self.assertEqual(data["checked"], names)
            self.assertEqual(data["pikmin_deaths"], 4)
            self.assertEqual(data["death_links_received"], 2)
            self.assertTrue(data["emperor_defeated"])
            self.assertEqual(client.checkpoint["gen"], 9)
            first = (client.directory / "mirror.json").read_bytes()
            self.assertEqual(client.poll(), (0, 0))
            self.assertEqual((client.directory / "mirror.json").read_bytes(), first)
            with (client.directory / "mirror-events.txt").open("a", encoding="ascii", newline="\n") as handle:
                handle.write(f"FRAME 1 RECEIVED 0 {items[0]}\nFRAME 2 CHECKED {names[0]}\n")
            applied, duplicates = client.poll()
            self.assertEqual(applied, 0)
            self.assertEqual(duplicates, 2)
            self.assertEqual((client.directory / "mirror.json").read_bytes(), first)
            self.assertEqual(client.mirror.load()["received"], items)
            # Identical item ids at distinct indices are distinct receipts.
            with (client.directory / "mirror-events.txt").open("a", encoding="ascii", newline="\n") as handle:
                handle.write(f"FRAME 9 RECEIVED 2 {items[0]}\n")
            applied, duplicates = client.poll()
            self.assertEqual((applied, duplicates), (1, 0))
            self.assertEqual(client.mirror.load()["received"], items + [items[0]])
            # A lower index with a conflicting item is rejected.
            before = (client.directory / "mirror.json").read_bytes()
            with (client.directory / "mirror-events.txt").open("a", encoding="ascii", newline="\n") as handle:
                handle.write(f"FRAME 10 RECEIVED 0 {items[1]}\n")
            with self.assertRaises(ValueError):
                client.poll()
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)
        # An index gap is rejected (fresh client to isolate the file cursor).
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            gap_client, _ = make_client(manifest, host_dir)
            item0 = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
            (gap_client.directory / "mirror-events.txt").write_text(
                f"FRAME 1 RECEIVED 5 {item0}\n", encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                gap_client.poll()
            self.assertEqual(gap_client.mirror.load()["received"], [])

    def test_malformed_and_unknown_lines_rejected(self):
        manifest = generate("m4c-malformed", "ap")
        bad = ["FRAME x RECEIVED 0 1", "FRAME 1 BOGUS 2", "FRAME 1 RECEIVED",
               "RECEIVED 1", "FRAME 1 EMPEROR x", "FRAME 1 SAVE_RESULT 3 NOTHEX",
               "FRAME 4294967296 RECEIVED 0 1", "FRAME 1 CHECKED ", "FRAME 1 DEATHS -1",
               "frame 1 EMPEROR", "FRAME 1 SAVE_FAIL", "FRAME 1 RECEIVED 1",
               "FRAME 1 RECEIVED 0 1 2",
               "FRAME  1 EMPEROR", "FRAME 1 SAVE_RESULT 1 " + "AB" * 32,
               "FRAME 1 RECEIVED １", "X" * 257,
               "FRAME 01 EMPEROR", "FRAME 1 RECEIVED 00 1", "FRAME 1 RECEIVED 0 01",
               "FRAME 1 SAVE_RESULT 007 " + "ab" * 32, "FRAME 1 SAVE_RESULT 0 " + "ab" * 32,
               "FRAME 1 SAVE_RESULT 18446744073709551616 " + "ab" * 32,
               "FRAME 1 SAVE_FAIL 0", "FRAME 1 EMPEROR\r", "FRAME 1 DEATHS 01"]
        for line in bad:
            with self.subTest(line=line[:40]):
                with self.assertRaises(ValueError):
                    parse_mirror_line(line)
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            client, _ = make_client(manifest, host_dir)
            before = (client.directory / "mirror.json").read_bytes()
            (client.directory / "mirror-events.txt").write_text("FRAME 1 FROBNICATE 2\n", encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                client.poll()
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)
            item = max({ITEM_IDS[n] for n in item_pool(manifest)}) + 1
            (client.directory / "mirror-events.txt").write_text(f"FRAME 1 RECEIVED 0 {item}\n", encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                client.poll()
            (client.directory / "mirror-events.txt").write_text(
                "FRAME 1 CHECKED Pikmin: Main Engine\n", encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                client.poll()
            (client.directory / "mirror-events.txt").write_text("FRAME 1 DEATHS 2\n", encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                client.poll()
            (client.directory / "mirror-events.txt").write_text("FRAME 1 EMPEROR\n", encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                client.poll()
            # CRLF / control bytes are rejected at the poll level (split on \n only).
            (client.directory / "mirror-events.txt").write_bytes("FRAME 1 EMPEROR\r\n".encode("ascii"))
            with self.assertRaises(ValueError):
                client.poll()
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)
            (client.directory / "mirror-events.txt").write_bytes(
                f"FRAME 60 CHECKED X\x0cFRAME 61 RECEIVED 0 1\n".encode("ascii"))
            with self.assertRaises(ValueError):
                client.poll()
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)

    def test_hello_handshake_gated(self):
        manifest = generate("m4c-hello", "ap")
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            bundle = export_client_bundle(manifest, host_dir, secrets.token_hex(32))
            client = NetplayClientRun(manifest, mirror_dir_for(host_dir, manifest),
                                      bundle["bootstrap_text"])
            item = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
            (client.directory / "mirror-events.txt").write_text(
                f"FRAME 1 RECEIVED 0 {item}\n", encoding="ascii", newline="\n")
            # No hello yet: ingest waits.
            self.assertEqual(client.poll(), (0, 0))
            self.assertEqual(client.mirror.load()["received"], [])
            # Wrong hello is fatal.
            (client.directory / "hello.txt").write_text(
                f"PIKMIN_HELLO {manifest['schema']} {'0' * 64} {fingerprint(manifest)} "
                + " ".join([*manifest["capabilities"], "END"]) + "\n", encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                client.poll()
            # Correct hello resumes.
            write_hello(manifest, client)
            self.assertEqual(client.poll(), (1, 0))
            self.assertEqual(client.mirror.load()["received"], [item])

    def test_relaunch_resumes_mirror(self):
        manifest = generate("m4c-relaunch", "ap", death_link=True)
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            peer = secrets.token_hex(32)
            bundle = export_client_bundle(manifest, host_dir, peer)
            mirror_dir = mirror_dir_for(host_dir, manifest)
            first = NetplayClientRun(manifest, mirror_dir, bundle["bootstrap_text"])
            write_hello(manifest, first)
            item = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
            name = next(iter(manifest["locations"]))
            (first.directory / "mirror-events.txt").write_text(
                f"FRAME 1 RECEIVED 0 {item}\nFRAME 2 CHECKED {name}\nFRAME 3 DEATHS 6\n",
                encoding="ascii", newline="\n")
            self.assertEqual(first.poll(), (3, 0))
            # Relaunch with the same host bootstrap resumes the same run dir.
            second = NetplayClientRun(manifest, mirror_dir, bundle["bootstrap_text"])
            self.assertEqual(second.directory, first.directory)
            self.assertEqual(second.mirror.load(), first.mirror.load())
            self.assertEqual(second.checkpoint, first.checkpoint)
            self.assertEqual(second.last_frame, 3)
            write_hello(manifest, second)
            self.assertEqual(second.poll(), (0, 0))
            items = sorted({ITEM_IDS[n] for n in item_pool(manifest)})
            second_item = items[1] if len(items) > 1 else items[0]
            with (second.directory / "mirror-events.txt").open("a", encoding="ascii", newline="\n") as handle:
                handle.write(f"FRAME 4 RECEIVED 1 {second_item}\n")
            self.assertEqual(second.poll(), (1, 0))
            self.assertEqual(second.mirror.load()["received"], [item, second_item])
            # Totals are session-cumulative: the mirror keeps the deaths total.
            self.assertEqual(second.mirror.load()["pikmin_deaths"], 6)

    def test_frame_retraction_rejected(self):
        manifest = generate("m4c-frame", "ap")
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            client, _ = make_client(manifest, host_dir)
            name = next(iter(manifest["locations"]))
            names = list(manifest["locations"])[:2]
            (client.directory / "mirror-events.txt").write_text(
                f"FRAME 5 CHECKED {names[0]}\n", encoding="ascii", newline="\n")
            self.assertEqual(client.poll(), (1, 0))
            with (client.directory / "mirror-events.txt").open("a", encoding="ascii", newline="\n") as handle:
                handle.write(f"FRAME 3 CHECKED {names[1]}\n")
            with self.assertRaises(ValueError):
                client.poll()

    def test_bad_batch_is_atomic(self):
        manifest = generate("m4c-atomic", "ap")
        with tempfile.TemporaryDirectory() as tmp:
            host_dir = Path(tmp) / "host"
            host_dir.mkdir()
            make_host(manifest, host_dir)
            client, _ = make_client(manifest, host_dir)
            item = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
            name = next(iter(manifest["locations"]))
            before = (client.directory / "mirror.json").read_bytes()
            (client.directory / "mirror-events.txt").write_text(
                f"FRAME 1 RECEIVED 0 {item}\nFRAME 2 BOGUS 3\n", encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                client.poll()
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)
            self.assertEqual(client.mirror.load()["received"], [])
            self.assertFalse((client.directory / "card" / "SAVE_RESULT.txt").exists())
            # Card pointer is also atomic: good SAVE_RESULT + bad line writes nothing.
            digest = "cd" * 32
            (client.directory / "mirror-events.txt").write_text(
                f"FRAME 1 RECEIVED 0 {item}\nFRAME 2 SAVE_RESULT 4 {digest}\nFRAME 3 BOGUS 0\n",
                encoding="ascii", newline="\n")
            with self.assertRaises(ValueError):
                client.poll()
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)
            self.assertFalse((client.directory / "card" / "SAVE_RESULT.txt").exists())

    def test_mirror_json_validates_against_session_schema(self):
        for seed, mode, extra in (("m4c-schema-solo", "solo", {}),
                                  ("m4c-schema-ap", "ap", {"death_link": True})):
            manifest = generate(seed, mode, **extra)
            with self.subTest(seed=seed):
                with tempfile.TemporaryDirectory() as tmp:
                    host_dir = Path(tmp) / "host"
                    host_dir.mkdir()
                    make_host(manifest, host_dir)
                    client, _ = make_client(manifest, host_dir)
                    lines = []
                    if mode == "ap":
                        item = sorted({ITEM_IDS[n] for n in item_pool(manifest)})[0]
                        lines.append(f"FRAME 1 RECEIVED 0 {item}")
                        lines.append("FRAME 2 DEATHS 10")
                        lines.append("FRAME 3 DEATHLINK 1")
                    lines.append(f"FRAME 4 CHECKED {next(iter(manifest['locations']))}")
                    if manifest.get("goal_mode") == "emperor_bulblax":
                        lines.append("FRAME 5 EMPEROR")
                    (client.directory / "mirror-events.txt").write_text(
                        "\n".join(lines) + "\n", encoding="ascii", newline="\n")
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
                    client, _ = make_client(manifest, host_dir)
                    lines = [f"FRAME {i + 1} CHECKED {name}" for i, name in enumerate(names)]
                    if mode == "ap":
                        lines += [f"FRAME {100 + i} RECEIVED {i} {item}"
                                  for i, item in enumerate(host_data["received"])]
                    (client.directory / "mirror-events.txt").write_text(
                        "\n".join(lines) + "\n", encoding="ascii", newline="\n")
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
            (campaign / ("0" * 19 + "7.sav")).write_bytes(payload)
            # A decoy the native loader would reject must be ignored.
            (campaign / "7.sav").write_bytes(b"decoy")
            (host_dir / "runs" / "zz" / "campaign").mkdir(parents=True)
            (host_dir / "runs" / "zz" / "campaign" / ("0" * 19 + "9.sav")).write_bytes(b"decoy2")
            before = sorted(str(p.relative_to(host_dir)) for p in host_dir.rglob("*") if p.is_file())
            bundle = export_client_bundle(manifest, host_dir, peer)
            host_bytes = (run.directory / "bootstrap.txt").read_bytes()
            out_bytes = bundle["bootstrap_text"].encode("ascii")
            old_line = b"SESSION " + run.token.encode("ascii")
            self.assertEqual(out_bytes, host_bytes.replace(old_line, b"SESSION " + peer.encode("ascii")))
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
            with self.assertRaises(ValueError):
                export_client_bundle(manifest, host_dir, peer, host_run_token="../..")
            with self.assertRaises(ValueError):
                export_client_bundle(manifest, host_dir, 12345)


if __name__ == "__main__":
    unittest.main()
