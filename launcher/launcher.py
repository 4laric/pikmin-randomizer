"""Player launcher: resolves assets/session/server, prints a seed card, runs `python -m randomizer run`.

Usage: launcher.py [seed.json] [--server host:port] [--assets dir] [--reset-assets] [--pause-on-exit]

Only the standard library and the `randomizer` package located in the package root are used.
Nothing is written inside the package root; config and sessions live under %APPDATA%\\PikminRandomizer.
"""
import argparse
import getpass
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_NAME = "PikminRandomizer"
SESSION_ID_LENGTH = 16
ASSET_RETRIES = 3


class LaunchError(Exception):
    """Actionable failure shown to the player; message is complete on its own."""


# --- Paths and config -------------------------------------------------------

def app_dir():
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME


def config_path():
    return app_dir() / "config.json"


def load_config():
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(config):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def runtime_version(root=ROOT):
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


# --- Seed manifest ----------------------------------------------------------

def load_manifest(path):
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise LaunchError(f"Cannot read seed file {path}: {exc}")
    except ValueError as exc:
        raise LaunchError(f"{path} is not valid JSON: {exc}")
    from randomizer.seed import validate
    try:
        validate(manifest)
    except (ValueError, KeyError, TypeError) as exc:
        raise LaunchError(f"{path} is not a valid Pikipelago seed: {exc}")
    return manifest


def short_fingerprint(manifest):
    from randomizer.seed import fingerprint
    return fingerprint(manifest)[:SESSION_ID_LENGTH]


def session_dir(manifest, seed_path):
    """Legacy layout keeps `session` next to the seed; otherwise one directory per seed fingerprint."""
    legacy = Path(seed_path).resolve().parent / "session"
    if legacy.is_dir():
        return legacy
    return app_dir() / "sessions" / short_fingerprint(manifest)


def choose_seed(seed_arg, root=ROOT, ask=input):
    if seed_arg:
        path = Path(seed_arg)
        if not path.is_file():
            raise LaunchError(f"Seed file not found: {path}")
        return path
    seeds = root / "seeds"
    default = seeds / "seed.json"
    if default.is_file():
        return default
    candidates = sorted(seeds.glob("*.json")) if seeds.is_dir() else []
    if not candidates:
        raise LaunchError(f"No seed given and no *.json files in {seeds}.\n"
                          "Drag a seed.json onto Play.cmd, or copy it into the seeds folder.")
    print("Available seeds:")
    for index, candidate in enumerate(candidates, 1):
        print(f"  {index}. {candidate.name}")
    while True:
        answer = ask(f"Choose a seed [1-{len(candidates)}]: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer) - 1]
        print("Please enter a number from the list.")


def seed_card(manifest, seed_path, root=ROOT):
    lines = ["=" * 60, "Pikipelago",
             f"  Runtime version: {runtime_version(root)}",
             f"  Seed file:       {Path(seed_path).name}",
             f"  Slot:            {manifest.get('slot', '?')}",
             f"  Mode:            {manifest.get('mode', '?')}",
             f"  Seed name:       {manifest.get('seed', '?')}",
             f"  Fingerprint:     {short_fingerprint(manifest)}"]
    if "profile" in manifest:
        lines.append(f"  Starting area:   {manifest['profile']}")
    if "starting_color" in manifest:
        lines.append(f"  Starting color:  {manifest['starting_color']}")
    if "goal_mode" in manifest:
        lines.append(f"  Goal:            {manifest['goal_mode']}")
    lines.append("=" * 60)
    return "\n".join(lines)


# --- Assets -----------------------------------------------------------------

def assets_problem(directory):
    """None when the directory holds extracted assets, else a sentence describing what is missing."""
    if not directory:
        return "No directory given."
    path = Path(directory)
    if not path.is_dir():
        return f"{path} is not a directory."
    if not (path / "dataDir").is_dir():
        return f"{path} has no dataDir folder; point at the folder that directly contains dataDir."
    if not (path / "dataDir" / "stages").is_dir():
        return f"{path}\\dataDir has no stages folder; the extraction looks incomplete."
    return None


def pick_folder_dialog():
    """Return a path from a tkinter folder dialog, or None when no GUI is available."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return None
    try:
        window = tkinter.Tk()
    except tkinter.TclError:
        return None
    window.withdraw()
    window.attributes("-topmost", True)
    try:
        chosen = filedialog.askdirectory(title="Select the extracted Pikmin assets folder (contains dataDir)")
    finally:
        window.destroy()
    return chosen or None


def ask_assets(ask=input, dialog=pick_folder_dialog):
    print("First run: select the folder with your extracted game assets (it must contain dataDir\\stages).")
    for attempt in range(ASSET_RETRIES):
        chosen = dialog()
        if chosen is None:
            chosen = ask("Extracted assets folder: ").strip().strip('"')
        problem = assets_problem(chosen)
        if problem is None:
            return str(Path(chosen).resolve())
        print(f"Not usable: {problem}")
    raise LaunchError("Could not find a valid assets folder after three attempts.\n"
                      "Extract the game assets first, then run Play.cmd again (or use --assets <dir>).")


def resolve_assets(config, override=None, reset=False, ask=input, dialog=pick_folder_dialog):
    if override:
        problem = assets_problem(override)
        if problem:
            raise LaunchError(f"--assets is not usable: {problem}")
        config["assets"] = str(Path(override).resolve())
        save_config(config)  # Remembered so the next plain launch needs no argument.
        return config["assets"]
    saved = None if reset else config.get("assets")
    if saved and assets_problem(saved) is None:
        return saved
    if saved:
        print(f"Saved assets folder is no longer valid: {assets_problem(saved)}")
    assets = ask_assets(ask, dialog)
    config["assets"] = assets
    save_config(config)
    return assets


# --- Archipelago ------------------------------------------------------------

def resolve_server(config, override=None, ask=input):
    if override:
        return override
    last = config.get("server")
    prompt = f"Archipelago server host:port [{last}]: " if last else "Archipelago server host:port: "
    while True:
        answer = ask(prompt).strip() or (last or "")
        if answer:
            break
        print("A server address is required for an AP seed.")
    if answer != last:
        config["server"] = answer
        save_config(config)
    return answer


def ask_password(ask=input, secret=getpass.getpass):
    answer = ask("Does the room have a password? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        return None
    return secret("Room password (not stored): ")


def check_ap_dependencies():
    try:
        import websockets  # noqa: F401
    except ImportError:
        raise LaunchError("AP mode needs the 'websockets' package, which is missing from this Python.\n"
                          f"Install it with:  \"{sys.executable}\" -m pip install \"websockets>=13,<14\"")


# --- Launch -----------------------------------------------------------------

def build_command(seed_path, session, exe, assets, server=None, python=None, root=ROOT):
    command = [python or sys.executable, "-m", "randomizer", "run", str(Path(seed_path).resolve()),
               "--session-dir", str(session), "--exe", str(exe), "--assets", str(assets)]
    if server:
        command += ["--server", server]
    return command


def newest_native_log(session):
    logs = sorted((Path(session) / "runs").glob("*/native.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def explain_failure(returncode, output, session):
    """Map runner output and exit status to a player-facing message."""
    text = output or ""
    if "another runner owns this session directory" in text:
        return ("Another launcher is already running this seed. Close the other game window first, "
                f"or wait for it to exit.\nSession: {session}")
    if "--assets must point" in text or "dataDir/stages" in text:
        return ("The assets folder is missing dataDir\\stages. Run Play.cmd with --reset-assets to choose it again.")
    if "AP connection refused" in text:
        return "The Archipelago server refused the connection: check the slot name, password and server address.\n" + text.strip().splitlines()[-1]
    if "AP slot manifest does not match" in text:
        return "This seed.json is not the one the Archipelago room was generated with. Use the seed from the room's output."
    if "No module named 'websockets'" in text or "ModuleNotFoundError: No module named 'websockets'" in text:
        return "AP mode needs the 'websockets' package. Install it with pip (see docs) and try again."
    if "native process exited" in text:
        log = newest_native_log(session)
        where = f"\nSee the game log: {log}" if log else ""
        return "The game exited with an error." + where
    if "FileNotFoundError" in text and "nectar.exe" in text:
        return "bin\\nectar.exe is missing from the package. Re-extract the release zip."
    log = newest_native_log(session)
    where = f"\nNewest game log: {log}" if log else ""
    return f"The runner exited with code {returncode}.{where}\n{text.strip()[-2000:]}"


def run(command, env, root=ROOT):
    """Run the runner, echoing its output while keeping a copy for diagnostics."""
    process = subprocess.Popen(command, cwd=str(root), env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    captured = []
    for line in process.stdout:
        print(line, end="", flush=True)
        captured.append(line)
    return process.wait(), "".join(captured)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pikipelago launcher")
    parser.add_argument("seed", nargs="?", help="seed.json (default: seeds\\seed.json in the package)")
    parser.add_argument("--server", help="Archipelago host:port (AP seeds)")
    parser.add_argument("--assets", help="extracted assets folder containing dataDir\\stages")
    parser.add_argument("--reset-assets", action="store_true", help="forget the saved assets folder and ask again")
    parser.add_argument("--pause-on-exit", action="store_true", help="wait for Enter before closing on failure")
    args = parser.parse_args(argv)
    try:
        code = launch(args)
    except LaunchError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        code = 2
    except KeyboardInterrupt:
        code = 130
    if code and args.pause_on_exit:
        try:
            input("Press Enter to close...")
        except EOFError:
            pass
    return code


def launch(args):
    exe = ROOT / "bin" / "nectar.exe"
    if not exe.is_file():
        raise LaunchError(f"The game executable is missing: {exe}\nRe-extract the release zip; do not move Play.cmd out of it.")
    seed_path = choose_seed(args.seed)
    manifest = load_manifest(seed_path)
    config = load_config()
    print(seed_card(manifest, seed_path))
    assets = resolve_assets(config, args.assets, args.reset_assets)
    session = session_dir(manifest, seed_path)
    print(f"Assets:  {assets}\nSession: {session}")
    env = dict(os.environ)
    env.pop("PIKMIN_AP_PASSWORD", None)
    env["PYTHONUNBUFFERED"] = "1"
    server = None
    if manifest["mode"] == "ap":
        check_ap_dependencies()
        server = resolve_server(config, args.server)
        password = ask_password()
        if password:
            env["PIKMIN_AP_PASSWORD"] = password
    command = build_command(seed_path, session, exe, assets, server)
    print("Launching...", flush=True)
    try:
        returncode, output = run(command, env)
    except OSError as exc:
        raise LaunchError(f"Could not start Python runner: {exc}")
    if returncode:
        raise LaunchError(explain_failure(returncode, output, session))
    print("Runner exited normally.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
