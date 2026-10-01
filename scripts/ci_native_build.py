#!/usr/bin/env python3
"""Fetch a CI-built Windows nectar.exe for a native branch or commit.

Agents should prefer this over building native/ locally: push the native branch
to the ``fork`` remote, then run::

    py -3.12 scripts/ci_native_build.py claude/my-branch
    py -3.12 scripts/ci_native_build.py 1a2b3c4d --no-wait

The script resolves the ref to a commit on GitHub, finds the ``Windows build``
workflow run for that commit (waiting for it to finish unless ``--no-wait``),
downloads the ``nectar-windows-<sha>`` artifact into ``output/ci-bin/<sha>/``,
verifies every file against the artifact's ``sha256.txt`` and prints the path
of ``nectar.exe`` on stdout (progress goes to stderr). Exit status is non-zero
if no successful run exists, the run failed, or a checksum does not match.

Requires an authenticated ``gh`` CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "4laric/Open-Nectar---Pikmin-Native-PC-Port"
DEFAULT_WORKFLOW = "windows.yml"
ARTIFACT_PREFIX = "nectar-windows-"


class CiError(RuntimeError):
    pass


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def gh(*args: str) -> str:
    try:
        result = subprocess.run(
            ["gh", *args], check=False, capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError as exc:
        raise CiError("gh CLI not found on PATH") from exc
    if result.returncode != 0:
        raise CiError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def resolve_sha(repo: str, ref: str) -> str:
    sha = gh("api", f"repos/{repo}/commits/{ref}", "--jq", ".sha").strip()
    if len(sha) != 40:
        raise CiError(f"could not resolve {ref!r} in {repo}")
    return sha


def list_runs(repo: str, workflow: str, sha: str) -> list[dict]:
    out = gh(
        "run", "list", "-R", repo, "--workflow", workflow, "--commit", sha,
        "--limit", "20", "--json", "databaseId,status,conclusion,event,headSha,url,createdAt",
    )
    return [run for run in json.loads(out) if run.get("headSha") == sha]


def pick_run(runs: list[dict]) -> dict | None:
    """Prefer a successful run, then an unfinished one; push runs before PR runs."""
    def rank(run: dict) -> tuple:
        success = run.get("conclusion") == "success"
        pending = run.get("status") != "completed"
        return (not success, not pending, run.get("event") != "push", run.get("createdAt", ""))

    usable = [r for r in runs if r.get("conclusion") in ("success", "", None) or r.get("status") != "completed"]
    if not usable:
        return None
    return sorted(usable, key=rank)[0]


def wait_for_run(repo: str, workflow: str, sha: str, timeout: float, poll: float, wait: bool) -> dict:
    deadline = time.monotonic() + timeout
    announced = None
    while True:
        runs = list_runs(repo, workflow, sha)
        run = pick_run(runs)
        if run is None and runs:
            failed = ", ".join(f"{r['url']} ({r.get('conclusion')})" for r in runs)
            raise CiError(f"no successful {workflow} run for {sha}: {failed}")
        if run is not None:
            if run.get("status") == "completed":
                if run.get("conclusion") != "success":
                    raise CiError(f"run {run['url']} concluded {run.get('conclusion')}")
                return run
            if announced != run["databaseId"]:
                log(f"waiting for {run['url']} ({run.get('status')})")
                announced = run["databaseId"]
        elif announced != "none":
            log(f"no {workflow} run for {sha} yet; has the branch been pushed?")
            announced = "none"
        if not wait:
            raise CiError("run not finished and --no-wait given")
        if time.monotonic() >= deadline:
            raise CiError(f"timed out after {timeout:.0f}s waiting for {workflow} on {sha}")
        time.sleep(poll)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(directory: Path) -> int:
    manifest = directory / "sha256.txt"
    if not manifest.is_file():
        raise CiError(f"missing {manifest}")
    checked = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        expected, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        actual = sha256_file(directory / name)
        if actual != expected.lower():
            raise CiError(f"sha256 mismatch for {name}: {actual} != {expected}")
        checked += 1
    if not (directory / "nectar.exe").is_file() or checked == 0:
        raise CiError(f"artifact in {directory} has no verified nectar.exe")
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ref", help="native branch name, tag or commit sha (pushed to GitHub)")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--out", type=Path, default=ROOT / "output" / "ci-bin")
    parser.add_argument("--timeout", type=float, default=3600, help="seconds to wait for the run")
    parser.add_argument("--poll", type=float, default=30)
    parser.add_argument("--no-wait", action="store_true", help="fail instead of waiting for a pending run")
    parser.add_argument("--json", action="store_true", help="print a JSON summary instead of the exe path")
    args = parser.parse_args(argv)

    try:
        sha = resolve_sha(args.repo, args.ref)
        log(f"{args.ref} -> {sha}")
        target = args.out / sha
        artifact = f"{ARTIFACT_PREFIX}{sha}"
        run: dict | None = None
        try:
            count = verify(target)
            log(f"already downloaded and verified ({count} files)")
        except CiError:
            run = wait_for_run(args.repo, args.workflow, sha, args.timeout, args.poll, not args.no_wait)
            log(f"downloading {artifact} from {run['url']}")
            target.mkdir(parents=True, exist_ok=True)
            for stale in target.iterdir():
                if stale.is_file():
                    stale.unlink()
            gh("run", "download", str(run["databaseId"]), "-R", args.repo, "-n", artifact, "-D", str(target))
            count = verify(target)
            log(f"verified {count} files against sha256.txt")
    except CiError as exc:
        log(f"error: {exc}")
        return 1

    exe = target / "nectar.exe"
    if args.json:
        print(json.dumps({
            "sha": sha,
            "artifact": artifact,
            "run": run["url"] if run else None,
            "exe": str(exe),
            "exe_sha256": sha256_file(exe),
        }, indent=2))
    else:
        print(exe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
