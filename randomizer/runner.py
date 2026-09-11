"""Local file-IPC runner. Every launch has a private token and journal directory."""
import asyncio
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from .catalog import GAME, NAMES, LOCATION_IDS
from .seed import fingerprint
from .stats import bootstrap_stats
from .enemy_slots import bootstrap_slots, verify_source_assets
from .session import Session, SessionLock, atomic_write


class NativeRun:
    def __init__(self, session):
        self.session = session
        self.token = secrets.token_hex(32)
        self.directory = session.directory / "runs" / self.token
        self.directory.mkdir(parents=True)
        self.bootstrap = self.directory / "bootstrap.txt"
        atomic_write(self.bootstrap, f"PIKMIN_RANDOMIZER {session.manifest['schema']}\n" +
                     f"SESSION {self.token}\nFINGERPRINT {session.fingerprint}\n" +
                     f"PROFILE {session.manifest['profile']}\nCATALOG {session.manifest['catalog']}\nPLACEMENT identity-v1\n" +
                     "GOAL 25\nDAYS repeat-day29-v1\n" +
                     (f"COLOR {session.manifest['starting_color']}\n" if session.manifest['schema'] >= 4 else '') +
                     (f"CHECKSET {int(session.manifest['permanent_checks']) + 2 * int(session.manifest.get('no_exploration', False)) + 4 * int(session.manifest.get('color_population', False))}\n" if session.manifest['schema'] >= 9 else '') + (f"ENEMIES {session.manifest['enemy_mask']}\n" if session.manifest['schema'] >= 6 else '') + (f"STARTING_FLARLIC {session.manifest['starting_flarlic']}\n" if "starting_flarlic" in session.manifest else "") + bootstrap_stats(session.manifest) + ("PROGRESSIVE_STATS 1\n" if session.manifest.get("progressive_color_stats") else "") + ("BENEFITS 1\n" if session.manifest.get("benefit_items") else "") + bootstrap_slots(session.manifest) + "END\n")
        self.seen = 0
        self.handshaken = False
        self.write_state(False)

    def write_state(self, ready):
        atomic_write(self.directory / "state.txt", self.session.native_state(self.token, ready))

    def poll(self):
        hello = self.directory / "hello.txt"
        if not self.handshaken and hello.exists():
            fields = hello.read_text(encoding="ascii").split()
            if fields != ["PIKMIN_HELLO", str(self.session.manifest["schema"]), self.token, self.session.fingerprint,
                          *self.session.manifest["capabilities"], "END"]:
                raise ValueError("native adapter capability or session handshake mismatch")
            self.handshaken = True
        journal = self.directory / "checks.txt"
        if self.handshaken and journal.exists():
            data = journal.read_bytes()
            # Ignore an incomplete final record while the native writer flushes.
            lines = data[:data.rfind(b"\n") + 1].splitlines()
            if len(lines) < self.seen:
                raise ValueError("native check journal was truncated")
            for line in lines[self.seen:]:
                if not line.isdigit() or not 0 <= int(line) < len(self.session.names):
                    raise ValueError("invalid native check journal")
                self.session.collect(self.session.names[int(line)])
                self.seen += 1


async def ap_connect(session, server, password, ready):
    import websockets
    if not server.startswith(("ws://", "wss://")):
        server = "ws://" + server
    async with websockets.connect(server) as ws:
        authenticated = False
        room_seed = None
        sent = set()
        goal_sent = False
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), 0.2)
            except asyncio.TimeoutError:
                raw = None
            if raw is not None:
                for packet in json.loads(raw):
                    cmd = packet.get("cmd")
                    if cmd == "RoomInfo":
                        room_seed = packet["seed_name"]
                        await ws.send(json.dumps([dict(cmd="Connect", game=GAME,
                            name=session.manifest["slot"], password=password,
                            uuid=session.fingerprint, version=dict(major=0, minor=6, build=0, **{"class": "Version"}),
                            items_handling=7, tags=["AP"], slot_data=True)]))
                    elif cmd == "ConnectionRefused":
                        raise ValueError("AP connection refused: " + str(packet.get("errors")))
                    elif cmd == "Connected":
                        data = packet.get("slot_data", {})
                        if data.get("manifest_fingerprint") != session.fingerprint or data.get("manifest") != session.manifest:
                            raise ValueError("AP slot manifest does not match this seed")
                        session.bind_ap(room_seed, packet["team"], packet["slot"])
                        authenticated = True
                        # Do not release the native game until the authoritative
                        # item stream has been reconciled, including an empty stream.
                        await ws.send(json.dumps([{"cmd": "Sync"}]))
                    elif cmd == "ReceivedItems":
                        if not authenticated:
                            raise ValueError("AP sent items before slot authentication")
                        session.receive(packet["index"], [item["item"] for item in packet["items"]])
                        ready[0] = True
            if authenticated and ready[0]:
                pending = set(session.data["checked"]) - sent
                if pending:
                    await ws.send(json.dumps([dict(cmd="LocationChecks", locations=[session.manifest["locations"][n] for n in sorted(pending)])]))
                    sent.update(pending)
                if session.goal and not goal_sent:
                    await ws.send(json.dumps([dict(cmd="StatusUpdate", status=30)]))
                    goal_sent = True


async def serve(session, run, process=None, server=None, password=None):
    ready = [session.manifest["mode"] == "solo"]
    task = None
    if session.manifest["mode"] == "ap":
        if not server:
            raise ValueError("AP mode requires --server")
        async def reconnect():
            import websockets
            while True:
                try:
                    await ap_connect(session, server, password, ready)
                except (OSError, websockets.ConnectionClosed) as exc:
                    ready[0] = False
                    print(f"AP disconnected: {exc}; retrying", flush=True)
                    await asyncio.sleep(2)
                # Configuration/protocol ValueErrors are fatal, not retries.
        task = asyncio.create_task(reconnect())
    previous_goal = False
    try:
        while process is None or process.poll() is None:
            if task is not None and task.done():
                await task
            run.poll()
            run.write_state(run.handshaken and ready[0])
            if session.goal and not previous_goal:
                print("PIKMIN_RANDOMIZER_GOAL: ship repaired", flush=True)
                previous_goal = True
            await asyncio.sleep(0.1)
    finally:
        try:
            run.poll()
        finally:
            run.write_state(False)
            if task:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


def launch(manifest, session_dir, exe=None, assets=None, server=None):
    with SessionLock(session_dir):
        return _launch(manifest, session_dir, exe, assets, server)


def _launch(manifest, session_dir, exe=None, assets=None, server=None):
    if manifest["mode"] == "ap" and not server:
        raise ValueError("AP mode requires --server")
    session = Session(manifest, session_dir)
    run = NativeRun(session)
    process = None
    overlay = None
    log = None
    if exe:
        exe = Path(exe).resolve(strict=True)
        if not assets or not (Path(assets) / "dataDir" / "stages").is_dir():
            raise ValueError("--assets must point to the extracted assets directory containing dataDir/stages/")
        if 'spawn_layout' in manifest: verify_source_assets(assets)
        # Windows directory junction, only into the new private runtime directory.
        target = run.directory / "assets"
        import _winapi
        _winapi.CreateJunction(str(Path(assets).resolve()), str(target.resolve()))
        env = dict(os.environ)
        env.pop("BBFT_PORT", None)
        log = (run.directory / "native.log").open("w", encoding="utf-8")
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 1  # Win32 SW_SHOWNORMAL; not exported by subprocess.
        process = subprocess.Popen([str(exe), "--randomizer-seed", str(run.bootstrap.resolve())],
            cwd=run.directory, env=env, stdout=log, stderr=subprocess.STDOUT, startupinfo=startup)
        overlay_manifest = run.directory / 'overlay-manifest.json'
        atomic_write(overlay_manifest, json.dumps(manifest))
        try:
            overlay = subprocess.Popen([sys.executable, '-m', 'randomizer.overlay',
                '--manifest', str(overlay_manifest.resolve()), '--session-dir', str(session_dir.resolve()),
                '--pid', str(process.pid)], cwd=Path(__file__).resolve().parents[1],
                stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as exc:
            print(f'Overlay unavailable: {exc}', flush=True)
    print(f"Native bootstrap: {run.bootstrap.resolve()}", flush=True)
    try:
        asyncio.run(serve(session, run, process, server, os.getenv("PIKMIN_AP_PASSWORD")))
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        if log:
            if overlay and overlay.poll() is None:
                overlay.terminate()
                overlay.wait(timeout=5)
            log.close()
    if process and process.returncode:
        raise RuntimeError(f"native process exited {process.returncode}; see {run.directory / 'native.log'}")
