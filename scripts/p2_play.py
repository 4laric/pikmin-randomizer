"""One-command P2 seed play script for solo and Archipelago seeds (#93).

Reduces the manual "generate -> prepare content + actors -> run" flow to one
command. It:

1. generates the seed manifest (solo ``--seed``) or runs an Archipelago
   generation for ``--apworld-yaml`` through the local Archipelago install
   (``scripts/build_apworld.py`` builds the .apworld),
2. prepares the identity-keyed P2 content root from the retail ISO, cached per
   ISO sha256 (reusing ``scripts/p2_prepare_content.py`` functions, never
   copying them),
3. writes the seed's ``{target: generator_id}`` actor bindings,
4. picks a short session directory (default ``C:/p2play/<seed>-<n>``) and
   refuses any run path over 200 chars (Windows' 260-char limit makes deep
   ``.mod`` loads fail),
5. puts ``C:/msys64/mingw64/bin`` on the child PATH and runs ``randomizer run``.

``--dry-run`` prints every step and path without generating, extracting or
launching anything. Generated content stays under ``output/`` (untracked) or the
chosen ``--cache-dir``; nothing extracted from the ISO is ever committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import p2_prepare_content as prepare  # noqa: E402

DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
DEFAULT_ASSETS = Path("C:/Users/alari/bbft/dist/cohesion/pikmin/assets")
DEFAULT_AP_ROOT = Path("C:/Users/alari/Archipelago")
DEFAULT_SESSION_ROOT = Path("C:/p2play")
MINGW_BIN = Path("C:/msys64/mingw64/bin")
MAX_RUN_PATH = 200
BINDING_RECEIPT = "p2-binding-receipt.json"
APWORLD_NAME = "pikmin_randomizer.apworld"
ISO_PREFIX = "p2-content"
SEED_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


class PlayPathError(ValueError):
    """A generated run path would exceed the Windows-safe length budget."""


@dataclass
class Step:
    name: str
    detail: str
    command: list | None = None


@dataclass
class PlayPlan:
    mode: str
    iso: Path
    assets: Path
    exe: Path | None
    server: str | None
    pool: str
    cache_root: Path
    work_dir: Path
    manifest: Path
    content_dir: Path
    content_cached: bool
    actors: Path
    session_dir: Path
    run_command: list
    steps: list = field(default_factory=list)


def ensure_run_path(path, limit=MAX_RUN_PATH):
    """Refuse a run path whose string form exceeds ``limit`` characters."""
    text = str(Path(path))
    if len(text) > limit:
        raise PlayPathError(
            f"run path is {len(text)} chars, over the {limit}-char limit: {text}")
    return Path(path)


def iso_sha256(iso):
    """Stream a retail ISO to its sha256 (the content-cache key)."""
    digest = hashlib.sha256()
    with open(iso, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_cache_dir(cache_root, iso):
    """Cache root for this ISO: one content tree per retail ISO hash."""
    return Path(cache_root) / ISO_PREFIX / iso_sha256(iso)[:16]


def content_is_cached(content_dir):
    """A content root is reusable once ``prepare_content_root`` wrote its summary."""
    return (Path(content_dir) / "prepared.json").is_file()


def sanitize_name(name):
    safe = SEED_SAFE_RE.sub("_", str(name)).strip("._-")
    return safe or "seed"


def next_session_dir(base, seed, limit=MAX_RUN_PATH):
    """Smallest free ``<base>/<seed>-<n>`` whose run tree fits the length budget."""
    safe = sanitize_name(seed)
    n = 1
    while True:
        candidate = Path(base) / f"{safe}-{n}"
        deepest = candidate / "runs" / ("0" * 64) / BINDING_RECEIPT
        ensure_run_path(deepest, limit=limit)
        if not candidate.exists():
            return candidate
        n += 1


def session_deepest_path(session_dir):
    return Path(session_dir) / "runs" / ("0" * 64) / BINDING_RECEIPT


def solo_generate_command(seed, output, pool, python=None):
    command = [python or sys.executable, "-m", "randomizer", "generate",
               "--seed", seed, "--p2-enemies", "--output", str(output)]
    if pool == "playable":
        command += ["--p2-species", "playable"]
    return command


def apworld_command(output, python=None):
    return [python or sys.executable, str(ROOT / "scripts" / "build_apworld.py"),
            "--output", str(output)]


def apworld_install_path(ap_root):
    return Path(ap_root) / "custom_worlds" / APWORLD_NAME


def ap_generate_command(ap_root, players_dir, output_dir, python=None):
    return [python or sys.executable, str(Path(ap_root) / "Generate.py"),
            "--player_files_path", str(players_dir),
            "--outputpath", str(output_dir)]


def wanted_source_ids(pool):
    """Source ids to extract for a pool: the launcher pool or every admitted id."""
    if pool == "playable":
        return list(prepare.PLAYABLE_SOURCE_IDS)
    return prepare.admitted_source_ids()


def run_command(manifest, session_dir, assets, exe=None, p2_content=None,
                p2_actors=None, server=None, python=None):
    command = [python or sys.executable, "-m", "randomizer", "run", str(manifest),
               "--session-dir", str(session_dir), "--assets", str(assets)]
    if p2_content is not None:
        command += ["--p2-content", str(p2_content)]
    if p2_actors is not None:
        command += ["--p2-actors", str(p2_actors)]
    if exe is not None:
        command += ["--exe", str(exe)]
    if server:
        command += ["--server", server]
    return command


def resolve_work_dir(cache_root, name, work_dir=None):
    if work_dir is not None:
        return Path(work_dir)
    return Path(cache_root) / "work" / sanitize_name(name)


def build_plan(args):
    """Resolve every path and command for a run, with no filesystem mutation."""
    if bool(args.seed) == bool(args.apworld_yaml):
        raise ValueError("give exactly one of --seed (solo) or --apworld-yaml (AP)")
    if args.apworld_yaml and not args.server:
        raise ValueError("AP generation requires --server host:port")

    iso = Path(args.iso)
    cache_root = Path(args.cache_dir)
    name = args.seed or Path(args.apworld_yaml).stem
    work_dir = resolve_work_dir(cache_root, name, args.work_dir)
    content_dir = content_cache_dir(cache_root, iso)
    cached = content_is_cached(content_dir)
    actors = work_dir / "p2-actors.json"
    steps = []

    mode = "ap" if args.apworld_yaml else "solo"
    if mode == "solo":
        manifest = work_dir / "seed-manifest.json"
        generate = solo_generate_command(args.seed, manifest, args.pool)
        steps.append(Step("generate", f"solo seed manifest -> {manifest}", generate))
    else:
        manifest = work_dir / "ap-output" / "*.pikmin.json"
        archive = work_dir / APWORLD_NAME
        install = apworld_install_path(args.ap_root)
        players = work_dir / "players"
        ap_output = work_dir / "ap-output"
        steps.append(Step("generate",
                          f"build .apworld -> {archive}",
                          apworld_command(archive)))
        steps.append(Step("generate",
                          f"install .apworld -> {install}",
                          None))
        steps.append(Step("generate",
                          f"copy {args.apworld_yaml} -> {players}",
                          None))
        steps.append(Step("generate",
                          f"Archipelago Generate.py (server {args.server}) -> {ap_output}",
                          ap_generate_command(args.ap_root, players, ap_output)))

    steps.append(Step("content (cached)" if cached else "content (extract)",
                      str(content_dir)))
    steps.append(Step("actors", str(actors)))

    if args.session_dir is not None:
        session_dir = Path(args.session_dir)
        ensure_run_path(session_deepest_path(session_dir))
    else:
        session_dir = next_session_dir(DEFAULT_SESSION_ROOT, name)

    steps.append(Step("session dir", str(session_dir)))

    command = run_command(manifest, session_dir, args.assets, exe=args.exe,
                          p2_content=content_dir, p2_actors=actors,
                          server=args.server)
    steps.append(Step("run command", f"final {mode} randomizer run",
                      command))

    return PlayPlan(mode=mode, iso=iso, assets=Path(args.assets),
                    exe=args.exe, server=args.server, pool=args.pool,
                    cache_root=cache_root, work_dir=work_dir, manifest=manifest,
                    content_dir=content_dir, content_cached=cached, actors=actors,
                    session_dir=session_dir, run_command=command, steps=steps)


def print_plan(plan):
    for step in plan.steps:
        print(f"{step.name}: {step.detail}")
        if step.command is not None:
            print(f"  command: {' '.join(str(part) for part in step.command)}")


def ensure_content(iso, content_dir, pool, pose_limit, research):
    """Extract the content root once per ISO hash; return whether it was rebuilt."""
    if content_is_cached(content_dir):
        return False
    content_dir = Path(content_dir)
    content_dir.parent.mkdir(parents=True, exist_ok=True)
    partial = content_dir.parent / (content_dir.name + ".partial")
    if partial.exists():
        shutil.rmtree(partial)
    try:
        prepare.prepare_content_root(iso, partial, research=research,
                                     pose_limit=pose_limit,
                                     wanted=wanted_source_ids(pool))
        if content_dir.exists():
            shutil.rmtree(content_dir)
        partial.rename(content_dir)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return True


def child_env():
    env = dict(os.environ)
    env["PATH"] = str(MINGW_BIN) + os.pathsep + env.get("PATH", "")
    return env


def run_checked(command, cwd=None):
    print(f"+ {' '.join(str(part) for part in command)}", flush=True)
    subprocess.run([str(part) for part in command], cwd=cwd, env=child_env(),
                   check=True)


def stage_ap_generation(plan, yaml_path):
    """Build/install the .apworld, generate the room and return the manifest path."""
    archive = plan.work_dir / APWORLD_NAME
    run_checked(apworld_command(archive), cwd=ROOT)
    install = apworld_install_path(DEFAULT_AP_ROOT)
    install.parent.mkdir(parents=True, exist_ok=True)
    if not install.exists() or install.read_bytes() != archive.read_bytes():
        shutil.copyfile(archive, install)
    players = plan.work_dir / "players"
    players.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(yaml_path, players / Path(yaml_path).name)
    ap_output = plan.work_dir / "ap-output"
    ap_output.mkdir(parents=True, exist_ok=True)
    run_checked(ap_generate_command(DEFAULT_AP_ROOT, players, ap_output),
                cwd=DEFAULT_AP_ROOT)
    found = sorted(ap_output.glob("*.pikmin.json"))
    if len(found) != 1:
        raise ValueError(f"expected one *.pikmin.json in {ap_output}, found {len(found)}")
    return found[0]


def wait_for_receipt(session_dir, timeout):
    pattern = Path(session_dir) / "runs" / "*" / BINDING_RECEIPT
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matches = sorted(Path(session_dir).glob(f"runs/*/{BINDING_RECEIPT}"))
        if matches:
            return matches[0]
        time.sleep(0.5)
    return None


def execute(plan, args):
    plan.work_dir.mkdir(parents=True, exist_ok=True)
    if plan.mode == "solo":
        run_checked(plan.steps[0].command, cwd=ROOT)
        manifest = plan.work_dir / "seed-manifest.json"
    else:
        manifest = stage_ap_generation(plan, Path(args.apworld_yaml))
    if not Path(manifest).is_file():
        raise ValueError(f"seed manifest was not written: {manifest}")

    ensure_content(plan.iso, plan.content_dir, plan.pool, args.pose_limit,
                   args.research)
    prepare.actors_for_manifest_file(manifest, plan.actors)
    plan.session_dir.parent.mkdir(parents=True, exist_ok=True)

    command = run_command(manifest, plan.session_dir, plan.assets, exe=plan.exe,
                          p2_content=plan.content_dir, p2_actors=plan.actors,
                          server=plan.server)
    print(f"+ {' '.join(str(part) for part in command)}", flush=True)
    process = subprocess.Popen([str(part) for part in command], cwd=ROOT,
                               env=child_env())
    if plan.exe is not None:
        return process.wait()
    try:
        receipt = wait_for_receipt(plan.session_dir, args.stage_timeout)
        if receipt is None:
            raise RuntimeError(
                f"no {BINDING_RECEIPT} under {plan.session_dir} within "
                f"{args.stage_timeout}s")
        print(f"PIKMIN_P2_STAGED: {receipt}", flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iso", type=Path, default=DEFAULT_ISO,
                        help="P2 retail ISO (default: the known user ISO)")
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS,
                        help="extracted P1 assets root containing dataDir/stages/")
    parser.add_argument("--exe", type=Path, default=None,
                        help="native executable to launch; omit to stage only")
    parser.add_argument("--seed", default=None, help="solo seed text")
    parser.add_argument("--apworld-yaml", type=Path, default=None,
                        help="Archipelago player YAML (AP mode)")
    parser.add_argument("--server", default=None,
                        help="AP server host:port (AP mode)")
    parser.add_argument("--pool", choices=("playable", "all"), default="playable",
                        help="P2 species pool to prepare (default: playable)")
    parser.add_argument("--session-dir", type=Path, default=None,
                        help="explicit session dir (default C:/p2play/<seed>-<n>)")
    parser.add_argument("--work-dir", type=Path, default=None,
                        help="where the manifest/actors/ap output are written")
    parser.add_argument("--cache-dir", type=Path,
                        default=ROOT / "output" / "p2-play-cache",
                        help="content-cache namespace, keyed per ISO hash")
    parser.add_argument("--ap-root", type=Path, default=DEFAULT_AP_ROOT,
                        help="local Archipelago install (AP mode)")
    parser.add_argument("--research", type=Path, default=None,
                        help="native/pikmin2-research checkout (default: %(default)s)")
    parser.add_argument("--pose-limit", type=int, default=3,
                        help="sampled poses per clip for the family banks (default 3)")
    parser.add_argument("--stage-timeout", type=int, default=900,
                        help="seconds to wait for the binding receipt (stage-only)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print every step and path without doing anything")
    args = parser.parse_args(argv)

    if not 2 <= args.pose_limit <= 8:
        parser.error("--pose-limit must be 2..8")

    plan = build_plan(args)
    if args.dry_run:
        print_plan(plan)
        return 0

    if not plan.iso.is_file():
        parser.error(f"ISO not found: {plan.iso}")
    if not (plan.assets / "dataDir" / "stages").is_dir():
        parser.error(f"--assets must contain dataDir/stages/: {plan.assets}")
    return execute(plan, args)


if __name__ == "__main__":
    sys.exit(main())
