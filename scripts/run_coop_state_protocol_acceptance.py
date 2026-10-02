"""#1148 real ICE/SDL pair orchestration, under implementation.

The current capture command records an actual guarded pair and native-created
external-state attachment. It deliberately emits no gameplay acceptance PASS;
case-specific ordinary gameplay/AP/save oracles are still being added.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback


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


def generation_tick_ms():
    if os.name != "nt":
        raise ValueError("Generation input requires the reviewed Windows boot clock")
    import ctypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    tick = kernel.GetTickCount64
    tick.argtypes = []
    tick.restype = ctypes.c_ulonglong
    return int(tick())


def generation_move_new(pending, destination):
    if os.name != "nt":
        raise ValueError("No unreviewed generation transport fallback")
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    move = kernel.MoveFileExW
    move.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    move.restype = wintypes.BOOL
    ctypes.set_last_error(0)
    if not move(str(pending), str(destination), 0):
        error = ctypes.WinError(ctypes.get_last_error())
        error.filename, error.filename2 = str(pending), str(destination)
        raise error


def generation_file_state(path):
    try:
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        if (before.st_dev, before.st_ino, before.st_size) != (after.st_dev, after.st_ino, after.st_size):
            raise RuntimeError("Generation changed during evidence read")
        return dict(present=True, device=after.st_dev, identity=after.st_ino,
                    bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    except FileNotFoundError:
        return dict(present=False)


class SdlGenerationCommand:
    """Optional immutable Windows fixture transport; any publication error poisons it."""
    def __init__(self, path, deadline, cleanup_end=None):
        generation_tick_ms()  # refuse unsupported host before directory creation
        if type(deadline.end) not in (int, float) or not math.isfinite(deadline.end):
            raise ValueError("Finite absolute mechanics deadline required")
        if cleanup_end is not None and (type(cleanup_end) not in (int, float)
                or not math.isfinite(cleanup_end) or not deadline.end <= cleanup_end <= deadline.end + 4):
            raise ValueError("Explicit cleanup reserve within four seconds required")
        self.directory = Path(path).resolve()
        try:
            directory_bytes = str(self.directory).encode("ascii")
        except UnicodeError:
            raise ValueError("Fixture's ANSI snapshot boundary requires an ASCII private path")
        if len(directory_bytes) + 26 >= 260:
            raise ValueError("Fixture generation path exceeds reviewed ANSI path limit")
        if not any(parent.name.casefold() == "output" for parent in self.directory.parents):
            raise ValueError("Private output generation directory required")
        self.directory.mkdir(exist_ok=False)
        self.audit_path = self.directory.parent / (self.directory.name + ".publication.jsonl")
        with self.audit_path.open("xb") as stream:
            owned_audit = os.fstat(stream.fileno())
        self.audit_identity = (owned_audit.st_dev, owned_audit.st_ino)
        self.audit_size = 0
        self.deadline, self.cleanup_end = deadline, cleanup_end
        self.sequence, self.last_tick = 0, None
        self.failed = False
        self.latest_ready = None
        self.events = []

    @property
    def path(self):
        return self.latest_ready if self.latest_ready is not None else self.directory

    def event(self, row):
        self.events.append(row)
        with self.audit_path.open("r+b") as stream:
            owned = os.fstat(stream.fileno())
            current = self.audit_path.stat()
            if ((owned.st_dev, owned.st_ino) != self.audit_identity
                    or (current.st_dev, current.st_ino) != self.audit_identity
                    or owned.st_size != self.audit_size):
                raise RuntimeError("Owned generation audit identity/size changed")
            stream.seek(0, os.SEEK_END)
            stream.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))
            stream.flush()
            current = self.audit_path.stat()
            if (current.st_dev, current.st_ino) != self.audit_identity:
                raise RuntimeError("Owned generation audit replaced during write")
            self.audit_size = os.fstat(stream.fileno()).st_size

    def publish(self, buttons=0, axes=(0, 0, 0, 0)):
        self.deadline.check()
        return self._publish(buttons, axes, self.deadline.end)

    def publish_cleanup(self):
        if self.cleanup_end is None:
            raise ValueError("Explicit reserved cleanup deadline absent")
        if type(self.cleanup_end) not in (int, float) or not math.isfinite(self.cleanup_end) or not self.deadline.end <= self.cleanup_end <= self.deadline.end + 4:
            raise ValueError("Cleanup reserve changed outside four-second bound")
        return self._publish(0, (0, 0, 0, 0), self.cleanup_end)

    def _publish(self, buttons, axes, end):
        if self.failed:
            raise RuntimeError("Generation transport failed; no retry or further publication")
        if type(end) not in (int, float) or not math.isfinite(end) or time.monotonic() >= end:
            raise TimeoutError("Generation absolute publication deadline exhausted")
        if type(buttons) is not int or not 0 <= buttons < (1 << 21) or len(axes) != 4 or any(
                type(axis) is not int or not -32768 <= axis <= 32767 for axis in axes):
            raise ValueError("Canonical SDL generation bounds")
        if self.sequence >= 4096:
            raise ValueError("Generation retention ceiling reached; no active-run pruning")
        sequence = self.sequence + 1
        tick = generation_tick_ms()
        if type(tick) is not int or not 0 <= tick < (1 << 64) or (self.last_tick is not None and tick < self.last_tick):
            raise ValueError("Generation boot clock regressed or invalid")
        raw = f"SDL2 {sequence} {tick} {buttons} {' '.join(map(str, axes))} END\n".encode("ascii")
        if len(raw) >= 256:
            raise ValueError("Generation snapshot length")
        destination = self.directory / f"g{sequence:020d}.sdl"
        pending = destination.with_suffix(".pending")
        if destination.exists() or pending.exists():
            self.failed = True
            raise FileExistsError("Existing generation/creator path refuses publication")
        api_succeeded = False
        try:
            with pending.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                created = os.fstat(stream.fileno())
                owned = dict(present=True, device=created.st_dev, identity=created.st_ino,
                             bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            if generation_file_state(pending) != owned:
                raise RuntimeError("Exclusive creator identity/expected bytes changed")
            if time.monotonic() >= end:
                raise TimeoutError("Publication deadline before new-name move")
            generation_move_new(pending, destination)  # SAME directory; flags0, exactly once
            api_succeeded = True
            self.sequence, self.last_tick, self.latest_ready = sequence, tick, destination
            actual = generation_file_state(destination)
            if actual != owned:
                raise RuntimeError("Published complete generation differs from creator")
            self.event(dict(sequence=sequence, published_tick=tick, path=str(destination),
                            disposition="published", api="MoveFileExW flags0", attempt=1,
                            target_after=actual, input_application_proven=False))
            return True
        except BaseException as error:
            self.failed = True  # never reattempt this generation or switch API
            row = dict(sequence=sequence, path=str(destination), api="MoveFileExW flags0", attempt=1,
                       disposition="published-evidence-failed" if api_succeeded else "refused",
                       api_succeeded=api_succeeded, exception=type(error).__name__,
                       winerror=getattr(error, "winerror", None), errno=getattr(error, "errno", None),
                       filename=getattr(error, "filename", None), filename2=getattr(error, "filename2", None))
            for label, file in (("pending", pending), ("destination", destination)):
                try:
                    row[label + "_after_error"] = generation_file_state(file)
                except BaseException as secondary:
                    row[label + "_audit_error"] = repr(secondary)
            try:
                self.event(row)
            except BaseException as secondary:
                error.add_note("Secondary generation evidence failure: " + repr(secondary))
            raise  # Retain owned pending/ready evidence; no deletion or retry.


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

    def close(self, absolute_end=None):
        failures = []
        for child in self.children:
            if child.poll() is None:
                try:
                    child.terminate()
                except Exception as error:
                    failures.append(error)
        graceful_end = time.monotonic() + 2
        if absolute_end is not None:
            graceful_end = min(graceful_end, absolute_end - 2)
        stubborn = []
        for child in self.children:
            try:
                child.wait(timeout=max(0, graceful_end - time.monotonic()))
            except subprocess.TimeoutExpired:
                stubborn.append(child)
                try:
                    child.kill()
                except Exception as error:
                    failures.append(error)
            except Exception as error:
                failures.append(error)
                stubborn.append(child)
                if child.poll() is None:
                    try:
                        child.kill()
                    except Exception as secondary:
                        failures.append(secondary)
        killed_end = time.monotonic() + 2
        if absolute_end is not None:
            killed_end = min(killed_end, absolute_end)
        for child in stubborn:
            try:
                child.wait(timeout=max(0, killed_end - time.monotonic()))
            except Exception as error:
                failures.append(error)
        for stream in self.streams:
            try:
                stream.close()
            except Exception as error:
                failures.append(error)
        if failures:
            raise ExceptionGroup("Owned cleanup failures after attempting every child", failures)


def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def exception_evidence(error):
    return dict(exception=type(error).__name__, message=str(error),
                winerror=getattr(error, "winerror", None), errno=getattr(error, "errno", None),
                filename=getattr(error, "filename", None), filename2=getattr(error, "filename2", None),
                notes=list(getattr(error, "__notes__", [])),
                traceback="".join(traceback.format_exception(error)))


def finish_capture(result, owned, commands, transport, overall_end):
    result["neutral_cleanup"] = []
    if transport == "generations":
        for feed in commands:
            row = dict(directory=str(feed.directory), input_application_proven=False)
            if feed.failed:
                row["disposition"] = "skipped-poisoned-transport"
            else:
                try:
                    feed.publish_cleanup()
                    row.update(disposition="published", sequence=feed.sequence)
                except Exception as error:
                    row.update(disposition="failed", failure=exception_evidence(error))
                    result.setdefault("secondary_errors", []).append(row["failure"])
                    result.setdefault("error", "Reserved neutral cleanup failed")
            result["neutral_cleanup"].append(row)
    try:
        owned.close(absolute_end=overall_end) if transport == "generations" else owned.close()
    except Exception as error:
        result.setdefault("secondary_errors", []).append(exception_evidence(error))
        result.setdefault("error", "Owned cleanup failed")


def capture_artifacts(out, commands, transport, result, queue_directories=None):
    paths = list(out.glob("*.log")) if transport == "generations" else list(out.rglob("*.log"))
    if transport == "generations":
        directories = queue_directories if queue_directories is not None else [feed.directory for feed in commands]
        for directory in directories:
            paths.extend((directory.parent / "native.log", directory.parent / (directory.name + ".publication.jsonl")))
            try:
                if directory.is_symlink() or directory.is_junction():
                    raise RuntimeError("Owned queue evidence path is a reparse entry")
                if directory.exists():
                    for count, entry in enumerate(directory.iterdir(), 1):
                        if count > 4097:
                            raise RuntimeError("Owned queue evidence enumeration ceiling")
                        if not re.fullmatch(r"g[0-9]{20}\.(?:sdl|pending)", entry.name):
                            raise RuntimeError("Unexpected queue evidence entry")
                        paths.append(entry)
            except Exception as error:
                result.setdefault("secondary_errors", []).append(exception_evidence(error))
                result.setdefault("error", "Capture queue enumeration failed")
    artifacts = {}
    for path in paths:
        try:
            if path.is_symlink() or path.is_junction():
                raise RuntimeError("Refusing foreign reparse artifact target")
            if path.is_file():
                artifacts[path.relative_to(out).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception as error:
            result.setdefault("secondary_errors", []).append(exception_evidence(error))
            result.setdefault("error", "Capture artifact evidence failed")
    return artifacts


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
    transport = getattr(args, "input_transport", "file")
    if transport not in ("file", "generations"):
        raise ValueError("Unknown fixture input transport")
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
    commands = []
    queue_directories = []
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
        peers, logs = [], []
        for role in (0, 1):
            stage = out / ("host" if role == 0 else "client")
            stage.mkdir()
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(args.assets.resolve()), str(stage / "assets"))
            else:
                (stage / "assets").symlink_to(args.assets.resolve(), target_is_directory=True)
            if transport == "generations":
                queue_directories.append(stage / "sdl-generations")
                feed = SdlGenerationCommand(queue_directories[-1], deadline, deadline.end + 4)
            else:
                feed = SdlCommand(stage / "sdl-input.txt", deadline)
            commands.append(feed)
            feed.publish()
            if transport == "generations":
                env = dict(base, PIKMIN_COOP_FIXTURE_INPUT_DIR=str(feed.directory),
                           PIKMIN_RANDOMIZER_TEST_BACKGROUND="1", SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS="1")
            else:
                env = dict(base, PIKMIN_COOP_FIXTURE_INPUT=str(feed.path))
            command = [str(executable), "--netplay-test-hidden", "--netplay-input", "gamepad:0" if transport == "generations" else "auto",
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
                if transport == "generations" and any(
                        not re.search(r"COOP_PROTOCOL_FIXTURE_INPUT[^\n]*\binput_protocol=2\b", read(log))
                        for log in logs):
                    raise RuntimeError("Generation transport requires both new SDK protocol advertisements")
                result["actual_guarded_observation"] = True
                break
            for peer in peers:
                if peer.poll() is not None:
                    raise RuntimeError(f"owned native peer exited{peer.returncode}")
            time.sleep(.05)
    except Exception as exc:
        result["error"] = str(exc)
        result["primary_error"] = exception_evidence(exc)
    finally:
        finish_capture(result, owned, commands, transport, deadline.end + 4)
        result["elapsed_seconds"] = time.monotonic() - started
        result["owned_children_exited"] = all(p.poll() is not None for p in owned.children)
        result["cleanup_method"] = "Owned process termination for capture only; no normal save/shutdown acceptance."
        result["child_exit_codes"] = [p.returncode for p in owned.children]
        try:
            result["artifacts"] = capture_artifacts(out, commands, transport, result, queue_directories)
        except Exception as error:
            result.setdefault("secondary_errors", []).append(exception_evidence(error))
            result.setdefault("error", "Capture artifact collection failed")
        try:
            (out / "capture-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        except Exception as error:
            result.setdefault("secondary_errors", []).append(exception_evidence(error))
            result.setdefault("error", "Capture result publication failed")
    print(json.dumps(result))
    return 1 if "error" in result else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-only", action="store_true", required=True)
    for name in ("exe", "runtime-dir", "assets", "bootstrap", "manifest", "python-root", "stage-receipt", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--native-sha", required=True)
    parser.add_argument("--root-sha", required=True)
    parser.add_argument("--input-transport", choices=("file", "generations"), default="file",
                        help="Optional generation mode requires a separately reviewed new matching SDK")
    parser.add_argument("--case", choices=("p1", "p2", "thelynk"), required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--p2-assets", type=Path)
    parser.add_argument("--timeout", type=float, default=60)
    return capture(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
