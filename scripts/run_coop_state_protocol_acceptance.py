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

    def check(self):
        if time.monotonic() >= self.end:
            raise TimeoutError("60second overall pair ceiling reached")


class SdlCommand:
    """Atomic file feeding only the fixture's actual SDL virtual controller."""
    def __init__(self, path: Path):
        self.path = path
        self.sequence = 0

    def publish(self, buttons=0, axes=(0, 0, 0, 0)):
        if type(buttons) is not int or not 0 <= buttons < 1 << 21:
            raise ValueError("SDL button bounds")
        if len(axes) != 4 or any(type(v) is not int or not -32768 <= v <= 32767 for v in axes):
            raise ValueError("SDL axis bounds")
        self.sequence += 1
        text = f"SDL1 {self.sequence} {buttons} {' '.join(map(str, axes))} END\n"
        pending = self.path.with_suffix(".pending")
        pending.write_bytes(text.encode("ascii"))
        # An open Windows reader can briefly prevent replace. No partial command
        # is exposed; keep the last complete file and retry on the next turn.
        try:
            os.replace(pending, self.path)
        except PermissionError:
            pending.unlink(missing_ok=True)
            return False
        return True


class OwnedChildren:
    def __init__(self):
        self.children = []
        self.streams = []

    def spawn(self, command, cwd, env, log):
        stream = log.open("wb")
        self.streams.append(stream)
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
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
    return captains == {0, 1} and "COOP_PROTOCOL_INVENTORY" in text and "COOP_PROTOCOL_FIXTURE_WINDOW 960x540 windowed centered" in text


def scrubbed_environment():
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("PIKMIN_NETPLAY_", "PIKMIN_COOP_", "PIKMIN_RANDOMIZER_")) or key in ("NECTAR_SAVE_DIR", "BBFT_PORT"):
            env.pop(key)
    env.update(SDL_AUDIODRIVER="dummy", PIKMIN_RANDOMIZER_TEST_BACKGROUND="1",
               PIKMIN_NETPLAY_UDP_BIND="127.0.0.1", PIKMIN_NETPLAY_ICE_BIND="127.0.0.1",
               PIKMIN_P2_ROOM_WINDOW="960x540")
    return env


def capture(args):
    # The deadline starts before staging/spawn/ICE pre-init, not engine idle.
    if not 4 < args.timeout <= 60:
        raise ValueError("capture needs a deadline within(4,60]seconds including4seconds for owned cleanup")
    deadline = Deadline(args.timeout - 4)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    owned = OwnedChildren()
    result = {"slice_passed": False, "gameplay_accepted": False, "mode": "capture-only",
              "remaining": "Ordinary gameplay/AP ReceivedItem, save/reconnect, legacy negotiation and guarded negative case oracles pending."}
    started = time.monotonic()
    try:
        result["inputs"] = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in (args.exe, args.bootstrap, args.manifest, Path(__file__))}
        result["runtime_dlls"] = {dll.name: hashlib.sha256(dll.read_bytes()).hexdigest()
                                  for dll in args.runtime_dir.glob("*.dll")}
        result["python_source"] = {
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.python_root, text=True).strip(),
            "dirty": subprocess.check_output(["git", "status", "--porcelain"], cwd=args.python_root, text=True).strip()}
        executable = out / args.exe.name
        shutil.copy2(args.exe, executable)
        for dll in args.runtime_dir.glob("*.dll"):
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
            feed = SdlCommand(stage / "sdl-input.txt")
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
            peers.append(owned.spawn(command, stage, env, log))
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
            owned.spawn(command, args.python_root.resolve(), base, out / f"helper-{role}.log")
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
    for name in ("exe", "runtime-dir", "assets", "bootstrap", "manifest", "python-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--case", choices=("p1", "p2", "thelynk"), required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--p2-assets", type=Path)
    parser.add_argument("--timeout", type=float, default=60)
    return capture(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
