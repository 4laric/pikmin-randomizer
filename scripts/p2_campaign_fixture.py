"""Reusable non-preview P2 campaign fixture (issue #837).

Productizes the successful issue #830 non-preview campaign setup as reusable
root tooling. It starts a real enabled randomizer session and stays
species-contract driven. It is infrastructure, not gameplay proof: it makes no
gameplay claim, pool admission, shared AP relink or user-game mutation.

Pipeline (each step is fail-closed and importable without booting the game):

* ``stage_campaign`` generates a real ``randomizer.seed.generate`` P2 seed,
  derives production actor bindings (``scripts/p2_prepare_content``), opens a
  short private session path (``randomizer.session.Session`` +
  ``randomizer.runner.NativeRun`` bootstrap with the production ``ENEMY_P2``
  block), stages content/actors (``experimental.pikmin2_family_install`` ->
  ``install_layout``) and writes an immutable fixture manifest recording
  root/native/executable/assets/seed/session hashes, 960x540 centred startup,
  the captain guard hash and the species marker contract.
* ``build_command`` constructs the production campaign boot
  ``[exe, --randomizer-seed, bootstrap]`` and refuses any preview flag, so the
  ``pc_bbft`` bridge-only early return (``--experimental-pikmin2-room``) that
  made the #830 gen-3 runs preview-only can never be staged as a campaign.
* ``supervise`` delegates bounded process supervision: hidden window,
  ``PIKMIN_P2_ROOM_WINDOW=960x540``, session keepalive thread
  (``run.poll`` + ``write_state``), stop-by-PID after ``--seconds``.
* ``parse_native_log`` / ``evaluate`` check the enabled-session handshake
  (``SESSION enabled=1 ready=1``), captain guard markers (``#632``,
  ``P2_FIXTURE_CAPTAIN_DOWN`` -> BLOCKED, exit 86) and caller-supplied
  species-specific pass/block marker contracts.

Fail-closed summary: preview mode, hand-written ``ENEMY_P2`` rows (any staged
bootstrap line that is not byte-equal to the production derivation for the
manifest), stale content/executable, missing session handshake, unsafe session
paths, missing captain guard, or an unbounded launch all raise
``FixtureRejected`` and nothing launches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCHEMA = 1

WINDOW_ENV = "PIKMIN_P2_ROOM_WINDOW"
WINDOW_GEOMETRY = "960x540"
GUARD_SOURCE = ROOT / "scripts/p2_fixture_captain_guard.h"
GUARD_EXIT_CODE = 86

# Any of these on the boot argv selects the preview bridge path, where
# pc_randomizer_init never runs and no enabled session exists. Refused.
PREVIEW_FLAGS = (
    "--experimental-pikmin2-room",
    "--preview",
    "--preview-pikmin2",
    "--campaign-preview",
)

# Markers that prove nothing natural happened; their presence only labels a
# run as non-natural. Kept here so reports use one vocabulary.
NONNATURAL_MARKERS = (
    "forced-transport",
    "injected-damage",
    "health-write",
    "state-write",
    "simulated-receipt",
    "vehicle",
    "host",
    "proxy",
)

CAPTAIN_DOWN_MARKERS = ("P2_FIXTURE_CAPTAIN_DOWN", "CAPTAIN_DOWN")
WORLD_RENDERED_MARKER = "PIKMIN_WORLD_RENDERED"
SESSION_HANDSHAKE_RE = re.compile(r"SESSION\s+enabled=1\s+ready=1\b")

# Reusable species marker contracts (issue #842 adoption).
#
# ``setup_markers`` prove staging/binding only: generic bind/ready shapes the
# smoke parser counts toward ``bound`` (``P2_<X>_BIND generator=``,
# ``P2_ENEMY_READY species=``) plus species ready/staging markers. They never
# prove gameplay.
# ``behavior_markers`` prove natural gameplay beyond setup (delivery, collect,
# corpse receipt, natural attack/death). Consumers require them via
# ``pass_markers``; a setup-only log (bound, handshake, boot, but no behavior
# marker) then fails closed with "no species pass marker observed". Some
# behavior markers (notably ``*_DELIVERY_BIND``) additionally match the generic
# bind shape; the setup/behavior distinction is enforced by the pass-marker
# requirement, not by bind accounting.
# ``block_markers`` are species setup aborts/skips; any hit is FAIL.
# Marker strings below are transcribed from the species lanes; the Sarai
# delivery-bind entry is the campaign delivery analogue of the Sokkuri
# delivery bind (consumer regex; setup-only logs without it fail closed).
SPECIES_MARKER_CONTRACTS = {
    "sarai": {
        "source_ids": (23,),
        "setup_markers": (
            r"P2_SARAI_READY\s+source_id=23\b",
            r"P2_SARAI_BIND\b.*?generator=\d+",
            r"P2_ENEMY_READY\s+species=Sarai\b.*?generator=\d+",
        ),
        "behavior_markers": (
            r"P2_SARAI_CORPSE_READY\b",
            r"P2_SARAI_DELIVERY_BIND\b.*?generator=\d+",
        ),
        "block_markers": (
            r"P2_SETUP_ABORT\s+Sarai\b",
            r"P2_SETUP_SKIP\s+Sarai\b",
        ),
    },
    "kogane": {
        "source_ids": (9, 10, 11),
        "setup_markers": (
            r"P2_KOGANE_BIND\b.*?generator=\d+",
            r"P2_ENEMY_READY\s+species=Kogane\b.*?generator=\d+",
        ),
        "behavior_markers": (
            r"P2_KOGANE_COLLECT_PASS\b",
            r"P2_KOGANE_NATURAL_ATTACK\b",
        ),
        "block_markers": (
            r"P2_SETUP_ABORT\s+Kogane\b",
            r"P2_SETUP_SKIP\s+Kogane\b",
        ),
    },
    "kurage": {
        "source_ids": (57,),
        "setup_markers": (
            r"P2_KURAGE_TEKI_READY\b",
            r"P2_KURAGE_TEKI_CORPSE\b",
            r"P2_ENEMY_READY\s+species=Kurage\b.*?generator=\d+",
        ),
        "behavior_markers": (
            r"P2_KURAGE_CORPSE_RECEIPT_PASS\s+generator=\d+",
            r"P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS\s+generator=\d+",
            r"P2_KURAGE_CORPSE_CLEANUP_PASS\b",
        ),
        "block_markers": (
            r"P2_SETUP_ABORT\s+Kurage\b",
            r"P2_SETUP_SKIP\s+Kurage\b",
        ),
    },
    "sokkuri": {
        "source_ids": (79,),
        "setup_markers": (
            r"P2_SOKKURI_BIND\b.*?generator=\d+",
            r"P2_ENEMY_READY\s+species=Sokkuri\b.*?generator=\d+",
        ),
        "behavior_markers": (
            r"P2_SOKKURI_DELIVERY_BIND\b.*?generator=\d+",
            r"P2_SOKKURI_DEAD\b",
            r"P2_SOKKURI79_DELIVERED_TO_GOAL\b",
            r"P2_ORDINARY_P2_RECEIPT\b.*?id=onion:p2:79\b",
        ),
        "block_markers": (
            r"P2_SETUP_ABORT\s+Sokkuri\b",
            r"P2_SETUP_SKIP\s+Sokkuri\b",
        ),
    },
}


def species_contract(name):
    """Return the reusable marker contract for a species (case-insensitive).

    Raises ``FixtureRejected`` on an unknown species so consumers cannot
    silently run with an empty contract.
    """
    key = str(name).strip().lower()
    if key not in SPECIES_MARKER_CONTRACTS:
        raise FixtureRejected(
            "unknown species contract: %r (expected one of: %s)"
            % (name, ", ".join(sorted(SPECIES_MARKER_CONTRACTS))))
    contract = SPECIES_MARKER_CONTRACTS[key]
    return {
        "species": key,
        "source_ids": tuple(contract["source_ids"]),
        "setup_markers": list(contract["setup_markers"]),
        "behavior_markers": list(contract["behavior_markers"]),
        "block_markers": list(contract["block_markers"]),
    }


def consumer_markers(name):
    """Return the consumer referral for a species: behavior pass markers plus
    species block markers.

    Consumers pass these straight into ``launch --pass-marker/--block-marker``
    (or ``parse_native_log``/``evaluate``). Setup markers are returned for
    documentation only; the fixture already counts binds generically.
    """
    contract = species_contract(name)
    return {
        "species": contract["species"],
        "source_ids": contract["source_ids"],
        "pass_markers": list(contract["behavior_markers"]),
        "block_markers": list(contract["block_markers"]),
        "setup_markers": list(contract["setup_markers"]),
    }

MAX_SECONDS = 600.0
SESSION_DIR_MAX_LEN = 100
BOOTSTRAP_PATH_MAX_LEN = 200


class FixtureRejected(ValueError):
    """A fixture precondition failed; nothing was launched."""


def sha256(path):
    """Hex sha256 of a file."""
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _git_head(repo):
    code, text = _run_capture(["git", "-C", str(repo), "rev-parse", "HEAD"])
    if code:
        raise FixtureRejected("cannot read git HEAD of " + str(repo))
    return text.strip()


def _run_capture(args):
    try:
        completed = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        raise FixtureRejected("cannot run helper: " + str(error)) from error
    return completed.returncode, completed.stdout


def require_no_preview(argv):
    """Reject any preview-mode flag; returns the argv as a list."""
    words = [str(word) for word in argv]
    for word in words:
        lowered = word.lower()
        if word in PREVIEW_FLAGS or lowered.startswith("--experimental-"):
            raise FixtureRejected(
                "preview flag refused on a campaign boot: " + word)
    return words


def require_guard(guard_source=GUARD_SOURCE):
    """Return the sha256 of the #632 captain guard header, or fail closed."""
    guard_source = Path(guard_source)
    if not guard_source.is_file():
        raise FixtureRejected(
            "captain guard missing: " + str(guard_source))
    text = guard_source.read_text(encoding="utf-8")
    if "p2_fixture_require_captain" not in text or "P2_FIXTURE_CAPTAIN_DOWN" not in text:
        raise FixtureRejected(
            "captain guard does not carry the #632 require/capability markers")
    return sha256(guard_source)


def require_safe_session_dir(session_dir, assets_dir=None):
    """Validate a short private session path; returns the resolved Path."""
    raw = str(session_dir)
    if "\0" in raw:
        raise FixtureRejected("session path contains NUL")
    candidate = Path(raw)
    if not candidate.is_absolute():
        raise FixtureRejected("session path must be absolute: " + raw)
    if ".." in Path(raw).parts:
        raise FixtureRejected("session path must not escape: " + raw)
    resolved = Path(os.path.normpath(str(candidate)))
    if len(str(resolved)) > SESSION_DIR_MAX_LEN:
        raise FixtureRejected(
            "session path too long for the Windows 260-char run tree "
            "(%d > %d): %s" % (len(str(resolved)), SESSION_DIR_MAX_LEN, raw))
    if resolved.exists():
        raise FixtureRejected(
            "session path must be a fresh private directory: " + str(resolved))
    if assets_dir is not None:
        assets = Path(os.path.normpath(str(Path(assets_dir).resolve())))
        if resolved == assets or assets in resolved.parents:
            raise FixtureRejected(
                "session path must be private, never inside the assets tree")
    return resolved


def validate_bootstrap(manifest, text):
    """Check staged bootstrap text against the manifest's production derivation.

    Requires the ``PIKMIN_RANDOMIZER`` header, the ``SESSION`` token, a
    matching ``FINGERPRINT``, and an ``ENEMY_P2`` line byte-equal to
    ``experimental.pikmin2_seed_bridge.bootstrap_for_manifest`` for this
    manifest. Any hand-written row changes that line and is rejected here;
    the error names it as a hand-written/stale bootstrap, never as a campaign.
    """
    from randomizer.seed import fingerprint
    from experimental.pikmin2_seed_bridge import bootstrap_for_manifest

    if not isinstance(manifest, dict) or "p2_layout" not in manifest:
        raise FixtureRejected("manifest has no p2_layout (generate with p2_enemies)")
    text = text or ""
    lines = text.splitlines()
    if not lines or not lines[0].startswith("PIKMIN_RANDOMIZER"):
        raise FixtureRejected("bootstrap is missing the PIKMIN_RANDOMIZER header")
    session_lines = [line for line in lines if line.startswith("SESSION ")]
    if len(session_lines) != 1 or len(session_lines[0].split()) != 2:
        raise FixtureRejected("bootstrap is missing the session handshake token")
    token = session_lines[0].split()[1]
    fingerprint_lines = [line for line in lines if line.startswith("FINGERPRINT ")]
    if len(fingerprint_lines) != 1:
        raise FixtureRejected("bootstrap is missing the manifest fingerprint")
    if fingerprint_lines[0].split()[1] != fingerprint(manifest):
        raise FixtureRejected("bootstrap fingerprint does not match the manifest")
    expected_enemy = bootstrap_for_manifest(manifest)
    if not expected_enemy:
        raise FixtureRejected("no production ENEMY_P2 derivation for this manifest")
    expected_enemy = expected_enemy.strip()
    if expected_enemy not in (line.strip() for line in lines):
        raise FixtureRejected(
            "bootstrap ENEMY_P2 is not the production derivation for this "
            "manifest (hand-written or stale rows refused)")
    return {"token": token, "enemy_line": expected_enemy}


def build_command(exe, bootstrap, extra_args=()):
    """Build the production campaign boot argv; refuses preview flags."""
    exe = Path(exe)
    if not exe.is_file():
        raise FixtureRejected("native executable not found: " + str(exe))
    bootstrap = Path(bootstrap)
    if not bootstrap.is_file():
        raise FixtureRejected("bootstrap not found: " + str(bootstrap))
    if len(str(bootstrap.resolve())) > BOOTSTRAP_PATH_MAX_LEN:
        raise FixtureRejected("bootstrap path too long for a reliable native boot")
    extra = require_no_preview(extra_args)
    return [str(exe.resolve()), "--randomizer-seed", str(bootstrap.resolve())] + extra


def check_executable(exe, expected_sha256=None):
    """Hash the executable; fail closed on a stale (mismatched) pin."""
    digest = sha256(exe)
    if expected_sha256 is not None and digest != expected_sha256:
        raise FixtureRejected(
            "stale executable: sha256 %s != expected %s" % (digest, expected_sha256))
    return digest


def check_content_root(content_root):
    """Require a prepared identity-keyed content root; return its receipt hash."""
    content_root = Path(content_root)
    prepared = content_root / "prepared.json"
    if not prepared.is_file():
        raise FixtureRejected(
            "stale content: no prepared.json in " + str(content_root))
    try:
        document = json.loads(prepared.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FixtureRejected("stale content: unreadable prepared.json") from error
    if not isinstance(document, dict) or not document.get("extracted"):
        raise FixtureRejected("stale content: prepared.json names no extraction")
    return sha256(prepared)


def parse_native_log(text, pass_markers=(), block_markers=()):
    """Pure native.log parser driven by a caller-supplied species contract.

    ``pass_markers``/``block_markers`` are regex strings naming the
    species-specific evidence for this run. Generic boot/handshake/guard/bound
    accounting is fixed; species meaning always comes from the caller, so this
    module never invents a gameplay claim.
    """
    from scripts import p2_campaign_smoke as smoke

    text = text or ""
    parsed = smoke.parse_native_log(text)
    handshake = bool(SESSION_HANDSHAKE_RE.search(text))
    preview_hint = "--experimental-pikmin2-room" in text
    pass_hits = [pattern for pattern in pass_markers if re.search(pattern, text)]
    block_hits = [pattern for pattern in block_markers if re.search(pattern, text)]
    nonnatural = [marker for marker in NONNATURAL_MARKERS if marker in text]
    return {
        "booted": parsed["booted"],
        "aborted": parsed["aborted"],
        "abort_markers": parsed["abort_markers"],
        "captain_down": parsed["captain_down"],
        "handshake": handshake,
        "preview_hint": preview_hint,
        "bound": parsed["bound"],
        "resolved": sorted(parsed["resolved"]),
        "species_counts": parsed["species_counts"],
        "setup_skips": parsed["setup_skips"],
        "missing_files": parsed["missing_files"],
        "pass_markers": list(pass_markers),
        "pass_hits": pass_hits,
        "block_markers": list(block_markers),
        "block_hits": block_hits,
        "nonnatural_markers": nonnatural,
    }


def evaluate(parsed, expected_targets=(), require_handshake=True):
    """Combine a parsed log with the expected bound targets.

    ``expected_targets`` are the manifest binding target uids (as strings or
    ints) whose content was staged into the run. A target counts as bound when
    any generic bind/ready marker names its uid; resolution/placement evidence
    alone is not a bind. ``ok`` is False on an abort, a missing boot, a
    missing session handshake, a captain-down marker, a block-marker hit, or
    any expected target with no bind marker. The outcome vocabulary is fixed:
    BLOCKED (captain guard fired), PASS, or FAIL. Partial boot is not a pass.
    """
    reasons = []
    if not parsed.get("booted"):
        reasons.append("world never rendered")
    if parsed.get("aborted"):
        reasons.append("abort markers: " + "; ".join(parsed["abort_markers"][:3]))
    if require_handshake and not parsed.get("handshake"):
        reasons.append("missing enabled-session handshake (preview-mode logs never emit it)")
    if parsed.get("preview_hint"):
        reasons.append("preview-mode hint in log")
    if parsed.get("captain_down"):
        reasons.append("captain guard fired")
    if parsed.get("block_hits"):
        reasons.append("block markers: " + "; ".join(parsed["block_hits"][:5]))
    bound = parsed.get("bound", {})
    missing = [str(target) for target in expected_targets
               if int(target) not in bound]
    if missing:
        reasons.append("targets without a bind marker: " + ", ".join(missing[:8]))
    if parsed.get("pass_markers") and not parsed.get("pass_hits"):
        reasons.append("no species pass marker observed")
    if parsed.get("captain_down"):
        outcome = "BLOCKED"
    elif not reasons:
        outcome = "PASS"
    else:
        outcome = "FAIL"
    return {"outcome": outcome, "reasons": reasons, "missing_binds": missing}


def stage_campaign(seed_name, session_dir, content_root, assets_dir, exe=None,
                   species=None, placement=None, out=None,
                   expected_exe_sha256=None):
    """Generate, stage and record a real enabled campaign; returns the manifest.

    All inputs are read-only dependencies: ``randomizer.seed.generate``,
    ``randomizer.session.Session`` / ``randomizer.runner.NativeRun``,
    ``scripts.p2_prepare_content.actor_bindings_for_manifest`` and
    ``experimental.pikmin2_family_install.install_layout``. Nothing here edits
    generate/content/session/supervision tools, native sources, the shared AP
    installation or the user's game.
    """
    from randomizer.seed import generate
    from randomizer.session import Session
    from randomizer.runner import NativeRun
    from scripts.p2_prepare_content import actor_bindings_for_manifest
    from experimental.pikmin2_family_install import install_layout

    if not seed_name or not isinstance(seed_name, str):
        raise FixtureRejected("seed name must be a nonempty string")
    session_dir = require_safe_session_dir(session_dir, assets_dir)
    content_root = Path(content_root).resolve()
    assets_dir = Path(assets_dir).resolve()
    if not (assets_dir / "dataDir" / "stages").is_dir():
        raise FixtureRejected("--assets must contain dataDir/stages: " + str(assets_dir))
    content_prepared_sha256 = check_content_root(content_root)
    guard_sha256 = require_guard()
    exe_sha256 = check_executable(Path(exe).resolve(), expected_exe_sha256) if exe else None

    manifest = generate(str(seed_name), p2_enemies=True,
                        p2_species=species, p2_placement=placement)
    bindings = manifest["p2_layout"]["bindings"]
    actors = actor_bindings_for_manifest(manifest)

    session_dir.mkdir(parents=True, exist_ok=False)
    session = Session(manifest, session_dir)
    (session_dir / "seed-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run = NativeRun(session)
    bootstrap_text = run.bootstrap.read_text(encoding="ascii")
    bootstrap_info = validate_bootstrap(manifest, bootstrap_text)
    receipt = install_layout(
        run.directory, manifest["p2_layout"], content_root,
        actor_bindings={str(target): int(generator) for target, generator in actors.items()},
        retail_assets=assets_dir, cache_dir=session.directory / "p2-content-cache")

    seed_manifest_sha256 = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()
    try:
        root_head = _git_head(ROOT)
    except FixtureRejected:
        root_head = "unknown"
    record = {
        "schema": SCHEMA,
        "seed": str(seed_name),
        "species": None if species is None else (species if isinstance(species, str) else sorted(species)),
        "session_dir": str(session_dir),
        "run_dir": str(run.directory),
        "run_token": bootstrap_info["token"],
        "bootstrap": str(run.bootstrap.resolve()),
        "bootstrap_sha256": sha256(run.bootstrap),
        "seed_manifest_sha256": seed_manifest_sha256,
        "bindings": [{"target": str(binding["target"]), "source_id": binding["source_id"],
                      "enum_name": binding["enum_name"]} for binding in bindings],
        "actor_bindings": {str(target): int(generator) for target, generator in actors.items()},
        "binding_receipt": {"bindings": len(receipt.get("bindings", [])),
                            "cached": bool(receipt.get("cached", False))},
        "root_head": root_head,
        "native": {"present": False,
                   "note": "native worktree absent on this lane; read-only through configured integration paths"},
        "exe": str(Path(exe).resolve()) if exe else None,
        "exe_sha256": exe_sha256,
        "assets": str(assets_dir),
        "content_root": str(content_root),
        "content_prepared_sha256": content_prepared_sha256,
        "window": {WINDOW_ENV: WINDOW_GEOMETRY, "centred": True},
        "guard_source": str(GUARD_SOURCE),
        "guard_source_sha256": guard_sha256,
        "command": [str(Path(exe).resolve()), "--randomizer-seed",
                    str(run.bootstrap.resolve())] if exe else None,
        "note": ("infrastructure, not gameplay proof: staged an enabled "
                 "campaign without preview flags"),
    }
    manifest_path = Path(out).resolve() if out is not None else (session_dir / "fixture-manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    record["manifest_path"] = str(manifest_path)
    return record


class _ReopenedRun:
    """Keepalive for an already-staged run dir without creating a new one."""

    def __init__(self, session, token, run_dir):
        self.session = session
        self.token = token
        self.directory = Path(run_dir)
        self.handshaken = False

    def write_state(self, ready):
        from randomizer.session import atomic_write
        atomic_write(self.directory / "state.txt",
                     self.session.native_state(self.token, ready))

    def poll(self):
        hello = self.directory / "hello.txt"
        if not self.handshaken and hello.exists():
            fields = hello.read_text(encoding="ascii").split()
            if fields != ["PIKMIN_HELLO", str(self.session.manifest["schema"]), self.token,
                          self.session.fingerprint, *self.session.manifest["capabilities"], "END"]:
                raise ValueError("native adapter capability or session handshake mismatch")
            self.handshaken = True
        if self.handshaken:
            self.session.recover_emperor(self.directory)
        journal = self.directory / "checks.txt"
        if self.handshaken and journal.exists():
            data = journal.read_bytes()
            lines = data[:data.rfind(b"\n") + 1].splitlines()
            for line in lines:
                if not line.isdigit() or not 0 <= int(line) < len(self.session.names):
                    raise ValueError("invalid native check journal")
                self.session.collect(self.session.names[int(line)])


def supervise(command, session, token, run_dir, seconds):
    """Bounded supervised launch with session keepalive; returns the result.

    The command must already have passed ``build_command`` (no preview flags).
    ``seconds`` is clamped to ``1..MAX_SECONDS``; anything else is an
    unbounded/degenerate launch and is refused before spawning.
    """
    try:
        budget = float(seconds)
    except (TypeError, ValueError) as error:
        raise FixtureRejected("invalid launch budget") from error
    if not 1.0 <= budget <= MAX_SECONDS:
        raise FixtureRejected(
            "launch budget must be 1..%.0f seconds (unbounded launch refused)" % MAX_SECONDS)
    command = require_no_preview(command)
    run_dir = Path(run_dir)
    log_path = run_dir / "native.log"
    if not run_dir.is_dir():
        raise FixtureRejected("run dir missing: " + str(run_dir))

    reopened = _ReopenedRun(session, token, run_dir)
    env = dict(os.environ)
    env[WINDOW_ENV] = WINDOW_GEOMETRY
    env["SDL_AUDIODRIVER"] = "dummy"
    env["PYTHONUTF8"] = "1"
    mingw = Path("C:/msys64/mingw64/bin")
    if mingw.is_dir():
        env["PATH"] = str(mingw) + os.pathsep + env.get("PATH", "")
    startup = None
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0

    stop = threading.Event()

    def keepalive():
        while not stop.is_set():
            try:
                reopened.poll()
                reopened.write_state(reopened.handshaken)
            except Exception:
                return
            time.sleep(0.1)

    timed_out = False
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command, cwd=str(run_dir), env=env, stdout=log,
            stderr=subprocess.STDOUT, startupinfo=startup)
        thread = threading.Thread(target=keepalive, daemon=True)
        thread.start()
        deadline = time.monotonic() + budget
        try:
            while time.monotonic() < deadline and process.poll() is None:
                time.sleep(0.2)
            timed_out = process.poll() is None
            if timed_out:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        finally:
            stop.set()
            thread.join(timeout=5)
    return {"exit_code": process.returncode, "timed_out": timed_out,
            "log": str(log_path), "log_sha256": sha256(log_path)}


def launch_campaign(manifest_path, exe, seconds, pass_markers=(), block_markers=(),
                    report_out=None, expected_exe_sha256=None):
    """Launch a staged campaign, parse it against the species contract, report."""
    from randomizer.session import Session

    manifest_path = Path(manifest_path).resolve()
    try:
        record = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FixtureRejected("unreadable fixture manifest: " + str(error))
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise FixtureRejected("unsupported fixture manifest: " + str(manifest_path))
    session_dir = Path(record["session_dir"])
    seed_path = session_dir / "seed-manifest.json"
    if not seed_path.is_file():
        raise FixtureRejected("staged seed manifest is gone; restage before launching")
    try:
        manifest = json.loads(seed_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FixtureRejected("unreadable staged seed manifest: " + str(error))
    exe = Path(exe).resolve(strict=True)
    check_executable(exe, expected_exe_sha256 or record.get("exe_sha256"))
    if record.get("exe") and str(exe) != record["exe"]:
        raise FixtureRejected("stale executable: staged %s, asked %s" % (record["exe"], exe))
    require_guard()
    check_content_root(record["content_root"])

    run_dir = Path(record["run_dir"])
    bootstrap = Path(record["bootstrap"])
    if not bootstrap.is_file():
        raise FixtureRejected("staged bootstrap is gone: " + str(bootstrap))
    validate_bootstrap(manifest, bootstrap.read_text(encoding="ascii"))
    command = build_command(exe, bootstrap)

    session = Session(manifest, session_dir)
    result = supervise(command, session, record["run_token"], run_dir, seconds)
    text = Path(result["log"]).read_text(encoding="utf-8", errors="replace")
    parsed = parse_native_log(text, pass_markers, block_markers)
    verdict = evaluate(parsed, [binding["target"] for binding in record["bindings"]])
    if parsed["captain_down"]:
        exit_code = GUARD_EXIT_CODE
    elif verdict["outcome"] == "PASS":
        exit_code = 0
    else:
        exit_code = 1
    report = {
        "schema": SCHEMA,
        "manifest": str(manifest_path),
        "seed": record["seed"],
        "exe": str(exe),
        "exe_sha256": sha256(exe),
        "run_dir": str(run_dir),
        "native_log": result["log"],
        "native_log_sha256": result["log_sha256"],
        "seconds": float(seconds),
        "timed_out": result["timed_out"],
        "process_exit": result["exit_code"],
        "outcome": verdict["outcome"],
        "reasons": verdict["reasons"],
        "missing_binds": verdict["missing_binds"],
        "booted": parsed["booted"],
        "aborted": parsed["aborted"],
        "handshake": parsed["handshake"],
        "species_counts": parsed["species_counts"],
        "pass_hits": parsed["pass_hits"],
        "block_hits": parsed["block_hits"],
        "setup_skips": parsed["setup_skips"],
        "window": record["window"],
        "guard_source_sha256": record["guard_source_sha256"],
        "captain_safety": {
            "policy": "guarded",
            "guard_source": record["guard_source"],
            "guard_source_sha256": record["guard_source_sha256"],
            "captain_down": parsed["captain_down"],
            "note": ("#632: the native fixture must call "
                     "p2_fixture_require_captain before pause/movie returns; "
                     "a guard trip exits 86 and blocks the run."),
        },
    }
    destination = Path(report_out).resolve() if report_out is not None else (run_dir / "fixture-report.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    report["report_path"] = str(destination)
    report["exit_code"] = exit_code
    return report


def _species_list(value):
    if value is None or value == "admitted":
        return None
    if value == "playable":
        return "playable"
    try:
        ids = [int(piece) for piece in str(value).split(",") if piece.strip()]
    except ValueError:
        raise FixtureRejected("--species must be 'playable', 'admitted' or comma-separated ints")
    if not ids:
        raise FixtureRejected("--species must be nonempty")
    return ids


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    stage = sub.add_parser("stage", help="generate + stage a real enabled campaign")
    stage.add_argument("--seed", required=True)
    stage.add_argument("--session-dir", type=Path, required=True)
    stage.add_argument("--content-root", type=Path, required=True)
    stage.add_argument("--assets", type=Path, required=True)
    stage.add_argument("--exe", type=Path, default=None)
    stage.add_argument("--species", default="admitted")
    stage.add_argument("--out", type=Path, default=None)
    stage.add_argument("--expected-exe-sha256", default=None)

    launch = sub.add_parser("launch", help="bounded launch of a staged campaign")
    launch.add_argument("--manifest", type=Path, required=True)
    launch.add_argument("--exe", type=Path, required=True)
    launch.add_argument("--seconds", type=float, default=150.0)
    launch.add_argument("--pass-marker", action="append", default=[],
                        help="species pass regex (repeatable)")
    launch.add_argument("--block-marker", action="append", default=[],
                        help="species block regex (repeatable)")
    launch.add_argument("--report-out", type=Path, default=None)
    launch.add_argument("--expected-exe-sha256", default=None)

    validate = sub.add_parser("validate",
                              help="validate a manifest + bootstrap without booting")
    validate.add_argument("--manifest", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            record = stage_campaign(
                args.seed, args.session_dir, args.content_root, args.assets,
                exe=args.exe, species=_species_list(args.species), out=args.out,
                expected_exe_sha256=args.expected_exe_sha256)
            print(json.dumps({"manifest": record["manifest_path"],
                              "bindings": len(record["bindings"]),
                              "run_dir": record["run_dir"]}, indent=2))
            return 0
        if args.command == "launch":
            report = launch_campaign(
                args.manifest, args.exe, args.seconds,
                pass_markers=args.pass_marker, block_markers=args.block_marker,
                report_out=args.report_out,
                expected_exe_sha256=args.expected_exe_sha256)
            print(json.dumps({key: report[key] for key in
                              ("outcome", "reasons", "booted", "handshake",
                               "species_counts", "missing_binds")}, indent=2))
            return report["exit_code"]
        record = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        try:
            bootstrap = Path(record["bootstrap"]).read_text(encoding="ascii")
            seed_path = Path(record["session_dir"]) / "seed-manifest.json"
            manifest = json.loads(seed_path.read_text(encoding="utf-8"))
        except (OSError, KeyError, ValueError) as error:
            raise FixtureRejected("staged manifest/bootstrap/seed is gone: " + str(error))
        validate_bootstrap(manifest, bootstrap)
        require_guard()
        check_content_root(record["content_root"])
        print(json.dumps({"manifest": str(args.manifest), "valid": True,
                          "bindings": len(record["bindings"])}))
        return 0
    except FixtureRejected as error:
        parser.exit(2, "fixture rejected: " + str(error) + "\n")


if __name__ == "__main__":
    sys.exit(main())
