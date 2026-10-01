"""Experimental native client for an explicit subset of TheLynk APWorld v7.

This contract is independent of Pikmin Randomizer manifests and sessions.
Unsupported gameplay options fail before a native process is launched.
"""
import argparse
import asyncio
import hashlib
import json
import os
import secrets
import subprocess
import zipfile
from pathlib import Path
from .compatibility import PART_CROSSWALK, THELYNK_REFERENCE
from .session import SessionLock, atomic_write

GAME = "Pikmin"
PART_ITEMS = {p["thelynk_item"]: p["thelynk_item_id"] for p in PART_CROSSWALK}
LOCATIONS = {p["thelynk_location"]: p["thelynk_location_id"] for p in PART_CROSSWALK}
LOCATIONS.update({f"{color} Pikmin: {n}": 71500 + c * 100 + n - 1
                  for c, color in enumerate(("Red", "Yellow", "Blue")) for n in range(1, 101)})
BONUSES = {f"{count} {color} {stage} Pikmin": 71800 + c * 6 + s * 2 + q
           for c, color in enumerate(("Red", "Yellow", "Blue"))
           for s, stage in enumerate(("Leaf", "Bud", "Flower")) for q, count in enumerate((1, 5))}
ITEMS = {**PART_ITEMS, **BONUSES, **dict(zip(
    ("Time Trap", "End Day Trap", "Damage Trap", "Teleport Trap", "Disbanding Trap", "Trip Immunity", "Trip Trap"),
    range(71818, 71825)))}
SUPPORTED_ITEMS = set(PART_ITEMS.values()) | set(BONUSES.values())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_options(options):
    if type(options) is not dict:
        raise ValueError("TheLynk patch requires Options")
    # Do not silently approximate native behavior or link effects. These options
    # can be supported incrementally without weakening this initial contract.
    for name in ("normal_first_day", "disable_pikmin_trip", "always_min_one_leaf", "day_cycle_mode",
                 "ship_part_hint_mode", "death_link", "pikmin_bond", "olimar_bond", "trap_link",
                 "trap_percentage"):
        if type(options.get(name)) is not int or options[name] != 0:
            raise ValueError(f"native TheLynk mode currently requires {name}: 0")
    if options.get("skip_events") != []:
        raise ValueError("native TheLynk mode currently requires skip_events: []")
    for name in ("enable_pikmin_locations", "red_pikmin_locations_enabled",
                 "yellow_pikmin_locations_enabled", "blue_pikmin_locations_enabled"):
        if type(options.get(name)) is not int or options[name] not in (0, 1):
            raise ValueError("invalid or missing TheLynk option: " + name)
    for color in ("red", "yellow", "blue"):
        n = options.get(color + "_pikmin_interval")
        if type(n) is not int or not 1 <= n <= 100:
            raise ValueError("invalid TheLynk population interval")


def enabled_locations(options):
    validate_options(options)
    result = {p["thelynk_location"]: p["thelynk_location_id"] for p in PART_CROSSWALK}
    if options["enable_pikmin_locations"]:
        for color in ("Red", "Yellow", "Blue"):
            if options[color.lower() + "_pikmin_locations_enabled"]:
                for n in range(options[color.lower() + "_pikmin_interval"], 101,
                               options[color.lower() + "_pikmin_interval"]):
                    name = f"{color} Pikmin: {n}"
                    result[name] = LOCATIONS[name]
    return result


def read_patch(path):
    with zipfile.ZipFile(path) as archive:
        if archive.getinfo("patch.appik1").file_size > 1024 * 1024:
            raise ValueError("TheLynk patch metadata is too large")
        patch = json.loads(archive.read("patch.appik1"))
    if type(patch) is not dict or type(patch.get("Seed")) is not str or not patch["Seed"]:
        raise ValueError("invalid TheLynk seed")
    if type(patch.get("Slot")) is not int or patch["Slot"] < 1 or type(patch.get("Name")) is not str or not patch["Name"]:
        raise ValueError("invalid TheLynk slot identity")
    if type(patch.get("GameIdSuffix")) is not str or len(patch["GameIdSuffix"]) != 3 or not patch["GameIdSuffix"].isascii() or not patch["GameIdSuffix"].isalnum():
        raise ValueError("invalid TheLynk game ID suffix")
    validate_options(patch.get("Options"))
    return {k: patch[k] for k in ("Seed", "Slot", "Name", "Options", "GameIdSuffix")}


def validate_server(patch, slot_data, location_ids):
    if type(slot_data) is not dict or slot_data.get("apworld_version") != 7:
        raise ValueError("native TheLynk mode requires APWorld version 7")
    if slot_data.get("game_id_suffix") != patch["GameIdSuffix"]:
        raise ValueError("TheLynk patch/server seed suffix mismatch")
    # The server exposes these resolved options; compare all that are present.
    for name, value in patch["Options"].items():
        if name in slot_data and slot_data[name] != value:
            raise ValueError("TheLynk patch/server option mismatch: " + name)
    for name in ("normal_first_day", "disable_pikmin_trip", "skip_events", "always_min_one_leaf",
                 "day_cycle_mode", "ship_part_hint_mode", "death_link", "pikmin_bond", "olimar_bond",
                 "trap_link", "enable_pikmin_locations", "red_pikmin_locations_enabled",
                 "yellow_pikmin_locations_enabled", "blue_pikmin_locations_enabled",
                 "red_pikmin_interval", "yellow_pikmin_interval", "blue_pikmin_interval"):
        if name not in slot_data or slot_data[name] != patch["Options"][name]:
            raise ValueError("missing or mismatched TheLynk server option: " + name)
    if set(location_ids) != set(enabled_locations(patch["Options"]).values()):
        raise ValueError("TheLynk server check set differs from patch")


def session_fingerprint(patch):
    return digest(dict(contract="thelynk-v7-native-v1", patch=patch, reference=THELYNK_REFERENCE))


def initial_session_data(patch):
    enabled_locations(patch["Options"])
    return dict(kind="thelynk-v7-native-v1", fingerprint=session_fingerprint(patch),
                identity=None, received=[], checked=[])


def validate_session_data(patch, value):
    expected = initial_session_data(patch)
    if type(value) is not dict or set(value) != set(expected) or value["kind"] != expected["kind"] or value["fingerprint"] != session_fingerprint(patch):
        raise ValueError("foreign session; use a separate TheLynk session directory")
    if type(value["received"]) is not list or any(type(i) is not int or i not in SUPPORTED_ITEMS for i in value["received"]):
        raise ValueError("invalid TheLynk receipts")
    if type(value["checked"]) is not list or any(type(i) is not int or i not in enabled_locations(patch["Options"]).values() for i in value["checked"]) or len(set(value["checked"])) != len(value["checked"]):
        raise ValueError("invalid TheLynk checks")
    if value["identity"] is not None and (type(value["identity"]) is not list or len(value["identity"]) != 3
            or value["identity"][0] != patch["Seed"] or type(value["identity"][1]) is not int
            or value["identity"][2] != patch["Slot"]):
        raise ValueError("invalid saved TheLynk identity")
    return True


def render_session_state(data, token, ready):
    parts = sum(1 << (i - 71400) for i in data["received"] if i in PART_ITEMS.values())
    checked = sorted(data["checked"])
    counts = [data["received"].count(i) for i in range(71800, 71818)]
    return (f"THELYNK_STATE 1 {token} {int(ready)} {parts} CHECKS {len(checked)} "
            + " ".join(map(str, checked)) + " BONUSES " + " ".join(map(str, counts)) + " END\n")


class TheLynkSession:
    def __init__(self, patch, directory):
        self.patch = patch
        self.directory = Path(directory)
        self.path = self.directory / "session.json"
        self.locations = enabled_locations(patch["Options"])
        self.fingerprint = session_fingerprint(patch)
        self.data = initial_session_data(patch)
        if self.path.exists():
            value = json.loads(self.path.read_text(encoding="utf-8"))
            validate_session_data(patch, value)
            self.data = value
        for journal in self.directory.glob("runs/*/checks.txt"):
            self.poll(journal.parent)

    def save(self):
        atomic_write(self.path, json.dumps(self.data, indent=2) + "\n")

    def server_checks(self, ids):
        if self.data["identity"] is None or type(ids) is not list or any(type(i) is not int or i not in self.locations.values() for i in ids):
            raise ValueError("invalid TheLynk server checks")
        for i in ids:
            if i not in self.data["checked"]:
                self.data["checked"].append(i)
        self.save()

    def bind(self, seed, team, slot):
        normalized = seed[1:] if seed.startswith("W") else seed
        identity = [normalized, team, slot]
        if normalized != self.patch["Seed"] or type(team) is not int or type(slot) is not int or slot != self.patch["Slot"] or self.data["identity"] not in (None, identity):
            raise ValueError("TheLynk room/team/slot mismatch")
        self.data["identity"] = identity
        self.save()

    def receive(self, index, items):
        if self.data["identity"] is None:
            raise ValueError("TheLynk receipts before authentication")
        old = self.data["received"]
        if type(index) is not int or not 0 <= index <= len(old):
            raise ValueError("TheLynk item stream gap")
        if type(items) is not list or any(type(i) is not int or i not in SUPPORTED_ITEMS for i in items):
            raise ValueError("unsupported TheLynk item; traps and Trip Immunity require future native support")
        overlap = min(len(old) - index, len(items))
        if old[index:index + overlap] != items[:overlap]:
            raise ValueError("TheLynk item replay conflict")
        if len(old) + len(items) - overlap > len(self.locations):
            raise ValueError("too many TheLynk receipts")
        merged = old + items[overlap:]
        parts = [i for i in merged if i in PART_ITEMS.values()]
        if len(set(parts)) != len(parts):
            raise ValueError("duplicate unique TheLynk ship part")
        self.data["received"] = merged
        self.save()

    @property
    def goal(self):
        return set(PART_ITEMS.values()) <= set(self.data["received"])

    def bootstrap(self, token):
        ids = sorted(self.locations.values())
        return (f"PIKMIN_THELYNK 1\nSESSION {token}\nFINGERPRINT {self.fingerprint}\n"
                f"CHECKS {len(ids)} " + " ".join(map(str, ids)) + "\nEND\n")

    def state(self, token, ready):
        return render_session_state(self.data, token, ready)

    def poll(self, directory):
        directory = Path(directory)
        if (directory / "bootstrap.txt").read_text(encoding="ascii") != self.bootstrap(directory.name):
            raise ValueError("foreign TheLynk native journal")
        expected = f"THELYNK_HELLO 1 {directory.name} {self.fingerprint} individual-parts-v1 squad-checks-v1 typed-pikmin-v1 END\n"
        if not (directory / "hello.txt").exists():
            if (directory / "checks.txt").exists():
                raise ValueError("unauthenticated TheLynk native journal")
            return False
        if (directory / "hello.txt").read_text(encoding="ascii") != expected:
            raise ValueError("TheLynk native capability handshake mismatch")
        if (directory / "checks.txt").exists():
            data = (directory / "checks.txt").read_bytes()
            for line in data[:data.rfind(b"\n") + 1].splitlines():
                if not line.isdigit() or int(line) not in self.locations.values():
                    raise ValueError("invalid TheLynk native check")
                if int(line) not in self.data["checked"]:
                    self.data["checked"].append(int(line))
                    self.save()
        return True


async def play(session, server, exe, assets, attached_directory=None):
    import websockets
    if not server.startswith(("ws://", "wss://")):
        server = "ws://" + server
    token = secrets.token_hex(32)
    directory = session.directory / "runs" / token
    attached = attached_directory is not None
    if attached:
        directory = Path(attached_directory).resolve(strict=True)
        token = directory.name
        from .netplay_mirror import run_dir_for
        if directory != run_dir_for(session.directory.resolve(), token):
            raise ValueError("attached TheLynk run differs from session root")
        if (directory / "bootstrap.txt").read_text(encoding="ascii") != session.bootstrap(token):
            raise ValueError("attached TheLynk bootstrap differs from complete patch")
    process = log = None
    goal_sent = False
    try:
        while process is None or process.poll() is None:
            connected = False
            try:
                async with websockets.connect(server) as ws:
                    connected = True
                    seed = None
                    authenticated = synced = package_ok = False
                    sent = set()
                    while process is None or process.poll() is None:
                        try:
                            packets = json.loads(await asyncio.wait_for(ws.recv(), .1))
                        except asyncio.TimeoutError:
                            packets = []
                        for packet in packets:
                            cmd = packet.get("cmd")
                            if cmd == "RoomInfo":
                                seed = packet["seed_name"]
                                await ws.send(json.dumps([dict(cmd="Connect", game=GAME, name=session.patch["Name"],
                                    password=os.getenv("PIKMIN_AP_PASSWORD"), uuid=session.fingerprint,
                                    version=dict(major=0, minor=6, build=7, **{"class": "Version"}),
                                    items_handling=7, tags=["AP"], slot_data=True)]))
                            elif cmd == "ConnectionRefused":
                                raise ValueError("TheLynk connection refused: " + str(packet.get("errors")))
                            elif cmd == "Connected":
                                validate_server(session.patch, packet.get("slot_data"), packet["checked_locations"] + packet["missing_locations"])
                                session.bind(seed, packet["team"], packet["slot"])
                                authenticated = True
                                session.server_checks(packet["checked_locations"])
                                await ws.send(json.dumps([dict(cmd="GetDataPackage", games=[GAME]), dict(cmd="Sync")]))
                            elif cmd == "DataPackage":
                                game = packet["data"]["games"].get(GAME, {})
                                if game.get("item_name_to_id") != ITEMS or game.get("location_name_to_id") != LOCATIONS:
                                    raise ValueError("TheLynk data package differs from pinned v7 identities")
                                package_ok = True
                            elif cmd == "RoomUpdate" and "checked_locations" in packet:
                                session.server_checks(packet["checked_locations"])
                            elif cmd == "ReceivedItems":
                                before = len(session.data["received"])
                                session.receive(packet["index"], [i["item"] for i in packet["items"]])
                                if packet["index"] == 0 and len(packet["items"]) >= before:
                                    synced = True
                        ready = authenticated and synced and package_ok
                        if ready and process is None and not attached:
                            directory.mkdir(parents=True)
                            atomic_write(directory / "bootstrap.txt", session.bootstrap(token))
                            atomic_write(directory / "state.txt", session.state(token, False))
                            import _winapi
                            _winapi.CreateJunction(str(assets), str(directory / "assets"))
                            env = dict(os.environ)
                            env.pop("BBFT_PORT", None)
                            log = (directory / "native.log").open("w", encoding="utf-8")
                            process = subprocess.Popen([str(exe), "--randomizer-seed", str(directory / "bootstrap.txt")],
                                                       cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)
                            print(f"TheLynk native session: {directory}", flush=True)
                        if attached or process is not None:
                            handshaken = session.poll(directory)
                            atomic_write(directory / "state.txt", session.state(token, ready and handshaken))
                            pending = set(session.data["checked"]) - sent
                            if ready and pending:
                                await ws.send(json.dumps([dict(cmd="LocationChecks", locations=sorted(pending))]))
                                sent |= pending
                            if ready and session.goal and not goal_sent:
                                await ws.send(json.dumps([dict(cmd="StatusUpdate", status=30)]))
                                goal_sent = True
            except (OSError, websockets.ConnectionClosed) as exc:
                if connected and isinstance(exc, OSError):
                    raise  # Local file/process failures are not network reconnects.
                if attached or process is not None:
                    atomic_write(directory / "state.txt", session.state(token, False))
                print(f"TheLynk reconnecting: {exc}", flush=True)
                await asyncio.sleep(1)
                goal_sent = False
        if process.returncode:
            raise RuntimeError(f"native exited {process.returncode}; see {directory / 'native.log'}")
    finally:
        if attached:
            atomic_write(directory / "state.txt", session.state(token, False))
        if process is not None:
            try:
                session.poll(directory)
            finally:
                atomic_write(directory / "state.txt", session.state(token, False))
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
        if log:
            log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch", type=Path, help="TheLynk-generated .appik1")
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--server")
    parser.add_argument("--netplay-client", action="store_true", help="Ingest host mirror only; no AP connection")
    parser.add_argument("--bootstrap", type=Path)
    parser.add_argument("--mirror-dir", type=Path)
    parser.add_argument("--attach-native-run", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--assets", type=Path)
    args = parser.parse_args()
    patch = read_patch(args.patch)
    if args.attach_native_run:
        if args.exe or args.assets or args.bootstrap:
            raise ValueError("attach uses the existing native process/bootstrap/assets")
        if args.netplay_client:
            if args.server:
                raise ValueError("client attach never contacts AP")
            from .runner import attach_native_client
            attach_native_client(patch, args.attach_native_run)
        else:
            if not args.server:
                raise ValueError("TheLynk host attach requires --server")
            with SessionLock(args.session_dir):
                session = TheLynkSession(patch, args.session_dir.resolve())
                asyncio.run(play(session, args.server, None, None, args.attach_native_run))
        return
    if args.exe is None or args.assets is None:
        raise ValueError("ordinary TheLynk launch requires --exe and --assets")
    exe, assets = args.exe.resolve(strict=True), args.assets.resolve(strict=True)
    if not (assets / "dataDir/stages").is_dir():
        raise ValueError("assets must contain dataDir/stages")
    if args.netplay_client:
        if args.server or args.bootstrap is None:
            raise ValueError("TheLynk mirror requires --bootstrap and no --server")
        from .runner import launch_netplay_client
        launch_netplay_client(patch, args.session_dir.resolve(), args.bootstrap.read_text(encoding="ascii"),
                              args.mirror_dir, exe, assets)
        return
    if not args.server:
        raise ValueError("TheLynk host requires --server")
    with SessionLock(args.session_dir):
        session = TheLynkSession(patch, args.session_dir.resolve())
        asyncio.run(play(session, args.server, exe, assets))


if __name__ == "__main__":
    main()
