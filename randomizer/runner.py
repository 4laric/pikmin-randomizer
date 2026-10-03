"""Local file-IPC runner. Every launch has a private token and journal directory."""
import asyncio
import copy
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from .catalog import GAME, NAMES, LOCATION_IDS
from .netplay_mirror import (
    BOOTSTRAP_FILENAME,
    CARD_DIRNAME,
    EVENTS_FILENAME,
    HELLO_FILENAME,
    INGEST_FILENAME,
    MIRROR_FILENAME,
    SAVE_RESULT_FILENAME,
    STATE_FILENAME,
    MirrorStore,
    is_thelynk,
    mirror_fingerprint,
    mirror_dir_for,
    parse_mirror_line,
    render_mirror_state,
    run_dir_for,
)
from .enemy_catalog import bootstrap as bootstrap_enemy_checks
from .seed import fingerprint
from .stats import bootstrap_stats
from .enemy_slots import bootstrap_slots, verify_source_assets
from .session import Session, SessionLock, atomic_write


def native_bootstrap(session, token, purple_campaign=False):
    white = session.manifest.get("p2_white_campaign", False)
    treasure = session.manifest.get("p2_white_treasure_campaign", False)
    if type(white) is not bool or type(treasure) is not bool or (treasure and not white) or (white and (not session.manifest.get("p2_layout") or session.manifest.get("p2_purple_campaign") is not True)):
        raise ValueError("White bootstrap requires an explicit P2/Purple/White manifest")
    purple_campaign = bool(purple_campaign or white)
    body = ( f"PIKMIN_RANDOMIZER {session.manifest['schema']}\n" +
                     f"SESSION {token}\nFINGERPRINT {session.fingerprint}\n" +
                     f"PROFILE {session.manifest['profile']}\nCATALOG {session.manifest['catalog']}\nPLACEMENT identity-v1\n" +
                     ("GOAL emperor25\n" if session.manifest.get("goal_mode") == "emperor_bulblax" else "GOAL 25\n") + "DAYS repeat-day29-v1\n" +
                     (f"COLOR {session.manifest['starting_color']}\n" if session.manifest['schema'] >= 4 else '') +
                     (f"CHECKSET {int(session.manifest['permanent_checks']) + 2 * int(session.manifest.get('no_exploration', False)) + 4 * int(session.manifest.get('color_population', False)) + 8 * int(session.manifest.get('compact_population', False)) + 16 * int(session.manifest.get('no_sticks', False))}\n" if session.manifest['schema'] >= 9 else '') + (f"ENEMIES {session.manifest['enemy_mask']}\n" if session.manifest['schema'] >= 6 else '') + (f"STARTING_FLARLIC {session.manifest['starting_flarlic']}\n" if "starting_flarlic" in session.manifest else "") + bootstrap_stats(session.manifest) + ("PROGRESSIVE_STATS " + ("2" if "progressive-color-stats-v2" in session.manifest["capabilities"] else "1") + "\n" if session.manifest.get("progressive_color_stats") else "") + (("BENEFITS " + str(1 + int(bool(session.manifest.get("bomb_rock_weight"))) + 2 * int(bool(session.manifest.get("combined_captain"))) + 4 * int(bool(session.manifest.get("bomb_trap_weight"))) + 8 * int(bool(session.manifest.get("progg_trap_weight"))) + 16 * int(bool(session.manifest.get("prerelease_trap_weight")))) + "\n") if session.manifest.get("benefit_items") else "") + ("MATURITY 1\n" if session.manifest.get("progressive_maturity") else "") + (f"DAY_LENGTH {session.manifest['progressive_day_length']} {session.manifest['day_length_step']}\n" if session.manifest.get("progressive_day_length") else "") + ("WHISTLE_PLUCK 1\n" if session.manifest.get("whistle_pluck_item") else "") + (f"DEATHLINK {session.death_link_unit}\n" if session.death_link_unit else "") + bootstrap_slots(session.manifest) + bootstrap_enemy_checks(session.manifest) + ("PURPLE 1\n" if purple_campaign else "") + ("WHITE 1\n" if white else "") + ("WHITE_TREASURE 1\n" if treasure else "") + ("CAPTAINS 2\n" if session.manifest.get("p2_second_captain") else "") + "END\n")
    if 'generated_cave' in session.manifest:
        from .cave_campaign import bootstrap_contract
        from .catalog import active_names
        cave = bootstrap_contract(session.manifest['generated_cave'],
                                  session.manifest['seed'], session.manifest['slot'],
                                  active_names(session.manifest))
        body = body.removesuffix('END\n') + cave + 'END\n'
    return body


class NativeRun:
    def __init__(self, session, purple_campaign=False):
        purple_campaign = bool(purple_campaign or session.manifest.get("p2_white_campaign"))
        if purple_campaign and not session.manifest.get("p2_layout"):
            raise ValueError("Purple campaign requires a P2 enemy seed")
        self.purple_campaign = bool(purple_campaign)
        self.session = session
        self.token = secrets.token_hex(32)
        self.directory = session.directory / "runs" / self.token
        self.directory.mkdir(parents=True)
        self.bootstrap = self.directory / "bootstrap.txt"
        atomic_write(self.bootstrap, native_bootstrap(session, self.token, self.purple_campaign))
        self.seen = 0
        self.deaths_seen = 0
        self.handshaken = False
        self.write_state(False)

    @classmethod
    def attach(cls, session, directory):
        directory = Path(directory).resolve(strict=True)
        bootstrap = directory / "bootstrap.txt"
        token = directory.name
        run_dir_for(directory.parent.parent, token)  # strict token grammar
        if directory.parent.parent != session.directory.resolve():
            raise ValueError("attached host session must be native-created session root")
        text = bootstrap.read_text(encoding="ascii")
        purple = bool(session.manifest.get("p2_purple_campaign"))
        if text != native_bootstrap(session, token, purple):
            raise ValueError("attached bootstrap differs from complete host manifest")
        obj = cls.__new__(cls)
        obj.session = session; obj.token = token; obj.directory = directory
        obj.bootstrap = bootstrap; obj.purple_campaign = purple
        obj.seen = 0; obj.handshaken = False
        # Native ICE creates exactly one run per private session root. Its
        # cumulative death journal is an absolute watermark on host reattach.
        obj.deaths_seen = session.data.get("pikmin_deaths", 0)
        return obj

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
        if self.handshaken:
            self.session.recover_emperor(self.directory)
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
        deaths = self.directory / "deaths.txt"
        if self.handshaken and self.session.death_link_unit and deaths.exists():
            # Each line is this run's running count of ordinary Pikmin deaths.
            data = deaths.read_bytes()
            lines = data[:data.rfind(b"\n") + 1].splitlines()
            if lines:
                if not lines[-1].isdigit() or int(lines[-1]) < self.deaths_seen or len(lines) != int(lines[-1]):
                    raise ValueError("invalid native death journal")
                total = int(lines[-1])
                self.session.record_deaths(total - self.deaths_seen)
                self.deaths_seen = total


class APConnectionRefused(ValueError):
    """Credentials may be corrected through the launcher's private input pipe."""


def connection_updates(stream):
    """Read GUI reconnect requests from stdin; the daemon cannot block shutdown."""
    import queue
    import threading
    updates = queue.Queue(maxsize=1)
    def read():
        for line in stream:
            try:
                command = json.loads(line)
                if (not isinstance(command, dict) or set(command) != {"server", "password"}
                        or not isinstance(command["server"], str) or not command["server"].strip()
                        or command["password"] is not None and not isinstance(command["password"], str)):
                    continue
                try:
                    updates.get_nowait()
                except queue.Empty:
                    pass
                updates.put_nowait(command)
            except (ValueError, queue.Full):
                pass
    threading.Thread(target=read, daemon=True).start()
    return updates


async def ap_connect(session, server, password, ready):
    import websockets
    if not server.startswith(("ws://", "wss://")):
        server = "ws://" + server
    import time
    unit = session.death_link_unit
    async with websockets.connect(server) as ws:
        authenticated = False
        room_seed = None
        sent = set()
        goal_sent = False
        # Links accumulated while offline are not replayed on (re)connect.
        links_sent = session.data["pikmin_deaths"] // unit if unit else 0
        sent_times = set()
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
                            items_handling=7, tags=["AP", "DeathLink"] if unit else ["AP"], slot_data=True)]))
                    elif cmd == "ConnectionRefused":
                        raise APConnectionRefused("AP connection refused: " + str(packet.get("errors")))
                    elif cmd == "Connected":
                        data = packet.get("slot_data", {})
                        if data.get("manifest_fingerprint") != session.fingerprint or data.get("manifest") != session.manifest:
                            raise ValueError("AP slot manifest does not match this seed")
                        session.bind_ap(room_seed, packet["team"], packet["slot"])
                        authenticated = True
                        # Do not release the native game until the authoritative
                        # item stream has been reconciled. A real server answers Sync
                        # only when items exist, so the Get reply (processed in order
                        # after any ReceivedItems) marks an empty stream as reconciled.
                        await ws.send(json.dumps([{"cmd": "Sync"}, {"cmd": "Get", "keys": []}]))
                    elif cmd == "ReceivedItems":
                        if not authenticated:
                            raise ValueError("AP sent items before slot authentication")
                        session.receive(packet["index"], [item["item"] for item in packet["items"]])
                        if not ready[0]:
                            print("PIKMIN_AP_STATUS: connected", flush=True)
                        ready[0] = True
                    elif cmd == "Retrieved":
                        if authenticated:
                            if not ready[0]:
                                print("PIKMIN_AP_STATUS: connected", flush=True)
                            ready[0] = True
                    elif cmd == "Bounced" and unit and "DeathLink" in packet.get("tags", []):
                        data = packet.get("data") or {}
                        # Skip our own echoes; the server bounces to every DeathLink client.
                        if authenticated and data.get("time") not in sent_times and data.get("source") != session.manifest["slot"]:
                            session.receive_death_link()
                            print(f"DeathLink received from {data.get('source')}: {data.get('cause', '')}", flush=True)
            if authenticated and ready[0]:
                while unit and session.data["pikmin_deaths"] // unit > links_sent:
                    links_sent += 1
                    stamp = time.time()
                    sent_times.add(stamp)
                    await ws.send(json.dumps([dict(cmd="Bounce", tags=["DeathLink"], data=dict(
                        time=stamp, source=session.manifest["slot"], cause=f"{session.manifest['slot']} lost {unit} Pikmin"))]))
                pending = set(session.data["checked"]) - sent
                if pending:
                    await ws.send(json.dumps([dict(cmd="LocationChecks", locations=[session.manifest["locations"][n] for n in sorted(pending)])]))
                    sent.update(pending)
                if session.goal and not goal_sent:
                    await ws.send(json.dumps([dict(cmd="StatusUpdate", status=30)]))
                    goal_sent = True


def describe_native_exit(log_path, tail_bytes=65536):
    """Say why the native process ended, from what it left in native.log.

    The native exe writes a "[PC Port Fatal] ..." line for every death it can
    observe (unhandled exception, abort, terminate, console close) and an
    "orderly process exit" line when the CRT exit chain runs. A log that ends
    with neither was terminated from outside: taskkill /F, Stop-Process and
    Popen.terminate() all report exit code 1, and no process can log its own
    TerminateProcess. (Exes built before the markers existed also look like
    this.)
    """
    try:
        with open(log_path, 'rb') as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - tail_bytes))
            lines = handle.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return 'native.log unreadable'
    fatal = [line for line in lines if line.startswith('[PC Port Fatal]')]
    if fatal:
        return 'native reported: ' + fatal[-1]
    if any('orderly process exit' in line for line in lines):
        return 'the game exited on its own through its normal exit path'
    return ('no fatal message and no orderly-exit marker: the process was most likely terminated '
            'from outside (taskkill /F, Stop-Process or another tool report exit code 1), '
            'or this exe predates the exit markers')


async def serve(session, run, process=None, server=None, password=None, updates=None):
    ready = [session.manifest["mode"] == "solo"]
    task = None
    if session.manifest["mode"] == "ap":
        if not server:
            raise ValueError("AP mode requires --server")
        async def reconnect():
            nonlocal server
            import websockets
            from websockets.exceptions import InvalidHandshake
            while True:
                try:
                    await ap_connect(session, server, password, ready)
                except APConnectionRefused:
                    if updates is None:
                        raise
                    ready[0] = False
                    print("PIKMIN_AP_STATUS: refused", flush=True)
                    # Wait for corrected credentials; do not repeatedly submit them.
                    await asyncio.Future()
                except InvalidHandshake:
                    ready[0] = False
                    if not server.startswith(("ws://", "wss://")):
                        server = "wss://" + server
                        print("AP connection handshake failed. Trying a secure connection (wss://)…", flush=True)
                        continue
                    print("AP connection handshake failed. Check the server address and port, "
                          "whether it requires ws:// or wss://, and that the room is running; "
                          "retrying in 2 seconds.", flush=True)
                    await asyncio.sleep(2)
                except (OSError, asyncio.TimeoutError, websockets.ConnectionClosed) as exc:
                    ready[0] = False
                    print(f"AP disconnected: {exc}; retrying", flush=True)
                    await asyncio.sleep(2)
                # Configuration/protocol ValueErrors are fatal, not retries.
        task = asyncio.create_task(reconnect())
    previous_goal = False
    try:
        while process is None or process.poll() is None:
            if updates is not None and task is not None:
                import queue
                try:
                    command = updates.get_nowait()
                except queue.Empty:
                    command = None
                if command is not None:
                    # Preserve fatal protocol/manifest failures even if a request races them.
                    if task.done():
                        await task
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    ready[0] = False
                    run.write_state(False)
                    server, password = command["server"], command["password"]
                    print("PIKMIN_AP_STATUS: connecting", flush=True)
                    task = asyncio.create_task(reconnect())
            if task is not None and task.done():
                await task
            run.poll()
            run.write_state(run.handshaken and ready[0])
            if session.goal and not previous_goal:
                print("PIKMIN_RANDOMIZER_GOAL: seed complete", flush=True)
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


def launch(manifest, session_dir, exe=None, assets=None, server=None, content_manifest=None,
           family_install=None, family_source=None, family_actors=None,
           p2_content=None, p2_actors=None, purple_bank=None, purple_motion=None, white_bank=None):
    with SessionLock(session_dir):
        return _launch(manifest, session_dir, exe, assets, server, content_manifest,
                       family_install, family_source, family_actors, p2_content, p2_actors, purple_bank, purple_motion, white_bank)


def _launch(manifest, session_dir, exe=None, assets=None, server=None, content_manifest=None,
            family_install=None, family_source=None, family_actors=None,
            p2_content=None, p2_actors=None, purple_bank=None, purple_motion=None, white_bank=None):
    if manifest["mode"] == "ap" and not server:
        raise ValueError("AP mode requires --server")
    staged_paths = [path for path in (content_manifest, family_install, p2_content) if path is not None]
    if len(staged_paths) > 1:
        raise ValueError("--content-manifest, --family-install and --p2-content own the private asset tree; use exactly one")
    if exe and manifest.get("p2_layout") and content_manifest is None and p2_content is None:
        raise ValueError("P2 native launch requires --content-manifest or --p2-content "
                         "covering the seed identities; unstaged P2 seeds cannot launch")
    if purple_bank is not None and (assets is None or not (Path(assets) / 'dataDir/stages').is_dir()):
        raise ValueError('Purple campaign requires --assets with dataDir/stages')
    if (manifest.get("p2_purple_campaign") and purple_bank is None
            and not os.environ.get("PIKMIN_DEV_CONSOLE")):
        # A seed that binds Purple-only species (seed.P2_REQUIRES_PURPLE) is not
        # winnable without the Violet supply, so it never launches without it.
        raise ValueError("this seed was generated with --p2-purple-campaign; "
                         "run it with --purple-bank and --purple-motion")
    from .purple_campaign import bind_campaign_mode
    bind_campaign_mode(Path(session_dir), manifest, purple_bank, purple_motion)
    from .white_campaign import bind_campaign_mode as bind_white_campaign
    bind_white_campaign(Path(session_dir), manifest, white_bank)
    session = Session(manifest, session_dir)
    run = NativeRun(session, purple_campaign=purple_bank is not None)
    if family_install is not None:
        # Consume a family-owned installer into the run's private model destination.
        if not assets or not (Path(assets) / "dataDir" / "stages").is_dir():
            raise ValueError("--assets must point to the extracted assets directory containing dataDir/stages/")
        if family_source is None:
            raise ValueError("--family-install requires --family-source")
        from experimental.pikmin2_family_install import install_family
        receipt = install_family(family_install, Path(family_source), run.directory,
                                 list(family_actors or []), retail_assets=Path(assets))
        print(f"PIKMIN_FAMILY_INSTALLED: {family_install} {receipt}", flush=True)
    if content_manifest is not None:
        # Build the run's private native asset tree with the session content applied,
        # so native asset lookup reads the content. Staging runs before any native
        # process starts; a missing/wrong source or uncovered identity raises and
        # nothing launches, and the receipt records the seed's P2 identities.
        if not assets or not (Path(assets) / "dataDir" / "stages").is_dir():
            raise ValueError("--assets must point to the extracted assets directory containing dataDir/stages/")
        from experimental.pikmin2_staging import stage_session_content
        identities = [binding["source_id"]
                      for binding in session.manifest.get("p2_layout", {}).get("bindings", [])]
        receipt = stage_session_content(content_manifest, run.directory / "assets",
                                        required_identities=identities, retail_assets=Path(assets))
        print(f"PIKMIN_CONTENT_STAGED: {receipt['summary']} identities={receipt['identities']}", flush=True)
    if p2_content is not None:
        # Identity-to-runtime binding: stage each p2_layout binding's family content
        # keyed by source id / enum name, so a generated session launches without
        # per-family manual sidecar copying. Runs before any native process, so an
        # unknown identity, missing/wrong source or missing actor binding raises and
        # nothing launches.
        if not assets or not (Path(assets) / "dataDir" / "stages").is_dir():
            raise ValueError("--assets must point to the extracted assets directory containing dataDir/stages/")
        layout = manifest.get("p2_layout")
        if not layout:
            raise ValueError("--p2-content requires a seed with a p2_layout (generate with --p2-enemies)")
        from experimental.pikmin2_family_install import install_layout
        from experimental.pikmin2_staging import StagingError
        cache_dir = session.directory / "p2-content-cache"
        try:
            from .p2_actor_bindings import resolve_actor_bindings
            actors = resolve_actor_bindings(session.manifest, p2_actors)
            receipt = install_layout(run.directory, layout, Path(p2_content),
                                     actor_bindings=actors, retail_assets=Path(assets),
                                     cache_dir=cache_dir)
        except Exception:
            # Any install failure (wrong source / uncovered identity / bad binding /
            # adapter ValueError or RuntimeError) must leave no run tree behind:
            # NativeRun already seeded bootstrap.txt/state.txt and a partial tree
            # would be replayed as an incomplete stage on the next launch.
            shutil.rmtree(run.directory, ignore_errors=True)
            raise
        print(f"PIKMIN_P2_BOUND: {len(receipt['bindings'])} identities cached={bool(receipt.get('cached'))}", flush=True)
        from .p2_units import stage_units
        staged_units = stage_units(run.directory, layout)
        if staged_units:
            print(f"PIKMIN_P2_UNITS: {staged_units}", flush=True)
    if purple_bank is not None:
        from .purple_campaign import stage_campaign
        stage_campaign(run.directory, assets, purple_bank, purple_motion, manifest)
    if white_bank is not None:
        from .white_campaign import stage_campaign as stage_white_campaign
        stage_white_campaign(run.directory, assets, white_bank, manifest)
    process = None
    overlay = None
    log = None
    if exe:
        exe = Path(exe).resolve(strict=True)
        if not assets or not (Path(assets) / "dataDir" / "stages").is_dir():
            raise ValueError("--assets must point to the extracted assets directory containing dataDir/stages/")
        if 'spawn_layout' in manifest or 'campaign_layout' in manifest: verify_source_assets(assets)
        if content_manifest is None and family_install is None and p2_content is None and purple_bank is None:
            # Link only inside this new private runtime directory.
            if sys.platform == "win32":
                import _winapi
                _winapi.CreateJunction(str(Path(assets).resolve()), str((run.directory / "assets").resolve()))
            else:
                (run.directory / "assets").symlink_to(Path(assets).resolve(), target_is_directory=True)
        env = dict(os.environ)
        env.pop("BBFT_PORT", None)
        from .native_settings import bind_settings
        settings = bind_settings(env, run.directory.parent.parent, run.directory)
        print(f"Native settings ({settings['status']}): {settings['path']}", flush=True)
        if settings.get("warning"):
            print("PIKMIN_SETTINGS_WARNING: " + settings["warning"], flush=True)
        startup_show = 1  # SW_SHOWNORMAL
        if env.get("PIKMIN_RANDOMIZER_TEST_BACKGROUND") == "1":
            # Agent/test launch inherited from a driver: never hold for focus; watch only if the owner opted in.
            from .test_run import apply_test_run_env
            apply_test_run_env(env)
            startup_show = 4  # SW_SHOWNOACTIVATE: a watched window must not take focus
        log = (run.directory / "native.log").open("w", encoding="utf-8")
        launch_options = {}
        if sys.platform == "win32":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = startup_show  # Win32 SW_*; not exported by subprocess.
            launch_options["startupinfo"] = startup
        process = subprocess.Popen([str(exe), "--randomizer-seed", str(run.bootstrap.resolve())],
            cwd=run.directory, env=env, stdout=log, stderr=subprocess.STDOUT, **launch_options)
        overlay_manifest = run.directory / 'overlay-manifest.json'
        atomic_write(overlay_manifest, json.dumps(manifest))
        try:
            if sys.platform == "win32":
                overlay = subprocess.Popen([sys.executable, '-m', 'randomizer.overlay',
                    '--manifest', str(overlay_manifest.resolve()), '--session-dir', str(session_dir.resolve()),
                    '--pid', str(process.pid)], cwd=Path(__file__).resolve().parents[1],
                    stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as exc:
            print(f'Overlay unavailable: {exc}', flush=True)
    print(f"Native bootstrap: {run.bootstrap.resolve()}", flush=True)
    try:
        updates = connection_updates(sys.stdin) if os.getenv("PIKMIN_AP_CONTROL") == "1" and manifest["mode"] == "ap" else None
        asyncio.run(serve(session, run, process, server, os.getenv("PIKMIN_AP_PASSWORD"), updates))
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
        log_path = run.directory / 'native.log'
        raise RuntimeError(f"native process exited {process.returncode} ({describe_native_exit(log_path)}); see {log_path}")


class NetplayClientRun:
    """One ``--netplay-client`` run. This class never touches the network.

    It owns only its mirror run directory
    (``<mirror>/runs/<token>/`` with ``bootstrap.txt``, ``mirror.json``,
    ``mirror-events.txt``, ``hello.txt``, a debug ``state.txt`` and ``card/``).
    It never imports ``websockets``, never contacts Archipelago, and never
    writes the host's ``session.json``, ``checks.txt`` or ``campaign/``.
    There is no reference to ``websockets``, ``ap_connect`` or ``serve``
    anywhere on this code path by construction.

    The run token is the peer token the host chose in ``export_client_bundle``
    and stamped into the bootstrap ``SESSION`` line: when ``run_token`` is
    omitted it is derived from the bootstrap (validated as hex), so relaunching
    with the same host bootstrap resumes the same ``runs/<token>/`` directory,
    ``mirror.json`` and ingest cursor. Passing ``run_token`` explicitly still
    requires it to match the bootstrap ``SESSION`` line.
    """

    def __init__(self, manifest, mirror_dir, bootstrap_text, run_token=None, seed_data=None, native_directory=None):
        self.manifest = manifest
        self.fingerprint_value = mirror_fingerprint(manifest)
        self.mirror_dir = Path(mirror_dir)
        if type(bootstrap_text) is not str or not bootstrap_text:
            raise ValueError("netplay client requires the host bootstrap")
        fields = bootstrap_text.split()
        try:
            session_line = fields[fields.index("SESSION") + 1]
            fingerprint_line = fields[fields.index("FINGERPRINT") + 1]
        except (ValueError, IndexError):
            raise ValueError("client bootstrap is missing SESSION/FINGERPRINT")
        if run_token is None:
            token = session_line
        else:
            if session_line != run_token:
                raise ValueError("client bootstrap SESSION does not match this run token")
            token = run_token
        expected_directory = run_dir_for(self.mirror_dir, token)
        self.directory = (Path(native_directory).resolve(strict=True) if native_directory is not None
                          else expected_directory)
        if native_directory is not None and self.directory != expected_directory.resolve():
            raise ValueError("attached client directory differs from native SESSION layout")
        self.token = self.directory.name
        if fingerprint_line != self.fingerprint_value:
            raise ValueError("client bootstrap fingerprint does not match manifest")
        if is_thelynk(manifest):
            from .thelynk import render_bootstrap
            canonical_bootstrap = render_bootstrap(manifest, token)
        else:
            identity = SimpleNamespace(manifest=manifest, fingerprint=self.fingerprint_value,
                death_link_unit=manifest["death_link_pikmin"] if manifest.get("death_link") else 0)
            canonical_bootstrap = native_bootstrap(identity, token, bool(manifest.get("p2_purple_campaign")))
        if bootstrap_text != canonical_bootstrap:
            raise ValueError("client bootstrap differs from complete host manifest")
        self.directory.mkdir(parents=True, exist_ok=True)
        if native_directory is None:
            atomic_write(self.directory / BOOTSTRAP_FILENAME, bootstrap_text)
        elif (self.directory / BOOTSTRAP_FILENAME).read_text(encoding="ascii") != bootstrap_text:
            raise ValueError("attached client bootstrap changed; refusing overwrite")
        (self.directory / CARD_DIRNAME).mkdir(exist_ok=True)
        self.events = self.directory / EVENTS_FILENAME
        self.hello = self.directory / HELLO_FILENAME
        self.handshaken = False
        if seed_data is not None and not (self.directory / MIRROR_FILENAME).exists():
            from .netplay_mirror import validate_mirror_data
            validate_mirror_data(manifest, seed_data)
            atomic_write(self.directory / MIRROR_FILENAME,
                         json.dumps(seed_data, indent=2) + "\n")
        self.mirror = MirrorStore(manifest, self.directory / MIRROR_FILENAME)
        self.ingest_path = self.directory / INGEST_FILENAME
        self.offset = 0
        self.seen = set()
        self.checkpoint = None
        self.last_frame = -1
        self.prefix_hash = hashlib.sha256(b"").hexdigest()
        if self.ingest_path.exists():
            try:
                state = json.loads(self.ingest_path.read_text(encoding="utf-8"))
                offset, seen, checkpoint = state["offset"], state["seen"], state.get("checkpoint")
                last_frame = state.get("last_frame", -1)
                prefix_hash = state.get("prefix_hash", self.prefix_hash)
                if type(offset) is not int or offset < 0 or type(seen) is not list:
                    raise ValueError("bad ingest state")
                if type(last_frame) is not int or last_frame < -1:
                    raise ValueError("bad ingest state")
                if type(prefix_hash) is not str:
                    raise ValueError("bad ingest state")
            except (ValueError, KeyError, UnicodeDecodeError):
                raise ValueError("mirror ingest state is damaged")
            self.offset = offset
            self.seen = set(seen)
            self.checkpoint = checkpoint
            self.last_frame = last_frame
            self.prefix_hash = prefix_hash
        self._check_hello()
        self.write_state(True)

    def _save_ingest(self):
        atomic_write(self.ingest_path, json.dumps(
            dict(offset=self.offset, seen=sorted(self.seen), checkpoint=self.checkpoint,
                 last_frame=self.last_frame, prefix_hash=self.prefix_hash),
            indent=2) + "\n")

    def _check_hello(self):
        """Gate ingest on the native ``hello.txt`` handshake.

        The native client advertises ``PIKMIN_HELLO <schema> <token>
        <fingerprint> <capabilities...> END`` in the run directory, mirroring
        the host ``NativeRun`` handshake. Nothing is ingested until it matches;
        a present-but-wrong hello is fatal.
        """
        if self.handshaken:
            return True
        if not self.hello.exists():
            return False
        try:
            fields = self.hello.read_text(encoding="ascii").split()
        except (OSError, UnicodeDecodeError):
            raise ValueError("mirror hello is unreadable")
        expected = (["THELYNK_HELLO", "1", self.token, self.fingerprint_value,
                     "individual-parts-v1", "squad-checks-v1", "typed-pikmin-v1", "END"]
                    if is_thelynk(self.manifest) else
                    ["PIKMIN_HELLO", str(self.manifest["schema"]), self.token,
                     self.fingerprint_value, *self.manifest["capabilities"], "END"])
        if fields != expected:
            raise ValueError("mirror hello handshake mismatch")
        self.handshaken = True
        return True

    def write_state(self, ready=True):
        atomic_write(self.directory / STATE_FILENAME,
                     render_mirror_state(self.manifest, self.mirror.load(), self.token, ready))

    def poll(self):
        """Ingest newly appended events; return ``(applied, duplicates)``.

        Lines are split on ``b"\\n"`` only; any ``\\r`` or control byte stays
        inside the line and is rejected by the strict parser. The whole batch
        is parsed and validated before anything is applied, so a malformed
        line leaves ``mirror.json``, the card pointer and the ingest cursor
        untouched. A malformed stream is fatal to the run (matching host
        semantics): the offending poll raises.
        """
        if not self._check_hello():
            return (0, 0)
        raw = self.events.read_bytes() if self.events.exists() else b""
        complete = raw[:raw.rfind(b"\n") + 1] if raw else b""
        if len(complete) < self.offset:
            raise ValueError("mirror event file was truncated")
        if self.offset and hashlib.sha256(bytes(complete[:self.offset])).hexdigest() != self.prefix_hash:
            raise ValueError("mirror event file was rewritten")
        try:
            text = complete.decode("ascii")
        except UnicodeDecodeError:
            raise ValueError("mirror event file is not ASCII")
        chunk = text[self.offset:]
        if not chunk:
            return (0, 0)
        raw_lines = chunk.split("\n")
        if raw_lines[-1] != "":
            raise ValueError("mirror event batch is not newline terminated")
        lines = raw_lines[:-1]
        if any(line == "" for line in lines):
            raise ValueError("invalid mirror event: blank line")
        # Phase 1: parse every line and check frame monotonicity, skipping
        # exact duplicates (which are no-ops by construction).
        parsed = []
        running = self.last_frame
        for line in lines:
            if line in self.seen:
                parsed.append(None)
                continue
            frame, tag, args = parse_mirror_line(line)
            if frame < running:
                raise ValueError("mirror frame retracted")
            running = max(running, frame)
            parsed.append((frame, tag, args))
        # Phase 1b: validate the whole batch against a copy before mutating.
        data_copy = copy.deepcopy(self.mirror.load())
        checkpoint_copy = copy.deepcopy(self.checkpoint)
        for line, event in zip(lines, parsed):
            if event is None:
                continue
            frame, tag, args = event
            if tag in ("SAVE_RESULT", "SAVE_FAIL"):
                checkpoint_copy = (dict(gen=args[0], digest=args[1], ok=True, frame=frame)
                                   if tag == "SAVE_RESULT"
                                   else dict(gen=args[0], digest=None, ok=False, frame=frame))
                continue
            self.mirror.apply(data_copy, event)
        # Phase 2: apply for real; card writes happen only after validation.
        data = self.mirror.load()
        applied = duplicates = 0
        card_text = None
        for line, event in zip(lines, parsed):
            if event is None:
                duplicates += 1
                continue
            frame, tag, args = event
            if tag in ("SAVE_RESULT", "SAVE_FAIL"):
                if tag == "SAVE_RESULT":
                    gen, digest = args
                    self.checkpoint = dict(gen=gen, digest=digest, ok=True, frame=frame)
                    card_text = f"SAVE_RESULT {gen} {digest}\n"
                else:
                    (gen,) = args
                    self.checkpoint = dict(gen=gen, digest=None, ok=False, frame=frame)
                    card_text = f"SAVE_FAIL {gen}\n"
                self.seen.add(line)
                applied += 1
                continue
            if self.mirror.apply(data, event):
                applied += 1
            else:
                duplicates += 1
            self.seen.add(line)
        self.offset = len(complete)
        self.last_frame = running
        self.prefix_hash = hashlib.sha256(bytes(complete)).hexdigest()
        if lines:
            if card_text is not None:
                atomic_write(self.directory / CARD_DIRNAME / SAVE_RESULT_FILENAME, card_text)
            self.mirror.save(data)
            self._save_ingest()
            self.write_state(True)
        return (applied, duplicates)


async def serve_netplay_client(manifest, run, process=None):
    """Local-file serve loop for client mode. No sockets, no AP reconnect."""
    try:
        while process is None or process.poll() is None:
            run.poll()
            await asyncio.sleep(0.1)
    finally:
        try:
            run.poll()
        finally:
            run.write_state(True)


def launch_netplay_client(manifest, session_dir, bootstrap_text, mirror_dir=None, exe=None, assets=None):
    """Run the mirror client. Only writes under the mirror directory."""
    if bootstrap_text is None:
        raise ValueError("netplay client requires the host bootstrap")
    target = Path(mirror_dir) if mirror_dir else mirror_dir_for(session_dir, mirror_fingerprint(manifest))
    with SessionLock(target):
        return _launch_netplay_client(manifest, target, bootstrap_text, exe, assets)


def _launch_netplay_client(manifest, mirror_dir, bootstrap_text, exe=None, assets=None):
    run = NetplayClientRun(manifest, mirror_dir, bootstrap_text)
    process = None
    overlay = None
    log = None
    if exe:
        exe = Path(exe).resolve(strict=True)
        if not assets or not (Path(assets) / "dataDir" / "stages").is_dir():
            raise ValueError("--assets must point to the extracted assets directory containing dataDir/stages/")
        target = run.directory / "assets"
        import _winapi
        _winapi.CreateJunction(str(Path(assets).resolve()), str(target.resolve()))
        env = dict(os.environ)
        env.pop("BBFT_PORT", None)
        from .native_settings import bind_settings
        settings = bind_settings(env, run.directory.parent.parent, run.directory)
        print(f"Native settings ({settings['status']}): {settings['path']}", flush=True)
        if settings.get("warning"):
            print("PIKMIN_SETTINGS_WARNING: " + settings["warning"], flush=True)
        log = (run.directory / "native.log").open("w", encoding="utf-8")
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 1  # Win32 SW_SHOWNORMAL; not exported by subprocess.
        process = subprocess.Popen([str(exe), "--randomizer-seed", str((run.directory / BOOTSTRAP_FILENAME).resolve())],
            cwd=run.directory, env=env, stdout=log, stderr=subprocess.STDOUT, startupinfo=startup)
        overlay_manifest = run.directory / "overlay-manifest.json"
        atomic_write(overlay_manifest, json.dumps(manifest))
        try:
            overlay = subprocess.Popen([sys.executable, "-m", "randomizer.overlay",
                "--manifest", str(overlay_manifest.resolve()), "--session-dir", str(run.directory.resolve()),
                "--pid", str(process.pid)], cwd=Path(__file__).resolve().parents[1],
                stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as exc:
            print(f"Overlay unavailable: {exc}", flush=True)
    print(f"Netplay client mirror: {run.directory.resolve()}", flush=True)
    try:
        asyncio.run(serve_netplay_client(manifest, run, process))
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


def attach_native_host(manifest, session_dir, native_directory, server=None):
    """Serve an existing native ICE run; never launch/stop its process or rewrite bootstrap."""
    session_dir = Path(session_dir).resolve(strict=True)
    with SessionLock(session_dir):
        session = Session(manifest, session_dir)
        run = NativeRun.attach(session, native_directory)
        try:
            asyncio.run(serve(session, run, server=server))
        finally:
            run.write_state(False)


def attach_native_client(manifest, native_directory):
    """Attach file IPC to the exact native-created peer token and private run."""
    directory = Path(native_directory).resolve(strict=True)
    text = (directory / BOOTSTRAP_FILENAME).read_text(encoding="ascii")
    with SessionLock(directory.parent.parent):
        run = NetplayClientRun(manifest, directory.parent.parent, text, native_directory=directory)
        asyncio.run(serve_netplay_client(manifest, run))
