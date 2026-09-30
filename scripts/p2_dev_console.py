"""Launch a Forest of Hope dev-console session with the whole playable P2 pool staged (#942).

One-time content preparation (reused on every later launch):

    py -3.12 scripts/p2_dev_console.py --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --prepare-only

Launch (PowerShell):

    py -3.12 scripts/p2_dev_console.py --exe <nectar.exe> --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets

In game press the backquote key (`) and type ``spawn 41`` (or ``help``); or feed the
script file from another PowerShell window:

    Add-Content <session>/dev-console.txt 'spawn 78'

The session is a plain Forest of Hope solo seed whose ``p2_layout`` binds every
staged species to its dev target uid (randomizer/dev_console.py), so nothing
spawns by itself; ``spawn <id|name>`` creates the actor next to the captain
through the family's own bind path. Native log lines start with ``DEV_CONSOLE``.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randomizer import dev_console  # noqa: E402
from randomizer.seed import PLAYABLE_P2_SPECIES  # noqa: E402

DEFAULT_CONTENT = ROOT / "output" / "p2-dev-content"
DEFAULT_SESSION = ROOT / "output" / "p2-dev-session"
DEFAULT_ASSETS = Path("C:/Users/alari/bbft/dist/cohesion/pikmin/assets")


def parse_species(text):
    if text is None or text == "playable":
        return list(PLAYABLE_P2_SPECIES)
    ids = [int(x) for x in text.split(",") if x.strip()]
    unknown = sorted(set(ids) - set(PLAYABLE_P2_SPECIES))
    if unknown:
        raise SystemExit(f"not in the playable pool: {unknown}")
    return ids


def prepare_command(iso, content, species):
    return [sys.executable, str(ROOT / "scripts" / "p2_prepare_content.py"), "--iso", str(iso),
            "--out", str(content), "--species", ",".join(str(i) for i in species)]


def ensure_content(iso, content: Path, species, *, run=subprocess.run):
    """Prepare the content root once; later calls reuse it (no re-extraction)."""
    content = Path(content)
    if (content / "prepared.json").is_file():
        staged = dev_console.staged_species(content, species)
        missing = sorted(set(species) - set(staged))
        print(f"P2_DEV_CONTENT reuse={content} staged={len(staged)} missing={missing}", flush=True)
        return staged
    if iso is None:
        raise SystemExit(f"{content} is not prepared; pass --iso to extract it once")
    content.mkdir(parents=True, exist_ok=True)
    print(f"P2_DEV_CONTENT preparing {content} from {iso} ({len(species)} species)", flush=True)
    run(prepare_command(iso, content, species), check=True)
    staged = dev_console.staged_species(content, species)
    print(f"P2_DEV_CONTENT prepared staged={len(staged)}", flush=True)
    return staged


def write_manifest(session: Path, species, seed_name):
    manifest = dev_console.build_dev_manifest(species, seed_name)
    session.mkdir(parents=True, exist_ok=True)
    path = session / "dev-seed.json"
    path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest, path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iso", type=Path, default=None, help="P2 ISO; only needed the first time (content extraction)")
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT, help="identity-keyed content root (reused)")
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION)
    parser.add_argument("--exe", type=Path, default=None, help="native nectar.exe built with the dev console")
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--species", default=None, help="'playable' (default) or comma-separated source ids")
    parser.add_argument("--seed-name", default="dev-console")
    parser.add_argument("--script", type=Path, default=None,
                        help="command file polled by the game (default <session>/dev-console.txt)")
    parser.add_argument("--prepare-only", action="store_true", help="extract content and write the manifest, no launch")
    args = parser.parse_args(argv)

    species = parse_species(args.species)
    staged = ensure_content(args.iso, args.content, species)
    if not staged:
        raise SystemExit("no staged species; nothing to launch")
    session = args.session_dir.resolve()
    manifest, manifest_path = write_manifest(session, staged, args.seed_name)
    actors = dev_console.actor_bindings(manifest["p2_layout"])
    (session / "dev-actors.json").write_text(json.dumps(actors, indent=1), encoding="utf-8")
    script = (args.script or session / dev_console.DEFAULT_SCRIPT_NAME).resolve()
    script.parent.mkdir(parents=True, exist_ok=True)
    if not script.exists():
        script.write_text("", encoding="utf-8")
    print(f"P2_DEV_SEED {manifest_path} species={staged}", flush=True)
    print(f"P2_DEV_SCRIPT {script}  (PowerShell: Add-Content '{script}' 'spawn 41')", flush=True)
    if args.prepare_only:
        return 0
    if args.exe is None:
        raise SystemExit("--exe is required to launch (or pass --prepare-only)")
    os.environ.update(dev_console.native_environment(script))
    os.environ["PIKMIN_RANDOMIZER_TEST_BACKGROUND"] = "1"  # agent-driven: never stall on focus (watch via output/workflow/WATCH_RUNS)
    from randomizer.runner import launch
    launch(manifest, session, args.exe.resolve(), args.assets.resolve(), None,
           p2_content=args.content.resolve(), p2_actors=actors)
    return 0


if __name__ == "__main__":
    sys.exit(main())
