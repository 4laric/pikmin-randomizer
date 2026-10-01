"""Independent packaged consumer audit; synthetic protocol files, no game runtime."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def token(label):
    return hashlib.sha256(label.encode()).hexdigest()


def refused(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("invalid consumer input was accepted")


def packaged(ap, archive, output):
    # A fresh child process has no checkout-backed randomizer/experimental imports.
    sys.path[:] = [p for p in sys.path if p and Path(p).resolve() not in (ROOT, ROOT / "scripts")]
    sys.path[:0] = [str(archive), str(ap)]
    import ModuleUpdate
    ModuleUpdate.update_ran = True
    import worlds  # noqa: F401
    world = importlib.import_module("pikmin_randomizer")
    assert str(archive) in world.__file__
    from test.general import setup_multiworld
    from Fill import distribute_items_restrictive
    from BaseClasses import CollectionState
    from pikmin_randomizer.core.seed import validate, fingerprint
    from pikmin_randomizer.core.catalog import ITEM_IDS
    configurations = {
        "p1-default": {},
        "p1-receipts": {"progressive_day_length": 3, "death_link": True},
        "p2-default": {"p2_enemy_randomizer": True},
        "p2-captains": {"p2_enemy_randomizer": True, "p2_second_captain": True,
                        "progressive_day_length": 3, "death_link": True},
    }
    old_cwd = Path.cwd()
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(output)  # package resource loading cannot fall back to checkout docs
    try:
        for label, options in configurations.items():
            for seed in (1158, 1159, 1160):
                mw = setup_multiworld(world.PikminRandomizerWorld, seed=seed, options=options)
                generated = mw.worlds[1]
                manifest = generated.manifest()
                validate(manifest)
                assert manifest.get("progressive_maturity") and manifest.get("whistle_pluck_item")
                assert ("p2_layout" in manifest) == label.startswith("p2")
                slot = generated.fill_slot_data()
                pristine = json.dumps(slot, sort_keys=True)
                distribute_items_restrictive(mw)
                assert mw.can_beat_game() and not mw.get_unfilled_locations()
                recovered = setup_multiworld(world.PikminRandomizerWorld, seed=999999, steps=())
                recovered.re_gen_passthrough = {generated.game: generated.interpret_slot_data(slot)}
                tracker = recovered.worlds[1]
                tracker.generate_early()
                tracker.create_regions(); tracker.create_items(); tracker.set_rules()
                assert tracker.manifest() == manifest
                assert json.dumps(slot, sort_keys=True) == pristine
                assert {l.name: l.address for l in mw.get_locations()} == {
                    l.name: l.address for l in recovered.get_locations()}
                for inventory in ({}, dict.fromkeys(ITEM_IDS, 40)):
                    a, b = CollectionState(mw), CollectionState(recovered)
                    for name, count in inventory.items():
                        for _ in range(count):
                            a.collect(generated.create_item(name), True)
                            b.collect(tracker.create_item(name), True)
                    assert mw.completion_condition[1](a) == recovered.completion_condition[1](b)
                    for location in mw.get_locations():
                        assert location.can_reach(a) == recovered.get_location(location.name, 1).can_reach(b)
                if seed == 1158:
                    destination = output / label
                    destination.mkdir()
                    generated.generate_output(str(destination))
                    exported = json.loads(next(destination.glob("*.pikmin.json")).read_text(encoding="utf-8"))
                    assert exported == manifest and fingerprint(exported) == slot["manifest_fingerprint"]
                    write_json(destination / "manifest.json", exported)
                    write_json(destination / "slot-data.json", slot)
        print("PASS: 12 isolated packaged P1/P2 fills, authoritative UT rules and exported manifests")
    finally:
        os.chdir(old_cwd)


def hello(manifest, run):
    from randomizer.netplay_mirror import is_thelynk
    from randomizer.runner import mirror_fingerprint
    fields = (["THELYNK_HELLO", "1", run.token, mirror_fingerprint(manifest),
               "individual-parts-v1", "squad-checks-v1", "typed-pikmin-v1", "END"]
              if is_thelynk(manifest) else
              ["PIKMIN_HELLO", str(manifest["schema"]), run.token, mirror_fingerprint(manifest),
               *manifest["capabilities"], "END"])
    (run.directory / "hello.txt").write_text(" ".join(fields) + "\n", encoding="ascii", newline="\n")


def ordinary(label, manifest, output):
    from randomizer.catalog import ITEM_IDS, item_pool
    from randomizer.netplay_mirror import export_client_bundle
    from randomizer.runner import NativeRun, NetplayClientRun, native_bootstrap
    from randomizer.session import Session
    from randomizer.tracker import TrackerModel
    host = Session(manifest, output / label / "host")
    host.bind_ap(manifest["seed"], 0, 1)
    host_token, peer_token = token(label + "-host"), token(label + "-peer")
    directory = host.directory / "runs" / host_token
    directory.mkdir(parents=True)
    bootstrap = native_bootstrap(host, host_token)
    (directory / "bootstrap.txt").write_text(bootstrap, encoding="ascii", newline="\n")
    attached = NativeRun.attach(host, directory)
    hello(manifest, attached)
    assert attached.poll() is None and attached.handshaken
    (directory / "initial-state.txt").write_text(host.native_state(host_token, False), encoding="ascii")
    attached.write_state(True)
    before = (directory / "bootstrap.txt").read_bytes()
    bundle = export_client_bundle(manifest, host.directory, peer_token, host_token)
    assert bundle["bootstrap_text"].replace(peer_token, host_token) == bootstrap
    write_json(output / label / "client-bundle.json", bundle)
    mirror_root = output / label / "client"
    client_dir = mirror_root / "runs" / peer_token
    client_dir.mkdir(parents=True)
    (client_dir / "bootstrap.txt").write_text(bundle["bootstrap_text"], encoding="ascii", newline="\n")
    client = NetplayClientRun(manifest, mirror_root, bundle["bootstrap_text"],
                              seed_data=bundle["session_snapshot"], native_directory=client_dir)
    hello(manifest, client)
    assert client.poll() == (0, 0)
    assert TrackerModel(manifest).snapshot(host.data) == TrackerModel(manifest).snapshot_from_dir(client_dir)
    items = [ITEM_IDS[n] for n in item_pool(manifest)]
    host.receive(0, items)
    stream = [f"FRAME {i + 1} RECEIVED {i} {item}" for i, item in enumerate(items)]
    names = host.names
    (directory / "checks.txt").write_text("".join(f"{i}\n" for i in range(len(names))), encoding="ascii")
    attached.poll()
    attached.write_state(True)
    stream += [f"FRAME {len(items) + i + 1} CHECKED {name}" for i, name in enumerate(names)]
    (client_dir / "mirror-events.txt").write_text("\n".join(stream) + "\n", encoding="ascii", newline="\n")
    client.poll()
    assert (client_dir / "state.txt").read_text() == host.native_state(peer_token, True)
    assert client.mirror.load() == host.data
    assert TrackerModel(manifest).snapshot_from_dir(host.directory) == TrackerModel(manifest).snapshot_from_dir(client_dir)
    assert Session(manifest, host.directory).data == host.data
    resumed = NetplayClientRun(manifest, mirror_root, bundle["bootstrap_text"], native_directory=client_dir)
    assert resumed.poll() == (0, 0) and resumed.mirror.load() == host.data
    assert (directory / "bootstrap.txt").read_bytes() == before
    bad = bundle["bootstrap_text"].replace("MATURITY 1", "MATURITY 0")
    refused(lambda: NetplayClientRun(manifest, output / label / "invalid", bad))
    assert not (output / label / "invalid").exists()
    refused(lambda: NativeRun.attach(Session(dict(manifest, seed="foreign"), output / label / "foreign"), directory))
    print(f"PASS: {label} attach/export/mirror/reopen/tracker: {len(names)} checks, {len(items)} receipts")


def thelynk(output, native_names=None, native_events=None):
    from randomizer.compatibility import PART_CROSSWALK
    from randomizer.thelynk import TheLynkSession, PART_ITEMS, BONUSES, LOCATIONS, read_patch
    from randomizer.runner import NetplayClientRun
    from randomizer.netplay_mirror import export_client_bundle
    options = dict.fromkeys(("normal_first_day", "disable_pikmin_trip", "always_min_one_leaf", "day_cycle_mode",
        "ship_part_hint_mode", "death_link", "pikmin_bond", "olimar_bond", "trap_link", "trap_percentage"), 0)
    options.update(skip_events=[], enable_pikmin_locations=1)
    for c in ("red", "yellow", "blue"):
        options[c + "_pikmin_locations_enabled"] = 1
        options[c + "_pikmin_interval"] = 1
    patch = dict(Seed="1158", Slot=1, Name="TheLynkProtocolFixture", Options=options, GameIdSuffix="T58")
    destination = output / "thelynk"
    destination.mkdir()
    archive = destination / "protocol-metadata.appik1"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(zipfile.ZipInfo("patch.appik1", (1980, 1, 1, 0, 0, 0)), json.dumps(patch, sort_keys=True))
    assert read_patch(archive) == patch
    host = TheLynkSession(patch, destination / "host")
    host.bind("W1158", 0, 1)
    assert len(host.locations) == 330 and host.locations == LOCATIONS
    assert len(PART_CROSSWALK) == 30 and set(PART_ITEMS.values()) == set(range(71400, 71430))
    assert len(BONUSES) == 18 and set(BONUSES.values()) == set(range(71800, 71818))
    # Independent item-name golden sequence from upstream P1Data ALL_PARTS.
    names = ("Bowsprit", "Gluon Drive", "Anti-Dioxin Filter", "Eternal Fuel Dynamo", "Main Engine",
        "Whimsical Radar", "Interstellar Radio", "Guard Satellite", "Chronos Reactor", "Radiation Canopy",
        "Geiger Counter", "Sagittarius", "Libra", "Omega Stabilizer", "#1 Ionium Jet", "#2 Ionium Jet",
        "Shock Absorber", "Gravity Jumper", "Pilot's Seat", "Nova Blaster", "Automatic Gear", "Zirconium Rotor",
        "Extraordinary Bolt", "Repair-type Bolt", "Space Float", "Massage Machine", "Secret Safe",
        "Positron Generator", "Analog Computer", "UV Lamp")
    assert PART_ITEMS == {name: 71400 + i for i, name in enumerate(names)}
    assert host.locations["TFN - #1 Ionium Jet"] == 71414
    assert host.locations["TDS - #2 Ionium Jet"] == 71415
    assert host.locations["TIS - Main Engine"] == 71404
    assert host.locations["Red Pikmin: 1"] == 71500 and host.locations["Blue Pikmin: 100"] == 71799
    host_token, peer_token = token("thelynk-host"), token("thelynk-peer")
    directory = host.directory / "runs" / host_token
    directory.mkdir(parents=True)
    (directory / "bootstrap.txt").write_text(host.bootstrap(host_token), encoding="ascii", newline="\n")
    identity = type("Fixture", (), dict(token=host_token, directory=directory))()
    hello(patch, identity)
    assert host.poll(directory)
    (directory / "initial-state.txt").write_text(host.state(host_token, False), encoding="ascii")
    bundle = export_client_bundle(patch, host.directory, peer_token, host_token)
    write_json(destination / "patch.json", patch)
    write_json(destination / "client-bundle.json", bundle)
    mirror_root = destination / "client"
    client = NetplayClientRun(patch, mirror_root, bundle["bootstrap_text"], seed_data=bundle["session_snapshot"])
    hello(patch, client)
    items = sorted(PART_ITEMS.values()) + sorted(BONUSES.values())
    host.receive(0, items)
    host.receive(0, items)  # same AP replay is a no-op
    (directory / "checks.txt").write_text("".join(f"{i}\n" for i in sorted(LOCATIONS.values())), encoding="ascii")
    assert host.poll(directory) and host.goal
    (directory / "state.txt").write_text(host.state(host_token, True), encoding="ascii")
    stream = [f"FRAME {i + 1} RECEIVED {i} {item}" for i, item in enumerate(items)]
    stream += [f"FRAME {len(items) + i + 1} CHECKED {name}" for i, name in enumerate(LOCATIONS)]
    events = client.directory / "mirror-events.txt"
    events.write_text("\n".join(stream) + "\n", encoding="ascii", newline="\n")
    client.poll()
    assert set(client.mirror.load()["checked"]) == set(LOCATIONS.values())
    assert client.mirror.load()["received"] == items
    assert (client.directory / "state.txt").read_text() == host.state(peer_token, True)
    assert TheLynkSession(patch, host.directory).data == host.data
    resumed = NetplayClientRun(patch, mirror_root, bundle["bootstrap_text"])
    assert resumed.poll() == (0, 0)
    before = (client.directory / "mirror.json").read_bytes()
    with events.open("a", encoding="ascii", newline="\n") as f:
        f.write(f"FRAME 1000 RECEIVED {len(items)} 71404\n")
    refused(resumed.poll)
    assert (client.directory / "mirror.json").read_bytes() == before
    # Leave the retained fixture valid for the paired harness.
    events.write_text("\n".join(stream) + "\n", encoding="ascii", newline="\n")
    refused(lambda: NetplayClientRun(dict(patch, Seed="foreign"), destination / "foreign", bundle["bootstrap_text"]))
    assert not (destination / "foreign").exists()
    print("PASS: TheLynk 330 numeric checks, 30 unique parts, 18 bonuses, patch reader, journal/replay/reopen")
    if native_events is not None:
        from randomizer.netplay_mirror import parse_mirror_line
        native_names = [args[0] for _, tag, args in
            (parse_mirror_line(line) for line in native_events.read_text(encoding="ascii").splitlines())
            if tag == "CHECKED"]
        assert len(native_names) >= 30, "compiled emitter journal must cover all thirty ship parts"
        (destination / "observed-native-mirror-events.txt").write_bytes(native_events.read_bytes())
    if native_names is not None:
        # The native writer emits checkName(slot), whose ship-part table uses
        # internal engine aliases. Exercise the actual pinned table independently
        # of the upstream external names used by the fixture above.
        failures = []
        for name in native_names:
            try:
                client.mirror.apply(client.mirror.load(), (1001, "CHECKED", (name,)))
            except ValueError as error:
                failures.append(dict(native_name=name, error=str(error)))
        if native_events is not None and not failures:
            assert set(range(71400, 71430)) <= {LOCATIONS[n] for n in native_names}
        write_json(destination / "native-writer-consumer-mismatches.json", failures)
        return failures
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ap", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--native-sha")
    parser.add_argument("--native-git", type=Path, help="Read the exact native ship-part writer table at --native-sha")
    parser.add_argument("--native-mirror-events", type=Path,
                        help="Validate an observed compiled-emitter CHECKED journal covering all thirty parts")
    parser.add_argument("--package-worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.package_worker:
        packaged(args.ap.resolve(), args.package_worker.resolve(), output)
        return
    if not args.native_sha or len(args.native_sha) != 40 or any(c not in "0123456789abcdef" for c in args.native_sha):
        parser.error("--native-sha must identify the paired harness's exact pushed native source")
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT))
    from scripts.build_apworld import build
    from randomizer.seed import validate
    native_names = None
    if args.native_git:
        source = subprocess.check_output(["git", "-C", str(args.native_git), "show",
            args.native_sha + ":pc_port/pc_randomizer.cpp"], text=True, encoding="utf-8")
        table = re.search(r'const char\* thelynkPartNames\[30\] = \{(.*?)\};', source, re.S)
        if not table:
            raise ValueError("native writer table changed; inspect its actual contract before updating this audit")
        native_names = re.findall(r'"([^"]+)"', table.group(1))
        assert len(native_names) == 30
        assert 'checkName(e.slot)' in source and 'pc_rand_outbox::mirror_checked' in source
        (output / "native-writer-source.txt").write_text(source, encoding="utf-8")
    package = build(output / "pikmin_randomizer.apworld")
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--ap", str(args.ap.resolve()),
                    "--output", str(output / "packaged"), "--package-worker", str(package)], check=True)
    for label in ("p1-default", "p1-receipts", "p2-default", "p2-captains"):
        manifest = json.loads((output / "packaged" / label / "manifest.json").read_text(encoding="utf-8"))
        validate(manifest)
        ordinary(label, manifest, output / "protocol")
    failures = thelynk(output / "protocol", native_names,
                      args.native_mirror_events.resolve() if args.native_mirror_events else None)
    paths = sorted(p for p in output.rglob("*") if p.is_file())
    receipt = dict(schema=1, kind="packaged-consumer-protocol-only", gameplay_accepted=False,
        root_sha=subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        root_dirty=subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True),
        native_sha=args.native_sha, native_executed=False,
        thelynk_patch_kind="synthetic supported metadata; not an upstream generated seed/ISO patch",
        tracker_boundary="P1/P2 host/mirror tracker verified; TheLynk metadata has no local TrackerModel UI",
        native_writer_consumer_checked=native_names is not None,
        compiled_emitter_journal_ingested=bool(args.native_mirror_events),
        native_writer_consumer_failures=len(failures),
        files={str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    write_json(output / "evidence.json", receipt)
    print("PASS: deterministic generated fixture contracts retained; no native engine/assets executed")
    if failures:
        raise SystemExit(f"FAIL: {len(failures)} actual native ship-part aliases are rejected by the mirror consumer")


if __name__ == "__main__":
    main()
