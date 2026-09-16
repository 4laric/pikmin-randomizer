"""Sokkuri79 exactly-once ordinary Onion receipt (#578, parent #569).

Follow-on of #495 (natural haul proven, receipt missing): the preview room
runs without a randomizer session by design, so no receipt could exist yet.
This module stages a Pod-enabled Sokkuri arena, boots the fixture WITH a
real session bootstrap, and validates that a naturally hauled corpse drives
the real ordinary endpoint (GoalItem::suckMe ->
pc_randomizer_p2_corpse_delivered) to ``onion:p2:79`` new=1, then new=0 for
the duplicate across a process restart sharing the session ledger.

Transport PASS needs BOTH the receipt line AND natural-carry markers; a
receipt alone is interface-only (same honesty rule as #495). No Transport,
kill or credit is ever injected: the fixture contains no suckMe call, no
health/state writes and no forget/re-entry. Gate 6 stays UNTESTED.
"""

import argparse
import functools
import json
import os
import re
import threading
from pathlib import Path

SOKKURI_GEN = 346005
SOURCE_ID = 79
RECEIPT_RE = re.compile(
    r"P2_ORDINARY_P2_RECEIPT seed=(\S+) id=onion:p2:79:(\d+) generator=(\d+) new=([01])")
CARRY_RE = re.compile(
    r"P2_SOKKURI79_CARRY tick=(\d+) moved=([\d.]+) goal_dist=([\d.\-]+) state=(\d+)")
READY_RE = re.compile(
    r"P2_SOKKURI79_READY squad=(\d+) sokkuri_gen=346005 reg=1 session=1")
DELIVERED_RE = re.compile(
    r"P2_SOKKURI79_DELIVERED_TO_GOAL tick=(\d+) moved=([\d.]+)")
INJECTED_RES = (
    "P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
    "P2_SOKKURI79_FALLBACK", "direct transport assigned",
)

# Retail checkout root (read-only). Overridable for tests.
RETAIL_ROOT = Path(os.environ.get(
    "PIKMIN_P2_RETAIL_ROOT",
    r"C:/Users/alari/pikmin-randomizer/native/pikmin2-research"))


def parse_receipts(text):
    """Return every onion:p2:79 receipt marker as a dict."""
    return [dict(seed=m.group(1), stage=int(m.group(2)),
                 generator=int(m.group(3)), new=int(m.group(4)))
            for m in RECEIPT_RE.finditer(text)]


def parse_carries(text):
    return [dict(tick=int(m.group(1)), moved=float(m.group(2)),
                 goal_dist=float(m.group(3)), state=int(m.group(4)))
            for m in CARRY_RE.finditer(text)]


def check_receipt_once(text, expect_new):
    """Exactly one onion:p2:79 line with the expected new= flag."""
    receipts = parse_receipts(text)
    if len(receipts) != 1:
        return dict(passed=False,
                    reason="expected 1 receipt line, found %d" % len(receipts),
                    receipts=receipts)
    if receipts[0]["new"] != expect_new:
        return dict(passed=False,
                    reason="expected new=%d, got new=%d" % (
                        expect_new, receipts[0]["new"]),
                    receipts=receipts)
    if receipts[0]["generator"] != SOKKURI_GEN:
        return dict(passed=False, reason="receipt generator != 346005",
                    receipts=receipts)
    return dict(passed=True, reason="onion:p2:79 stage=%d new=%d" % (
        receipts[0]["stage"], receipts[0]["new"]), receipts=receipts)


def check_natural_carry(text, min_moved=100.0):
    """Natural-carry markers: real haul movement, goal delivery, no injection."""
    carries = parse_carries(text)
    best = max([c["moved"] for c in carries], default=0.0)
    delivered = DELIVERED_RE.search(text)
    injected = [token for token in INJECTED_RES if token in text]
    if injected:
        return dict(passed=False, reason="injection markers present",
                    best=best)
    if not carries or best < min_moved:
        return dict(passed=False,
                    reason="no natural haul movement (best %.1f)" % best,
                    best=best)
    if not delivered:
        return dict(passed=False, reason="no goal-delivery marker", best=best)
    return dict(passed=True,
                reason="hauled %.1f to Pod goal" % best, best=best)


def check_ordinary_corpse_source(retail_root=None):
    # Unlike the Long Legs family (EB_LeaveCarcass disabled: no carcass ever),
    # Sokkuri keeps the ordinary carcass path, so a hauled corpse reaching an
    # Onion is source-backed behavior, not a proxy credit.
    root = Path(retail_root) if retail_root else RETAIL_ROOT
    path = root / "src/plugProjectNishimuraU/Sokkuri.cpp"
    try:
        content = path.read_text(errors="replace")
    except OSError:
        return dict(passed=False, detail="missing: %s" % path)
    passed = "startCarcassMotion" in content
    return dict(passed=passed,
                detail="startCarcassMotion present" if passed
                else "MARKER ABSENT")


def validate(text, expect_new, retail_root=None, code=0):
    """Validate one receipt-run native log."""
    receipt = check_receipt_once(text, expect_new)
    carry = check_natural_carry(text)
    nocarcass = check_ordinary_corpse_source(retail_root)
    ready = READY_RE.search(text)
    squad = int(ready.group(1)) if ready else 0
    binds = bool(re.search(
        r"P2_SOKKURI_DELIVERY_BIND generator=346005 source_id=79", text))
    window = bool(re.search(
        r"Experimental preview window set to 960x540 windowed and centered", text))
    session = bool(re.search(r"session=1", text)) if ready else False
    no_inject = not any(token in text for token in INJECTED_RES)
    no_extinction = not re.search(r"Extinction", text, re.IGNORECASE)
    completion = "PASS P2_SOKKURI79_RECEIPT_RUN" in text
    checks = dict(
        receipt=receipt["passed"],
        natural_carry=carry["passed"],
        no_carcass_source=nocarcass["passed"],
        bound=binds,
        window=window,
        live_squad=squad >= 1,
        session_ready=session,
        no_inject=no_inject,
        no_extinction=no_extinction,
        completion=completion and code == 0,
    )
    passed = all(checks.values())
    return dict(passed=passed, checks=checks, receipt=receipt, carry=carry,
                nocarcass=nocarcass, squad=squad,
                natural_vs_injected=dict(
                    receipt_natural=receipt["passed"] and carry["passed"],
                    inject_present=not no_inject))


def prepare(assets, imported, output):
    """Stage a Pod-enabled Sokkuri arena (NOT cargo-free).

    Same Sokkuri-only ground arena as #495, then the lane-19 Pod package is
    staged through the maintained cargo path so carriers have a real Red
    container goal. The Pod anchor stays present-but-ordinary: no carry or
    receipt is claimed here.
    """
    from experimental.pikmin2_sokkuri_natural_runtime import sokkuri_only_cfg
    from experimental.pikmin2_batch2_core import prepare as _prepare
    from experimental.pikmin2_batch2_core import install, verify_install
    from experimental.pikmin2_sokkuri_behavior import normalize_pose_names
    from experimental.pikmin2_mamuta_rules import (
        find_pod_package, load_pod_package, stage_cargo)
    cfg = sokkuri_only_cfg()
    run = _prepare(cfg, Path(assets), Path(imported), Path(output),
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    normalize_pose_names(run)
    package = find_pod_package([
        Path(os.environ.get("PIKMIN_P2_POD_PACKAGE", "")),
        Path(__file__).resolve().parents[2] / "dsw" / "l19-out" / "pod",
    ])
    stage_cargo(run, Path(assets), load_pod_package(package))
    return run


def instrument(source, app=None):
    """Splice the reserved receipt fixture app into preview_p2_room.cpp."""
    if app is None:
        raise ValueError("receipt fixture source text required")
    if "P2_SOKKURI79_READY" in source:
        raise ValueError("Room fixture already carries the receipt app")
    start = source.index("class RoomApp : public PlugPikiApp {")
    end = source.index("int main(", start)
    includes = ('#include <cstring>\n#include "Generator.h"\n#include "pc_p2_sokkuri.h"\n'
                '#include "pc_p2_preview.h"\n#include "pc_randomizer.h"\n#include "ItemMgr.h"\n')
    return includes + source[:start] + app + source[end:]


def build(native, build_dir, output, head, fixture_cpp, resume=False):
    """Build the private instrumented receipt fixture (never a run)."""
    from scripts import build_pikmin2_fixture as builder
    from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
    native = Path(native).resolve()
    build_dir = Path(build_dir).resolve()
    output = Path(output).resolve()
    app = Path(fixture_cpp).read_text()
    room = output / "room.cpp"
    source = instrument((native / "tools/preview_p2_room.cpp").read_text(), app)
    if resume:
        if (output / "instrumentation.json").exists() or room.read_text() != source:
            raise ValueError("Cannot resume completed or changed fixture")
        record = json.loads((output / "baseline/provenance.json").read_text())
        if record.get("status") != "built" or record.get("expected_native_head") != head \
                or builder.git_state(native) != record["observed_source"]:
            raise ValueError("Baseline no longer matches source")
        for key in ("inputs", "fixture_inputs", "configuration_inputs"):
            builder.check_snapshot(record[key])
    else:
        output.mkdir(parents=True, exist_ok=False)
        room.write_text(source)
        record = builder.build_fixture(build_dir, native, room, output / "baseline", head)
    compile_cmd = list(record["commands"][-2])
    compile_cmd[builder.option_index(compile_cmd, "-o")] = str(output / "room.obj")
    compile_cmd[builder.option_index(compile_cmd, "-MF")] = str(output / "room.d")
    link = list(record["commands"][-1])
    targets = [i for i, a in enumerate(link) if a.endswith("\\fixture.obj") or a.endswith("/fixture.obj")]
    if len(targets) != 1:
        raise ValueError("Expected one private room object")
    link[targets[0]] = str(output / "room.obj")
    link[builder.option_index(link, "-o")] = str(output / "fixture.exe")
    link = [("-Wl,--out-implib," + str(output / "fixture.dll.a")) if a.startswith("-Wl,--out-implib,") else a for a in link]
    tutorial = native / "src/plugPikiColin/newPikiGame.cpp"
    tutorial_private = output / "tutorial.cpp"
    tutorial_private.write_text(instrument_tutorial(tutorial.read_text()))
    tutorial_compile = [str(tutorial_private) if a == str(room) else a for a in compile_cmd]
    tutorial_compile[builder.option_index(tutorial_compile, "-o")] = str(output / "tutorial.obj")
    tutorial_compile[builder.option_index(tutorial_compile, "-MF")] = str(output / "tutorial.d")
    targets = [i for i, a in enumerate(link) if a.endswith("libpikmin_legacy.a")]
    if len(targets) != 1:
        raise ValueError("Expected one private legacy archive")
    link.insert(targets[0], str(output / "tutorial.obj"))
    env = dict(os.environ, PATH=r"C:\msys64\mingw64\bin;" + os.environ.get("PATH", ""))
    audit = dict(original_fixture=builder.snapshot([native / "tools/preview_p2_room.cpp", tutorial]),
                 instrumented=builder.snapshot([room, tutorial_private]),
                 commands=[compile_cmd, tutorial_compile, link], freshness_checks=[])
    for name, command in [("room-compile", compile_cmd), ("tutorial-compile", tutorial_compile), ("room-link", link)]:
        code, text = builder.run(command, build_dir, env)
        (output / (name + ".log")).write_text(text)
        if code:
            raise RuntimeError(name + " failed")
    builder.require_fresh(Path(record["toolchain"]["ninja"]["path"]), build_dir, audit["freshness_checks"])
    builder.check_snapshot(record["inputs"])
    builder.check_snapshot(record["fixture_inputs"])
    builder.check_snapshot(record["configuration_inputs"])
    if builder.git_state(native) != record["observed_source"]:
        raise RuntimeError("Native changed during private replacement")
    audit["artifacts"] = builder.snapshot([output / "fixture.exe", output / "room.obj"])
    audit["status"] = "built"
    (output / "instrumentation.json").write_text(json.dumps(audit, indent=2) + "\n")
    record = json.loads((output / "baseline/provenance.json").read_text())
    record.setdefault("artifacts", {})[str(output / "fixture.exe")] = dict(
        audit["artifacts"][str(output / "fixture.exe")], role="linked-run-executable")
    (output / "baseline/provenance.json").write_text(json.dumps(record, indent=2) + "\n")


def run_once(session, assets, imported, output, exe, seconds, label):
    """One session-enabled receipt run: fresh arena + bootstrap in one dir."""
    from randomizer.runner import NativeRun
    from randomizer.session import atomic_write
    from experimental.pikmin2_animation_profile import capture_command
    native_run = NativeRun(session)
    arena = prepare(Path(assets), Path(imported), Path(output))
    (arena / "bootstrap.txt").write_text(
        (native_run.directory / "bootstrap.txt").read_text())
    done = threading.Event()

    def refresh():
        while not done.is_set():
            atomic_write(arena / "state.txt",
                         session.native_state(native_run.token, True))
            done.wait(0.1)

    threading.Thread(target=refresh, daemon=True).start()
    try:
        meta = capture_command(
            [str(Path(exe).resolve()), "--experimental-pikmin2-room",
             "--randomizer-seed", str((arena / "bootstrap.txt").resolve())],
            arena, arena / "capture", seconds)
    finally:
        done.set()
    text = (arena / "capture" / "native.log").read_text(errors="replace")
    print("[%s] exit=%s timed_out=%s dir=%s" % (
        label, meta["exit_code"], meta["timed_out"], arena))
    return arena, meta, text


def run_session(session_dir, seed_name, assets, imported, output, exe,
                seconds=600):
    """Two receipt runs sharing one session ledger; run1 new=1, run2 new=0."""
    import uuid
    from randomizer.seed import generate
    from randomizer.session import Session
    output = Path(output)
    session_dir = Path(session_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest = generate(seed_name, "ap", expanded=True, all_areas=True,
                        collection_checks=True, starting_flarlic=10)
    session = Session(manifest, session_dir / ("session-" + uuid.uuid4().hex[:8]))
    results = []
    for index, expect in ((1, 1), (2, 0)):
        arena, meta, text = run_once(
            session, assets, imported, output / ("run%d" % index),
            exe, seconds, "run%d" % index)
        result = validate(text, expect, code=meta["exit_code"])
        result["capture"] = {k: meta[k] for k in ("executable_sha256",
                                                  "elapsed_seconds",
                                                  "exit_code", "timed_out")}
        result["arena"] = str(arena)
        (arena / "sokkuri79-receipt-validation.json").write_text(
            json.dumps(result, indent=2) + "\n")
        results.append(result)
        print("run%d passed=%s" % (index, result["passed"]))
    return session, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="native.log to validate")
    parser.add_argument("--expect-new", type=int, default=1)
    args = parser.parse_args()
    result = validate(args.log.read_text(errors="replace"), args.expect_new)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)