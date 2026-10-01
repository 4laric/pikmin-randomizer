"""Real Python mirror consumer parity, including existing TheLynk identifiers."""
import json
import secrets
import tempfile
import unittest
from pathlib import Path
from randomizer.thelynk import TheLynkSession, PART_ITEMS, BONUSES
from randomizer.runner import NetplayClientRun, NativeRun, native_bootstrap
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.netplay_mirror import parse_mirror_line


def patch():
    options = dict.fromkeys(("normal_first_day", "disable_pikmin_trip", "always_min_one_leaf", "day_cycle_mode",
        "ship_part_hint_mode", "death_link", "pikmin_bond", "olimar_bond", "trap_link", "trap_percentage"), 0)
    options.update(skip_events=[], enable_pikmin_locations=1)
    for color in ("red", "yellow", "blue"):
        options[color + "_pikmin_locations_enabled"] = 1
        options[color + "_pikmin_interval"] = 1
    return dict(Options=options, Seed="protocol-test", Slot=1, Name="player")


class ProtocolConsumers(unittest.TestCase):
    def test_thelynk_real_mirror_once_and_external_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); host=TheLynkSession(patch(), root / "host")
            host.bind("protocol-test", 0, 1)
            token=secrets.token_hex(32)
            client=NetplayClientRun(patch(), root / "client", host.bootstrap(token))
            (client.directory / "hello.txt").write_text(
                f"THELYNK_HELLO 1 {token} {host.fingerprint} individual-parts-v1 squad-checks-v1 typed-pikmin-v1 END\n", encoding="ascii")
            items=[list(PART_ITEMS.values())[-1], list(BONUSES.values())[-1]]
            host.receive(0, items)
            name="Blue Pikmin: 100"; host.server_checks([host.locations[name]])
            stream="".join(f"FRAME {i+1} RECEIVED {i} {item}\n" for i,item in enumerate(items))
            stream+=f"FRAME 3 CHECKED {name}\n"
            (client.directory / "mirror-events.txt").write_text(stream, encoding="ascii", newline="\n")
            self.assertEqual(client.poll(), (3, 0))
            self.assertEqual(client.mirror.load()["checked"], [71799])
            self.assertEqual((client.directory / "state.txt").read_text(), host.state(token, True))
            before=(client.directory / "mirror.json").read_bytes()
            resumed=NetplayClientRun(patch(), root / "client", host.bootstrap(token))
            self.assertEqual(resumed.poll(), (0, 0))
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)
            with (client.directory / "mirror-events.txt").open("a",encoding="ascii",newline="\n") as f:
                f.write(f"FRAME 4 RECEIVED 2 {items[0]}\n")
            with self.assertRaisesRegex(ValueError,"duplicate unique"):
                resumed.poll()
            self.assertEqual((client.directory / "mirror.json").read_bytes(), before)

    def test_attach_native_identity_and_no_bootstrap_overwrite(self):
        manifest=generate("protocol-attach", "ap", progressive_maturity=True, progressive_day_length=3, whistle_pluck_item=True)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); session=Session(manifest, root / "session")
            token=secrets.token_hex(32); run_dir=session.directory / "runs" / token
            run_dir.mkdir(parents=True)
            bootstrap=run_dir / "bootstrap.txt"
            text=native_bootstrap(session, token)
            bootstrap.write_text(text,encoding="ascii",newline="\n")
            before=bootstrap.read_bytes()
            attached=NativeRun.attach(session,run_dir)
            self.assertEqual(attached.token,token)
            mirror=NetplayClientRun(manifest,session.directory,text,native_directory=run_dir)
            self.assertEqual(mirror.directory,run_dir.resolve())
            self.assertEqual(bootstrap.read_bytes(),before)
            bootstrap.write_text(text.replace("MATURITY 1","MATURITY 0"),encoding="ascii")
            with self.assertRaisesRegex(ValueError,"complete host manifest"):
                NativeRun.attach(session,run_dir)
            with self.assertRaisesRegex(ValueError,"changed"):
                NetplayClientRun(manifest,session.directory,text,native_directory=run_dir)

    def test_deathlink_uint32_boundary_and_atomic_batch(self):
        manifest=generate("protocol-deathlink", "ap", death_link=True)
        with tempfile.TemporaryDirectory() as tmp:
            host=Session(manifest, Path(tmp)/"host")
            token=secrets.token_hex(32)
            client=NetplayClientRun(manifest, Path(tmp)/"client", native_bootstrap(host,token))
            from tests.test_netplay_mirror import write_hello
            write_hello(manifest,client)
            events=client.directory/"mirror-events.txt"
            events.write_text("FRAME 1 DEATHLINK 4294967295\n",encoding="ascii",newline="\n")
            self.assertEqual(client.poll(),(1,0))
            self.assertEqual(client.mirror.load()["death_links_received"],(1<<32)-1)
            before=(client.directory/"mirror.json").read_bytes()
            with events.open("a",encoding="ascii",newline="\n") as f: f.write("FRAME 2 DEATHLINK 4294967296\n")
            with self.assertRaises(ValueError): client.poll()
            self.assertEqual((client.directory/"mirror.json").read_bytes(),before)
            events.write_text("FRAME 1 DEATHLINK 4294967295\nFRAME 2 DEATHLINK 4294967294\n",encoding="ascii",newline="\n")
            with self.assertRaises(ValueError): client.poll()
            self.assertEqual((client.directory/"mirror.json").read_bytes(),before)
            self.assertEqual(parse_mirror_line("FRAME 3 DEATHLINK 16909060")[2],(16909060,))
            with self.assertRaises(ValueError): parse_mirror_line("FRAME 3 DEATHS 1000001")
            invalid=json.loads(before);invalid["death_links_received"]=1<<32
            with self.assertRaises(ValueError): client.mirror.save(invalid)
            self.assertEqual((client.directory/"mirror.json").read_bytes(),before)

    def test_complete_client_bootstrap_refusal_before_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            ordinary=generate("protocol-bootstrap", "ap", progressive_maturity=True, progressive_day_length=3, whistle_pluck_item=True)
            host=Session(ordinary,root/"host")
            token=secrets.token_hex(32)
            self.assertIn("MATURITY 1",native_bootstrap(host,token))
            cases=[(ordinary,native_bootstrap(host,token).replace("MATURITY 1","MATURITY 0")),
                   (ordinary,native_bootstrap(host,token)+"UNKNOWN 1\n")]
            tl=TheLynkSession(patch(),root/"tl-host")
            cases.extend([(patch(),tl.bootstrap(token).replace("CHECKS 330","CHECKS 329")),
                          (patch(),tl.bootstrap(token)+f"SESSION {token}\n")])
            for i,(manifest,text) in enumerate(cases):
                target=root/str(i)
                with self.assertRaisesRegex(ValueError,"complete host manifest"):
                    NetplayClientRun(manifest,target,text)
                self.assertFalse(target.exists())


class PairedHarnessSafetyTests(unittest.TestCase):
    @staticmethod
    def harness():
        import importlib.util
        path = Path(__file__).resolve().parents[1] / "scripts/run_coop_state_protocol_acceptance.py"
        spec = importlib.util.spec_from_file_location("paired_harness", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_sdl_command_atomic_refusal_preserves_previous_file(self):
        from unittest.mock import patch as mock_patch
        module = self.harness()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "command.txt"
            command = module.SdlCommand(path)
            self.assertTrue(command.publish(1, (-32768, 32767, 0, 0)))
            previous = path.read_bytes()
            self.assertEqual(previous, b"SDL1 1 1 -32768 32767 0 0 END\n")
            for buttons, axes in [(1 << 21, (0, 0, 0, 0)), (-1, (0, 0, 0, 0)),
                                   (0, (32768, 0, 0, 0)), (0, (0, 0, 0))]:
                with self.assertRaises(ValueError): command.publish(buttons, axes)
                self.assertEqual(path.read_bytes(), previous)
            with mock_patch.object(module.os, "replace", side_effect=PermissionError):
                self.assertFalse(command.publish())
            self.assertEqual(path.read_bytes(), previous)
            self.assertFalse(path.with_suffix(".pending").exists())
            self.assertTrue(command.publish())
            self.assertEqual(path.read_bytes(), b"SDL1 3 0 0 0 0 0 END\n")

    def test_deadline_covers_preinit_and_refuses_extended_limit(self):
        from unittest.mock import patch as mock_patch
        module = self.harness()
        for seconds in (0, -1, 60.001):
            with self.assertRaises(ValueError): module.Deadline(seconds)
        with mock_patch.object(module.time, "monotonic", side_effect=[100, 159.99, 160]):
            deadline = module.Deadline(60)
            deadline.check()
            with self.assertRaises(TimeoutError): deadline.check()

    def test_cleanup_signals_only_registered_owned_children(self):
        module = self.harness()
        class Child:
            def __init__(self, exited=False): self.exited=exited; self.signals=[]
            def poll(self): return 0 if self.exited else None
            def terminate(self): self.signals.append("terminate"); self.exited=True
            def wait(self, timeout): return 0
        alive, exited, unrelated = Child(), Child(True), Child()
        owned = module.OwnedChildren(); owned.children = [alive, exited]
        owned.close()
        self.assertEqual(alive.signals, ["terminate"])
        self.assertEqual(exited.signals, [])
        self.assertEqual(unrelated.signals, [])
