"""#1148 real ICE/SDL pair orchestration, under implementation.

The current capture command records an actual guarded pair and native-created
external-state attachment. It deliberately emits no gameplay acceptance PASS;
case-specific ordinary gameplay/AP/save oracles are still being added.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


class Deadline:
    def __init__(self, seconds: float = 60):
        if not 0 < seconds <= 60:
            raise ValueError("overall deadline must be within60seconds")
        self.end = time.monotonic() + seconds

    def remaining(self):
        seconds = self.end - time.monotonic()
        if seconds <= 0:
            raise TimeoutError("60second overall pair ceiling reached")
        return seconds

    def check(self):
        self.remaining()


def replace_complete_command(pending, target):
    """Preserve POSIX/new-file publication; existing Windows file uses ReplaceFileW.

    The matching native fixture reader explicitly shares deletion. No5 retry:
    every native API refusal remains an OSError with its actual code and paths.
    """
    if os.name != "nt" or not target.exists():
        os.replace(pending, target)
        return
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    replace = kernel.ReplaceFileW
    replace.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                       wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p]
    replace.restype = wintypes.BOOL
    ctypes.set_last_error(0)
    if not replace(str(target), str(pending), None, 0, None, None):
        error = ctypes.WinError(ctypes.get_last_error())
        error.filename = str(pending)
        error.filename2 = str(target)
        raise error


class SdlCommand:
    """Same-owner atomic SDL feed; only identified sharing/lock violations retry."""
    def __init__(self, path: Path, deadline):
        self.path = path
        self.deadline = deadline
        self.sequence = 0
        self.events = []

    def event(self, disposition, attempt, error=None):
        row = dict(sequence=self.sequence, path=str(self.path),
                   disposition=disposition, attempt=attempt,
                   monotonic=time.monotonic())
        if error is not None:
            row.update(exception=type(error).__name__, errno=error.errno,
                       winerror=getattr(error, "winerror", None),
                       filename=error.filename, filename2=error.filename2)
        self.events.append(row)
        with self.path.with_suffix(".publication.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")

    def publish(self, buttons=0, axes=(0, 0, 0, 0)):
        if type(buttons) is not int or not 0 <= buttons < 1 << 21:
            raise ValueError("SDL button bounds")
        if len(axes) != 4 or any(type(v) is not int or not -32768 <= v <= 32767 for v in axes):
            raise ValueError("SDL axis bounds")
        nonzero = buttons != 0 or any(axes)
        if nonzero:
            self.deadline.check()
        self.sequence += 1
        text = f"SDL1 {self.sequence} {buttons} {' '.join(map(str, axes))} END\n"
        pending = self.path.with_suffix(".pending")
        pending.write_bytes(text.encode("ascii"))
        retry_end = min(time.monotonic() + 0.050, self.deadline.end)
        try:
            for attempt in range(1, 12):
                if nonzero:
                    self.deadline.check()  # Preserve absolute-phase timeout semantics.
                if attempt > 1 and time.monotonic() >= retry_end:
                    return False  # No retry after audit/scheduling consumed its window.
                if nonzero:
                    self.deadline.check()  # Every replacement, including a retry.
                try:
                    replace_complete_command(pending, self.path)
                    if attempt > 1:
                        self.event("published-after-transient-sharing-retry", attempt)
                    return True
                except PermissionError as error:
                    #111 did not retain the code. Only actual32/33 justify retries;
                    # access-denied5/unknown PermissionError remain fail-closed.
                    transient = getattr(error, "winerror", None) in (32, 33)
                    self.event("identified-sharing-violation" if transient else "refused", attempt, error)
                    # Actual audit I/O can consume time; recompute AFTER it.
                    remaining = retry_end - time.monotonic()
                    if not transient or attempt >= 11 or remaining <= 0:
                        return False
                    if nonzero:
                        self.deadline.check()
                    time.sleep(min(0.005, remaining))
        finally:
            pending.unlink(missing_ok=True)


class OwnedChildren:
    def __init__(self):
        self.children = []
        self.streams = []

    def spawn(self, command, cwd, env, log, deadline):
        stream = log.open("wb")
        self.streams.append(stream)
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        deadline.check()  # Immediately before actual process creation, after log/staging work.
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT, creationflags=flags)
        self.children.append(child)
        return child

    def close(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
        graceful_end = time.monotonic() + 2
        stubborn = []
        for child in self.children:
            try:
                child.wait(timeout=max(0, graceful_end - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                stubborn.append(child)
        killed_end = time.monotonic() + 2
        for child in stubborn:
            child.wait(timeout=max(0, killed_end - time.monotonic()))
        for stream in self.streams:
            stream.close()


def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def wait_until(predicate, deadline, peers):
    while True:
        deadline.check()
        value = predicate()
        if value:
            return value
        for peer in peers:
            if peer.poll() is not None:
                raise RuntimeError(f"owned native peer exited{peer.returncode} before readiness")
        time.sleep(.02)


def native_run(log):
    match = re.search(r"\[netplay\] launch: role=\w+.*run dir (.+)", read(log))
    return Path(match.group(1).strip()) if match else None


def token_run(run):
    candidates = list((run / "session/runs").glob("*/bootstrap.txt"))
    if len(candidates) != 1 or not re.fullmatch(r"[0-9a-f]{64}", candidates[0].parent.name):
        return None
    return candidates[0].parent


def observed_start(log):
    text = read(log)
    captains = set()
    for captain, alive, hp in re.findall(r"COOP_PROTOCOL_OBSERVE .*captain=(\d+) alive=(\d+) state=\d+ hp=([0-9.]+)", text):
        if int(alive) == 20 and float(hp) > 0:
            captains.add(int(captain))
    return captains == {0, 1} and "COOP_PROTOCOL_INVENTORY" in text and "COOP_PROTOCOL_FIXTURE_WINDOW measured=1 width=960 height=540 centered=1 windowed=1" in text


def scrubbed_environment():
    env = dict(os.environ)
    for key in list(env):
        if key.upper().startswith(("PIKMIN_", "P2_")) or key.upper() in ("NECTAR_SAVE_DIR", "BBFT_PORT"):
            env.pop(key)
    env.update(SDL_AUDIODRIVER="dummy", PIKMIN_RANDOMIZER_TEST_BACKGROUND="1",
               PIKMIN_NETPLAY_UDP_BIND="127.0.0.1", PIKMIN_NETPLAY_ICE_BIND="127.0.0.1",
               PIKMIN_P2_ROOM_WINDOW="960x540")
    return env


DLLS = ("SDL2.dll", "libgcc_s_seh-1.dll", "libstdc++-6.dll", "libwinpthread-1.dll")


def artifact_preflight(exe, directory, native_sha):
    """Require actual selected ON CI artifact identity and every runtime byte."""
    exe, directory = exe.resolve(), directory.resolve()
    if exe.parent != directory or not re.fullmatch(r"[0-9a-f]{40}", native_sha):
        raise ValueError("fixture executable and DLLs require one pinned CI artifact directory")
    info_path, hashes_path = directory / "BUILD_INFO.txt", directory / "sha256.txt"
    info = info_path.read_text(encoding="utf-8")
    required = (f"compiled_commit {native_sha}", "profile netplay=ON",
                f"selected_target {exe.stem}",
                "guard_root 36ac5ddd2877b9308276f96b28a81e137ae58c5a",
                "guard_sha256 ee2bfeaba96020f4f0ae310f9cf98dfabbd824353d20de6fb78fec17001f3ff9")
    lines = info.splitlines()
    if any(lines.count(line) != 1 for line in required):
        raise ValueError("CI compiled source/profile/selected fixture/guard identity mismatch")
    trees = [line for line in lines if line.startswith("compiled_tree ")]
    if len(trees) != 1 or not re.fullmatch(r"compiled_tree [0-9a-f]{40}", trees[0]):
        raise ValueError("CI compiled tree identity absent")
    declared = {}
    for line in hashes_path.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64}) [ *](?:\./)?([^/\\]+)", line)
        if not match or match[2] in declared:
            raise ValueError("CI hash manifest malformed/duplicate")
        declared[match[2]] = match[1]
    verified = {}
    for name in (exe.name, *DLLS):
        path = directory / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if declared.get(name) != actual:
            raise ValueError(f"CI byte mismatch or absent hash: {name}")
        verified[name] = actual
    return {"native_sha": native_sha, "build_info": info,
            "build_info_sha256": hashlib.sha256(info_path.read_bytes()).hexdigest(),
            "manifest_sha256": hashlib.sha256(hashes_path.read_bytes()).hexdigest(), "files": verified}


def capture(args):
    # The deadline starts before staging/spawn/ICE pre-init, not engine idle.
    if not 4 < args.timeout <= 60:
        raise ValueError("capture needs a deadline within(4,60]seconds including4seconds for owned cleanup")
    deadline = Deadline(args.timeout - 4)
    preflight = artifact_preflight(args.exe, args.runtime_dir, args.native_sha)
    actual_root = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.python_root, text=True, timeout=deadline.remaining()).strip()
    root_dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=args.python_root, text=True, timeout=deadline.remaining()).strip()
    if actual_root != args.root_sha or root_dirty:
        raise ValueError("Python consumer must be exact clean requested source")
    deadline.check()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    owned = OwnedChildren()
    result = {"slice_passed": False, "gameplay_accepted": False, "mode": "capture-only",
              "remaining": "Ordinary gameplay/AP ReceivedItem, save/reconnect, legacy negotiation and guarded negative case oracles pending."}
    started = deadline.end - (args.timeout - 4)
    result["artifact_preflight"] = preflight
    result["staging"] = "Caller-provided bootstrap/manifest are hashed here. Linked assets require the separately frozen actual stage/hash receipt recorded in inputs; this runner does not hash linked asset contents. No claim of natural population or gameplay from readiness. Deadline includes artifact verification, staging, startup and owned cleanup."
    try:
        result["inputs"] = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in (args.exe, args.bootstrap, args.manifest, args.stage_receipt, Path(__file__))}
        result["runtime_dlls"] = {dll.name: hashlib.sha256(dll.read_bytes()).hexdigest()
                                  for dll in (args.runtime_dir / name for name in DLLS)}
        result["python_source"] = {
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.python_root, text=True, timeout=deadline.remaining()).strip(),
            "dirty": subprocess.check_output(["git", "status", "--porcelain"], cwd=args.python_root, text=True, timeout=deadline.remaining()).strip()}
        executable = out / args.exe.name
        shutil.copy2(args.exe, executable)
        for dll in (args.runtime_dir / name for name in DLLS):
            shutil.copy2(dll, out / dll.name)
        offer, answer = out / "offer.txt", out / "answer.txt"
        base = scrubbed_environment()
        peers, logs, commands = [], [], []
        for role in (0, 1):
            stage = out / ("host" if role == 0 else "client")
            stage.mkdir()
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(args.assets.resolve()), str(stage / "assets"))
            else:
                (stage / "assets").symlink_to(args.assets.resolve(), target_is_directory=True)
            feed = SdlCommand(stage / "sdl-input.txt", deadline)
            feed.publish()
            env = dict(base, PIKMIN_COOP_FIXTURE_INPUT=str(feed.path))
            command = [str(executable), "--netplay-test-hidden", "--netplay-input", "auto",
                       "--netplay-external-state", "--netplay-run-root", str(stage / "runs")]
            if role == 0:
                command += ["--netplay-host-ice", "--netplay-code-out", str(offer),
                            "--netplay-answer-in", str(answer), "--bootstrap", str(args.bootstrap.resolve())]
            else:
                wait_until(lambda: read(offer).strip().startswith("NPIX"), deadline, peers)
                command += ["--netplay-join-ice", "@" + str(offer), "--netplay-code-out", str(answer)]
                if args.p2_assets:
                    command += ["--netplay-p2-assets", str(args.p2_assets.resolve())]
            log = stage / "native.log"
            peers.append(owned.spawn(command, stage, env, log, deadline))
            logs.append(log)
            commands.append(feed)
        for role in (0, 1):
            run = wait_until(lambda: native_run(logs[role]), deadline, peers)
            native_token = wait_until(lambda: token_run(run), deadline, peers)
            bootstrap_before = (native_token / "bootstrap.txt").read_bytes()
            module = "randomizer.thelynk" if args.case == "thelynk" else "randomizer"
            command = [sys.executable, "-m", module]
            if module == "randomizer":
                command.append("run")
            command += [str(args.manifest.resolve()), "--session-dir", str(run / "session"),
                        "--attach-native-run", str(native_token)]
            command += ["--server", args.server] if role == 0 else ["--netplay-client"]
            owned.spawn(command, args.python_root.resolve(), base, out / f"helper-{role}.log", deadline)
            if (native_token / "bootstrap.txt").read_bytes() != bootstrap_before:
                raise RuntimeError("native bootstrap changed during Python attach")
            result[f"native_run_{role}"] = str(run)
        # Neutral baseline capture is distinct from a case-specific mechanic.
        # Repeat real SDL neutral commands so the500mswatchdog stays live.
        while True:
            deadline.check()
            for feed in commands:
                feed.publish()
            if all(observed_start(log) for log in logs):
                result["actual_guarded_observation"] = True
                break
            for peer in peers:
                if peer.poll() is not None:
                    raise RuntimeError(f"owned native peer exited{peer.returncode}")
            time.sleep(.05)
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        try:
            owned.close()
        except Exception as exc:
            result["error"] = f"owned cleanup failure: {exc}"
        result["elapsed_seconds"] = time.monotonic() - started
        result["owned_children_exited"] = all(p.poll() is not None for p in owned.children)
        result["cleanup_method"] = "Owned process termination for capture only; no normal save/shutdown acceptance."
        result["child_exit_codes"] = [p.returncode for p in owned.children]
        result["artifacts"] = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in out.rglob("*.log")}
        (out / "capture-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 1 if "error" in result else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-only", action="store_true", required=True)
    for name in ("exe", "runtime-dir", "assets", "bootstrap", "manifest", "python-root", "stage-receipt", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--native-sha", required=True)
    parser.add_argument("--root-sha", required=True)
    parser.add_argument("--case", choices=("p1", "p2", "thelynk"), required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--p2-assets", type=Path)
    parser.add_argument("--timeout", type=float, default=60)
    return capture(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
