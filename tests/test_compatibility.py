import copy
import unittest
import tempfile
import json
from unittest.mock import patch as mock_patch
from pathlib import Path
from randomizer.compatibility import PART_CROSSWALK, part_identity, restore_slot_manifest
from randomizer.seed import generate, fingerprint
from randomizer.catalog import ALL_PART_IDS
from randomizer.thelynk import TheLynkSession, validate_server, enabled_locations, validate_options, LOCATIONS


def thelynk_patch():
    options = dict.fromkeys(("normal_first_day", "disable_pikmin_trip", "always_min_one_leaf", "day_cycle_mode",
                            "ship_part_hint_mode", "death_link", "pikmin_bond", "olimar_bond", "trap_link", "trap_percentage"), 0)
    options.update(skip_events=[], enable_pikmin_locations=1, red_pikmin_locations_enabled=1,
                   yellow_pikmin_locations_enabled=1, blue_pikmin_locations_enabled=1,
                   red_pikmin_interval=5, yellow_pikmin_interval=25, blue_pikmin_interval=10)
    return dict(Seed="12345", Slot=1, Name="TheLynkPlayer", Options=options, GameIdSuffix="abc")


class TheLynkConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_handshake_sync_checks_and_goal(self):
        from randomizer.thelynk import play, ITEMS
        patch = thelynk_patch()
        ids = list(enabled_locations(patch["Options"]).values())
        packets = [dict(cmd="RoomInfo", seed_name="W12345"),
                   dict(cmd="Connected", team=0, slot=1, checked_locations=[], missing_locations=ids,
                        slot_data=dict(patch["Options"], apworld_version=7, game_id_suffix="abc")),
                   dict(cmd="ReceivedItems", index=0, items=[dict(item=i) for i in range(71400,71430)]),
                   dict(cmd="DataPackage", data=dict(games={"Pikmin": dict(item_name_to_id=ITEMS, location_name_to_id=LOCATIONS)})),
                   dict(cmd="RoomUpdate", checked_locations=[71504])]
        sent, launches = [], []
        class Process:
            returncode = None
            def poll(self): return self.returncode
        process = Process()
        class Socket:
            async def recv(self):
                if packets:
                    return json.dumps([packets.pop(0)])
                process.returncode = 0
                return "[]"
            async def send(self, value): sent.extend(json.loads(value))
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
        with tempfile.TemporaryDirectory() as temp:
            session = TheLynkSession(patch, Path(temp) / "session")
            def launch(command, **kwargs):
                # All seed/option/ID checks and full Sync must precede launch.
                self.assertEqual(session.data["received"], list(range(71400,71430)))
                self.assertEqual(packets[0]["cmd"], "RoomUpdate")
                directory = Path(command[-1]).parent
                (directory / "hello.txt").write_text(f"THELYNK_HELLO 1 {directory.name} {session.fingerprint} individual-parts-v1 squad-checks-v1 typed-pikmin-v1 END\n", encoding="ascii")
                (directory / "checks.txt").write_text("71404\n", encoding="ascii")
                launches.append(command)
                return process
            with mock_patch("websockets.connect", return_value=Socket()), mock_patch("_winapi.CreateJunction"), \
                    mock_patch("randomizer.thelynk.subprocess.Popen", side_effect=launch):
                await play(session, "localhost:1234", Path(temp)/"native.exe", Path(temp))
            self.assertEqual(len(launches), 1)
            self.assertEqual(set(session.data["checked"]), {71404,71504})
            self.assertTrue(any(p["cmd"] == "Connect" and p["game"] == "Pikmin" for p in sent))
            self.assertTrue(any(p["cmd"] == "Sync" for p in sent))
            self.assertTrue(any(p["cmd"] == "LocationChecks" and 71404 in p["locations"] for p in sent))
            self.assertTrue(any(p["cmd"] == "StatusUpdate" and p["status"] == 30 for p in sent))

    async def test_foreign_world_never_launches_native(self):
        from randomizer.thelynk import play
        patch = thelynk_patch()
        packets = [dict(cmd="RoomInfo", seed_name="W12345"),
                   dict(cmd="Connected", team=0, slot=1, checked_locations=[],
                        missing_locations=list(enabled_locations(patch["Options"]).values()),
                        slot_data=dict(patch["Options"], apworld_version=8, game_id_suffix="abc"))]
        class Socket:
            async def recv(self): return json.dumps([packets.pop(0)])
            async def send(self, value): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
        with tempfile.TemporaryDirectory() as temp:
            session = TheLynkSession(patch, temp)
            with mock_patch("websockets.connect", return_value=Socket()), \
                    mock_patch("randomizer.thelynk.subprocess.Popen") as launch:
                with self.assertRaises(ValueError):
                    await play(session, "localhost:1234", Path(temp)/"native.exe", Path(temp))
                launch.assert_not_called()


class CompatibilityTests(unittest.TestCase):
    def test_thelynk_server_and_option_contract(self):
        patch = thelynk_patch()
        slot = dict(patch["Options"], apworld_version=7, game_id_suffix="abc")
        ids = list(enabled_locations(patch["Options"]).values())
        validate_server(patch, slot, ids)
        self.assertEqual(len(ids), 64)
        self.assertEqual(LOCATIONS["Red Pikmin: 10"], 71509)
        self.assertEqual(LOCATIONS["Blue Pikmin: 100"], 71799)
        for name in ("normal_first_day", "disable_pikmin_trip", "death_link", "trap_percentage"):
            options = dict(patch["Options"], **{name: 1})
            with self.assertRaises(ValueError):
                validate_options(options)
        for bad in (dict(slot, apworld_version=8), dict(slot, red_pikmin_interval=10),
                    dict(slot, game_id_suffix="bad")):
            with self.assertRaises(ValueError):
                validate_server(patch, bad, ids)
        with self.assertRaises(ValueError):
            validate_server(patch, slot, ids[:-1])

    def test_thelynk_receipts_replay_and_session_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            session = TheLynkSession(thelynk_patch(), directory)
            with self.assertRaises(ValueError):
                session.receive(0, [71404])
            session.bind("W12345", 0, 1)
            session.receive(0, [71404, 71800, 71817])
            session.receive(0, [71404, 71800, 71817])
            self.assertEqual(session.data["received"], [71404, 71800, 71817])
            self.assertFalse(session.goal)
            for index, items in ((4, []), (0, [71403]), (3, [71818]), (3, [71404])):
                with self.assertRaises(ValueError):
                    session.receive(index, items)
            before = session.path.read_bytes()
            with self.assertRaises(ValueError):
                session.bind("12346", 0, 1)
            self.assertEqual(session.path.read_bytes(), before)
            reloaded = TheLynkSession(thelynk_patch(), directory)
            self.assertEqual(reloaded.data, session.data)
            self.assertIn(" 16 CHECKS ", session.state("a" * 64, True))
            reloaded.receive(3, [i for i in range(71400, 71430) if i != 71404])
            self.assertTrue(reloaded.goal)
            with self.assertRaises(ValueError):
                from randomizer.session import Session
                Session(generate("local"), directory)

    def test_thelynk_journal_recovery_requires_authenticated_handshake(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            session = TheLynkSession(thelynk_patch(), directory)
            run = directory / "runs" / ("a" * 64)
            run.mkdir(parents=True)
            (run / "bootstrap.txt").write_text(session.bootstrap(run.name), encoding="ascii")
            (run / "checks.txt").write_bytes(b"71404\n71504\n717")
            with self.assertRaises(ValueError):
                session.poll(run)
            (run / "hello.txt").write_text(f"THELYNK_HELLO 1 {run.name} {session.fingerprint} individual-parts-v1 squad-checks-v1 typed-pikmin-v1 END\n", encoding="ascii")
            self.assertTrue(session.poll(run))
            self.assertEqual(session.data["checked"], [71404, 71504])
            self.assertEqual(TheLynkSession(thelynk_patch(), directory).data, session.data)
            (run / "checks.txt").write_text("999\n", encoding="ascii")
            with self.assertRaises(ValueError):
                session.poll(run)

    def test_all_parts_and_aliases(self):
        self.assertEqual(len(PART_CROSSWALK), 30)
        for field in ("native_index", "fourcc", "thelynk_item", "thelynk_location", "thelynk_item_id"):
            self.assertEqual(len({p[field] for p in PART_CROSSWALK}), 30)
        for row in PART_CROSSWALK:
            for key in ("native_index", "fourcc", "thelynk_item", "thelynk_location", "local_location"):
                if row[key] is not None:
                    self.assertEqual(part_identity(row[key]), row)
        self.assertIsNone(part_identity("Main Engine")["local_location"])
        self.assertEqual(part_identity("#1 Ionium Jet")["local_location"], "Pikmin: Ionium Jet 1")
        self.assertEqual(part_identity("Pikmin: Ionium Jet 2")["thelynk_item"], "#2 Ionium Jet")
        self.assertEqual({p["local_location"]: p["native_index"] for p in PART_CROSSWALK
                          if p["local_location"] is not None}, ALL_PART_IDS)
        for value in (True, None, "Red Pikmin: 10", "Population: 10 total Red Pikmin"):
            with self.assertRaises(ValueError):
                part_identity(value)

    def test_tracker_authoritative_copy_and_fingerprint(self):
        for config in ({}, dict(collection_checks=True, campaign_enemies=True,
                               starting_area="random", starting_color="random",
                               starting_flarlic=1, progressive_color_stats=True,
                               randomize_color_stats=True, goal_mode="emperor_bulblax")):
            manifest = generate("persisted-world", "ap", "OriginalSlot", **config)
            before = fingerprint(manifest)
            slot = dict(manifest=manifest, manifest_fingerprint=before)
            restored = restore_slot_manifest(slot)
            self.assertEqual(restored, manifest)
            restored["locations"].clear()
            self.assertEqual(fingerprint(manifest), before)
            bad = copy.deepcopy(slot)
            bad["manifest"]["seed"] = "different-seed"
            with self.assertRaises(ValueError):
                restore_slot_manifest(bad)
        for bad in (None, {}, dict(manifest={}, manifest_fingerprint="x"),
                    dict(manifest=generate("solo"), manifest_fingerprint="x")):
            with self.assertRaises(ValueError):
                restore_slot_manifest(bad)


if __name__ == "__main__":
    unittest.main()
