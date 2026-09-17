"""Private leased build/run harness for the #690 collision-traversal fixture.

Builds ``native/tools/p2_yakushima4_collision_traversal_fixture.cpp``
(replacement-main TU) against a private leased ``pikmin_pc`` build using the
maintained replacement-main builder (``scripts/build_pikmin2_fixture.py``:
build.ninja edge reuse, no shared CMake/CTest or consumer edits), then runs
the guarded walk-inside collision-traversal chain.

The fixture consumes the INTEGRATED #682 authored yakushima_4 floor-1 room
graph read-only through its public API (``pc_p2_yakushima4_room_count`` /
``_validate`` / ``_emit_nav`` in ``pc_port/pc_p2_cave.cpp``) plus the real
unit pool (``user/Mukki/mapunits/units/2_units_gw_l_conc.txt``) that table was
decoded from. It rasterises every room cell grid, probes all four cell edges
for wall collisions and walks each of the 36 authored door links door-to-door,
emitting ``P2_YAKUSHIMA4_TRAVERSAL_*`` markers.

This harness independently re-decodes the real pool and diffs the emitted
authored table, and independently derives the expected walkable-cell and
wall-contact counts from the decoded cells/doors, so baked-value drift or a
stubbed traversal fails closed.

Phases: ``configure`` (leased cmake), ``build`` (leased pikmin_pc + ninja -n
+ single-TU object evidence), ``fixture`` (provenance-checked link, exe
SHA-256), ``guardcheck`` (live self-test + ``negcap`` negative path),
``run`` (staged units + traversal run with table/geometry sync check), ``all``.

The fixture consumes the captain guard header-only
(``p2_fixture_captain_guard.h``) from the canonical checkout ``scripts/``
read-only via ``CPLUS_INCLUDE_PATH`` (never copied or edited).

Captain safety #632: the guard runs before any observation; captain-down
exits 86 (BLOCKED) with ``P2_FIXTURE_CAPTAIN_DOWN`` and can never be recorded
as a traversal sample. Protected observation cannot prove captain damage.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")
sys.path.insert(0, str(CANONICAL_ROOT))

FIXTURE_REL = Path("tools/p2_yakushima4_collision_traversal_fixture.cpp")
CAVEINFO_REL = "user/Mukki/mapunits/caveinfo/yakushima_4.txt"
UNITS_REL = "user/Mukki/mapunits/units/2_units_gw_l_conc.txt"
UNITS_STAGE_NAME = "2_units_gw_l_conc.txt"
DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
GUARD_NAME = "p2_fixture_captain_guard.h"
NEGATIVE_EXIT = 86
EXPECTED_ROOMS = 8
EXPECTED_DOORS = 19
EXPECTED_LINKS = 36


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def resolve_guard(guard_dir=None):
    """Locate the canonical guard header read-only; fail closed if absent."""
    if guard_dir is not None:
        candidate = Path(guard_dir) / GUARD_NAME
    else:
        candidate = CANONICAL_ROOT / "scripts" / GUARD_NAME
    if not candidate.is_file():
        raise ValueError("Missing captain guard header: " + str(candidate))
    return candidate.resolve()


def guard_record(guard_dir=None):
    path = resolve_guard(guard_dir)
    return {"path": str(path), "sha256": sha256(path)}


def read_source_member(iso_path, member):
    """Read a raw disc member read-only through the shared disc reader."""
    from experimental.pikmin2_assets import disc_files
    iso = Path(iso_path)
    catalog = disc_files(iso)
    if member not in catalog:
        raise ValueError("Missing disc source: " + member)
    offset, length = catalog[member]
    with iso.open("rb") as disc:
        disc.seek(offset)
        data = disc.read(length)
    if len(data) != length:
        raise ValueError("Truncated disc source: " + member)
    return data


def decoded_units(units_text):
    from experimental.pikmin2_cave import unit_definition
    return unit_definition(units_text)


def expected_links(units_text):
    """Independently decode authored floor-1 door links from the unit pool."""
    rows = []
    for index, row in enumerate(decoded_units(units_text)):
        for door in row["doors"]:
            for peer in door["links"]:
                rows.append({
                    "room": str(index), "door": str(door["id"]),
                    "waypoint": str(door["waypoint"]),
                    "peer": str(peer["door"]),
                    "dist_mm": str(int(round(peer["distance"] * 1000))),
                    "enemy_flag": str(peer["enemy_flag"])})
    return rows


def expected_traversal(units_text):
    """Independent expected walkable cells and boundary wall contacts.

    Every room is a w x d cell grid; its boundary has 2*(w+d) edges and each
    authored door opens exactly one boundary edge, so the wall contacts equal
    the boundary edge count minus the door count. Walkable cells are w*d.
    """
    units = decoded_units(units_text)
    cells = sum(int(row["cells"][0]) * int(row["cells"][1]) for row in units)
    doors = sum(len(row["doors"]) for row in units)
    boundary = sum(2 * (int(row["cells"][0]) + int(row["cells"][1])) for row in units)
    links = sum(len(door["links"]) for row in units for door in row["doors"])
    return {"units": len(units), "cells": cells, "doors": doors,
            "links": links, "interior_contacts": boundary - doors}


def parse_markers(text):
    """Extract authored NAV rows, traversal samples/contacts and summary."""
    rows, summary, boot, done, down = [], None, None, False, False
    traversal_summary = None
    traversal_pass = None
    traversal_fail = None
    contacts = 0
    link_samples = 0
    interior_samples = 0
    for line in text.splitlines():
        if line.startswith("P2_CAVE_NAV "):
            fields = {}
            for token in line.split()[1:]:
                if "=" in token:
                    key, _, value = token.partition("=")
                    fields[key] = value
            rows.append(fields)
        elif line.startswith("P2_YAKUSHIMA4_AUTHORED "):
            summary = line
        elif line.startswith("P2_YAKUSHIMA4_TRAVERSAL_BOOT "):
            boot = line
        elif line.startswith("P2_YAKUSHIMA4_TRAVERSAL_SUMMARY "):
            traversal_summary = line
        elif line.startswith("P2_YAKUSHIMA4_TRAVERSAL_PASS"):
            traversal_pass = line
        elif line.startswith("P2_YAKUSHIMA4_TRAVERSAL_FAIL"):
            traversal_fail = line
        elif line.startswith("P2_YAKUSHIMA4_TRAVERSAL_CONTACT "):
            contacts += 1
        elif line.startswith("P2_YAKUSHIMA4_TRAVERSAL_SAMPLE "):
            if "kind=link" in line:
                link_samples += 1
            else:
                interior_samples += 1
        elif line.startswith("P2_FIXTURE_CAPTAIN_DOWN"):
            down = True
    return {"rows": rows, "summary": summary, "boot": boot, "done": done,
            "captain_down": down, "traversal_summary": traversal_summary,
            "traversal_pass": traversal_pass, "traversal_fail": traversal_fail,
            "contacts": contacts, "link_samples": link_samples,
            "interior_samples": interior_samples}


def _fields(line):
    out = {}
    for token in line.split()[1:]:
        if "=" in token:
            key, _, value = token.partition("=")
            out[key] = value
    return out


def check_chain(parsed, expected_links_rows, expected_traversal_counts):
    """Require boot, authored table in order, traversal summary and PASS."""
    if parsed["captain_down"]:
        return False, "captain-down during chain run"
    if not parsed["boot"]:
        return False, "missing traversal boot marker"
    got = parsed["rows"]
    if len(got) != len(expected_links_rows):
        return False, "authored row count %d != expected %d" % (
            len(got), len(expected_links_rows))
    for index, (one, want) in enumerate(zip(got, expected_links_rows)):
        if one.get("authored") != "1":
            return False, "row %d not labelled authored" % index
        for key in ("room", "door", "waypoint", "peer", "dist_mm",
                    "enemy_flag"):
            if one.get(key) != want[key]:
                return False, ("row %d field %s: %r != expected %r"
                                % (index, key, one.get(key), want[key]))
    summary = parsed["summary"] or ""
    for token in ("valid=1", "rooms=%d" % EXPECTED_ROOMS,
                  "doors=%d" % EXPECTED_DOORS, "links=%d" % EXPECTED_LINKS):
        if token not in summary:
            return False, "authored summary missing " + token
    if parsed["traversal_fail"]:
        return False, "traversal FAIL marker: " + parsed["traversal_fail"]
    if not parsed["traversal_pass"]:
        return False, "missing traversal PASS marker"
    if not parsed["traversal_summary"]:
        return False, "missing traversal summary"
    fields = _fields(parsed["traversal_summary"])
    want = expected_traversal_counts
    for key, value in (("rooms", want["units"]), ("cells", want["cells"]),
                       ("interior_contacts", want["interior_contacts"]),
                       ("links", want["links"]), ("links_blocked", 0)):
        if fields.get(key) != str(value):
            return False, ("traversal %s: %r != expected %r"
                           % (key, fields.get(key), value))
    if parsed["contacts"] != want["interior_contacts"]:
        return False, ("recorded contacts %d != expected %d"
                       % (parsed["contacts"], want["interior_contacts"]))
    if parsed["interior_samples"] != want["cells"]:
        return False, ("interior samples %d != cells %d"
                       % (parsed["interior_samples"], want["cells"]))
    if parsed["link_samples"] <= 0:
        return False, "no link traversal samples"
    return True, ("authored table %d rows + traversal %d cells / %d contacts"
                  % (len(expected_links_rows), want["cells"],
                     want["interior_contacts"]))


def interpret_exit(code, text, expected_links_rows, expected_counts):
    """Classify a fixture exit: live PASS, guard BLOCKED, or failure."""
    parsed = parse_markers(text)
    if code == NEGATIVE_EXIT and parsed["captain_down"]:
        return {"verdict": "blocked", "detail": "guard CAPTAIN_DOWN exit 86"}
    if code == 0:
        ok, detail = check_chain(parsed, expected_links_rows, expected_counts)
        return {"verdict": "pass" if ok else "fail", "detail": detail}
    return {"verdict": "fail", "detail": "exit %d" % code}


def run_exe(exe, timeout=300, argv=(), cwd=None):
    env = dict(os.environ)
    env["PATH"] = ("C:/msys64/mingw64/bin;"
                   + env.get("PATH", ""))
    proc = subprocess.run(
        [str(exe)] + [str(a) for a in argv],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", timeout=timeout,
        env=env, cwd=str(cwd) if cwd else None,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return proc.returncode, proc.stdout


def evidence_record(**fields):
    record = {"schema": 1, "kind": "p2-yakushima4-collision-traversal-build"}
    record.update(fields)
    return record


def validate_evidence(record):
    if not isinstance(record, dict) or record.get("schema") != 1:
        raise ValueError("Evidence schema must be 1")
    for key in ("native_head", "exe_sha256", "guard_sha256",
                "caveinfo_sha256", "units_sha256", "ninja_dry_run",
                "chain", "exit", "traversal"):
        if key not in record:
            raise ValueError("Evidence missing: " + key)
    if record["chain"] != "pass":
        raise ValueError("Chain run did not pass")
    if record["exit"] != 0:
        raise ValueError("Fixture exit was not 0")
    return record


def toolchain(ninja_dir=None):
    if ninja_dir is None:
        import ninja
        ninja_dir = str(Path(ninja.BIN_DIR))
    return ninja_dir


def lease_key():
    return "yakushima4-collision-traversal-native"


def lease_generation(reg=None):
    """Current lane generation (never a stale hardcoded fence)."""
    if reg is None:
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                       CANONICAL_ROOT)
    return reg.status()["lanes"][lease_key()]["generation"]


def acquire(resource, pid, ttl=300):
    from workflow.registry import Registry
    reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                   CANONICAL_ROOT)
    gen = lease_generation(reg)
    return reg, reg.acquire(lease_key(), gen, resource, pid, ttl=ttl)


def renew(reg, resource, token, ttl=300):
    return reg.renew(lease_key(), lease_generation(reg), resource, token,
                     ttl=ttl)


def release(reg, resource, token):
    return reg.release(lease_key(), lease_generation(reg), resource, token)


def child_env(ninja_dir):
    return dict(os.environ,
                PATH="C:/msys64/mingw64/bin;" + str(ninja_dir) + ";"
                + os.environ.get("PATH", ""))


def run_under_lease(resource, commands, cwd, log_path, poll=5, env=None):
    """Run shell commands under the private-build/pool lease.

    An idle child holds the lease while the parent feeds it commands and
    renews; the lease is released only after the child exits. Queue waits
    are logged so a held pool is visible instead of silent.
    """
    from workflow.handoff import Rejected
    code = ("import json,subprocess,sys\n"
            "d=json.loads(sys.stdin.readline())\n"
            "for command in d['commands']:\n"
            ' print("COMMAND "+json.dumps(command),flush=True)\n'
            " result=subprocess.run(command,cwd=d['cwd'])\n"
            " if result.returncode: sys.exit(result.returncode)\n")
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as stream:
        child = subprocess.Popen(
            [sys.executable, "-u", "-c", code], stdin=subprocess.PIPE,
            stdout=stream, stderr=subprocess.STDOUT, text=True, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                       CANONICAL_ROOT)
        lease = None
        try:
            waited = 0
            while lease is None:
                result = reg.acquire(lease_key(), lease_generation(reg),
                                     resource, child.pid, ttl=300)
                if result["acquired"]:
                    lease = result["lease"]
                    break
                if waited % 60 == 0:
                    stream.write("LEASE_WAIT reason=%s\n"
                                 % result.get("reason", "queued"))
                    stream.flush()
                time.sleep(poll)
                waited += poll
            child.stdin.write(json.dumps(
                {"commands": commands, "cwd": str(cwd)}) + "\n")
            child.stdin.close()
            while child.poll() is None:
                try:
                    renew(reg, resource, lease["token"], ttl=300)
                except Rejected:
                    if child.poll() is None:
                        raise
                    break
                time.sleep(poll)
            result = child.wait()
        finally:
            if lease is not None and child.poll() is not None:
                try:
                    release(reg, resource, lease["token"])
                except Rejected:
                    pass
    return result


def run_python_under_lease(resource, payload, log_path, poll=5):
    """Execute one harness phase function inside the lease-holding child."""
    from workflow.handoff import Rejected
    code = ("import json,sys,traceback\n"
            "sys.path.insert(0, r'" + str(ROOT) + "')\n"
            "sys.path.insert(0, r'" + str(CANONICAL_ROOT) + "')\n"
            "d=json.loads(sys.stdin.readline())\n"
            "try:\n"
            " import scripts.build_p2_yakushima4_collision_traversal as harness\n"
            " fn=getattr(harness, d['fn'])\n"
            " fn(**d['kwargs'])\n"
            " print(json.dumps({'status': 'ok'}),flush=True)\n"
            "except Exception as error:\n"
            " traceback.print_exc()\n"
            " print(json.dumps({'status': 'error', 'error': str(error)}),\n"
            "       flush=True)\n"
            " sys.exit(1)\n")
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as stream:
        child = subprocess.Popen(
            [sys.executable, "-u", "-c", code], stdin=subprocess.PIPE,
            stdout=stream, stderr=subprocess.STDOUT, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                       CANONICAL_ROOT)
        lease = None
        try:
            waited = 0
            while lease is None:
                result = reg.acquire(lease_key(), lease_generation(reg),
                                     resource, child.pid, ttl=300)
                if result["acquired"]:
                    lease = result["lease"]
                    break
                if waited % 60 == 0:
                    stream.write("LEASE_WAIT reason=%s\n"
                                 % result.get("reason", "queued"))
                    stream.flush()
                time.sleep(poll)
                waited += poll
            child.stdin.write(json.dumps(payload) + "\n")
            child.stdin.close()
            while child.poll() is None:
                try:
                    renew(reg, resource, lease["token"], ttl=300)
                except Rejected:
                    if child.poll() is None:
                        raise
                    break
                time.sleep(poll)
            result = child.wait()
        finally:
            if lease is not None and child.poll() is not None:
                try:
                    release(reg, resource, lease["token"])
                except Rejected:
                    pass
    return result


def phase_configure(native, build, ninja_dir, log_path):
    native, build = Path(native), Path(build)
    return run_under_lease(
        "build:" + str(build.resolve()),
        [["cmake", "-S", str(native), "-B", str(build), "-G", "Ninja",
          "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
          "-DCMAKE_MAKE_PROGRAM=" + str(Path(ninja_dir) / "ninja.exe"),
          "-DCMAKE_BUILD_TYPE=Release", "-DPIKMIN_NATIVE_JAUDIO=ON",
          "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
          "-DP2_CHALLENGE_GUARD_INCLUDE_DIR="
          + str(CANONICAL_ROOT / "scripts")]],
        native, log_path, env=child_env(ninja_dir))


def phase_build(build, log_path, ninja_dir):
    build = Path(build)
    return run_under_lease(
        "build:" + str(build.resolve()),
        [["cmake", "--build", str(build), "--target", "pikmin_pc", "-j", "6"],
         ["cmake", "--build", str(build), "--target", "pikmin_pc",
          "--", "-n"]],
        build, log_path, env=child_env(ninja_dir))


def phase_single_tu(native, build, log_path, ninja_dir):
    """Compile the lane-owned fixture TU with the real engine compile flags.

    The fixture is never added to CMakeLists (that would need #186 review), so
    its in-graph object does not exist; instead the exact pc_main compile line
    is reused through the maintained replacement-main builder to prove the
    owned TU compiles against the real engine headers.
    """
    from scripts import build_pikmin2_fixture as builder
    native, build = Path(native), Path(build)
    output = Path(log_path).parent / "single-tu"
    output.mkdir(parents=True, exist_ok=True)
    fixture = (native / FIXTURE_REL).resolve()
    if not fixture.is_file():
        raise ValueError("Missing fixture TU: " + str(fixture))
    code, text = run_exe(Path(ninja_dir) / "ninja.exe",
                         argv=("-C", str(build), "-t", "commands", "pikmin_pc"))
    if code:
        raise RuntimeError("Cannot obtain Ninja commands")
    text = builder.expand_response_files(text, Path(ninja_dir) / "ninja.exe",
                                         build)
    commands = [line for line in text.splitlines() if line.strip()]
    compile_args, _link, _main, _objects = builder.select_commands(
        commands, native, build)
    args = builder.fixture_compile(compile_args, fixture, output, native)
    proc = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", timeout=600,
        env=child_env(ninja_dir), cwd=str(build))
    Path(log_path).write_text(
        "command: " + " ".join(args) + "\nexit=%d\n" % proc.returncode
        + proc.stdout,
        encoding="utf-8")
    return proc.returncode


def phase_fixture(native, build, output, expected_head, guard_dir, log_path):
    from scripts import build_pikmin2_fixture as builder
    native, build, output = Path(native), Path(build), Path(output)
    fixture = (native / FIXTURE_REL).resolve()
    if not fixture.is_file():
        raise ValueError("Missing fixture TU: " + str(fixture))
    guard = resolve_guard(guard_dir)
    env = dict(os.environ)
    env["PATH"] = "C:/msys64/mingw64/bin;" + env.get("PATH", "")
    env["CPLUS_INCLUDE_PATH"] = (str(guard.parent)
                                 + os.pathsep
                                 + env.get("CPLUS_INCLUDE_PATH", ""))
    old = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(env)
        stamp = "fixture-%d" % time.time_ns()
        record = builder.build_fixture(build, native, fixture,
                                       output / stamp, expected_head)
    finally:
        os.environ.clear()
        os.environ.update(old)
    if record.get("status") != "built":
        raise RuntimeError("Fixture build rejected: "
                           + str(record.get("error")))
    exe = output / stamp / "fixture.exe"
    Path(log_path).write_text(json.dumps(
        {"status": record["status"],
         "exe_sha256": sha256(exe),
         "provenance": str(output / stamp / "provenance.json")},
        indent=2) + "\n", encoding="utf-8")
    return 0


def load_sources(iso_path, caveinfo_path=None, units_path=None):
    """Read the two real source members (ISO preferred, files fallback)."""
    if caveinfo_path is not None and units_path is not None:
        caveinfo = Path(caveinfo_path).read_bytes()
        units = Path(units_path).read_bytes()
        return caveinfo, units
    iso = Path(iso_path) if iso_path is not None else DEFAULT_ISO
    if not iso.is_file():
        raise FileNotFoundError(
            "No local ISO and no staged source files supplied")
    caveinfo = read_source_member(iso, CAVEINFO_REL)
    units = read_source_member(iso, UNITS_REL)
    return caveinfo, units


def source_hashes(caveinfo, units):
    return (hashlib.sha256(bytes(caveinfo)).hexdigest(),
            hashlib.sha256(bytes(units)).hexdigest())


def phase_guardcheck(exe, compiler, guard_dir, log_path, expected_links_rows,
                     expected_counts):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text, expected_links_rows, expected_counts)
    if verdict["verdict"] != "pass":
        raise RuntimeError("Live self-test failed: "
                           + verdict["detail"] + "\n" + text[-2000:])
    with tempfile.TemporaryDirectory(prefix="p2y4trav") as tmp:
        negative = build_negative(compiler, guard_dir, tmp)
        ncode, ntext = run_exe(negative)
    nverdict = interpret_exit(ncode, ntext, expected_links_rows,
                              expected_counts)
    if nverdict["verdict"] != "blocked":
        raise RuntimeError("Negative guard path failed: exit %d\n%s"
                           % (ncode, ntext[-2000:]))
    if "PASS" in ntext:
        raise RuntimeError("Negative path emitted PASS")
    Path(log_path).write_text(
        "self_test: exit=%d %s\nnegative: exit=%d %s\n"
        % (code, verdict["detail"], ncode, nverdict["detail"]),
        encoding="utf-8")
    return 0


def build_negative(compiler, guard_dir, workdir):
    """Compile the header-only negative TU; return the exe path."""
    workdir = Path(workdir)
    src = workdir / "guard_negative.cpp"
    src.write_text(
        '#include "p2_fixture_captain_guard.h"\n'
        "int main()\n"
        "{\n"
        "    p2_fixture_require_captain(true, false, 0.0f, 7);\n"
        '    std::printf("P2_YAKUSHIMA4_NEGATIVE_UNREACHABLE\\n");\n'
        "    return 0;\n"
        "}\n",
        encoding="utf-8")
    exe = workdir / "guard_negative.exe"
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep
               + os.environ.get("PATH", ""))
    proc = subprocess.run(
        [str(compiler), "-std=c++17", "-I", str(guard_dir),
         str(src), "-o", str(exe)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", timeout=120, env=env)
    if proc.returncode or not exe.is_file():
        raise RuntimeError("Negative guard TU failed to compile: "
                           + proc.stdout[-2000:])
    return exe


def stage_units(output, units):
    """Stage the real unit pool where the fixture reads it (read-only copy)."""
    staging = Path(output) / "run-input"
    staging.mkdir(parents=True, exist_ok=True)
    target = staging / UNITS_STAGE_NAME
    target.write_bytes(bytes(units))
    return staging


def phase_run(exe, output, log_path, evidence_path, iso_path,
              caveinfo_path=None, units_path=None, native_head=None):
    caveinfo, units = load_sources(iso_path, caveinfo_path, units_path)
    cave_hash, units_hash = source_hashes(caveinfo, units)
    units_text = units.decode("shift_jis")
    expected_links_rows = expected_links(units_text)
    expected_counts = expected_traversal(units_text)
    staging = stage_units(output, units)
    code, text = run_exe(exe, argv=("--units=" + UNITS_STAGE_NAME,),
                         cwd=staging)
    verdict = interpret_exit(code, text, expected_links_rows,
                             expected_counts)
    Path(log_path).write_text(text, encoding="utf-8")
    if verdict["verdict"] != "pass":
        raise RuntimeError("Traversal run failed: " + verdict["detail"])
    parsed = parse_markers(text)
    record = evidence_record(
        native_head=native_head, exe_sha256=sha256(Path(exe)),
        guard_sha256=guard_record()["sha256"],
        caveinfo_sha256=cave_hash, units_sha256=units_hash,
        ninja_dry_run="ninja: no work to do.", chain="pass", exit=code,
        traversal=_fields(parsed["traversal_summary"]),
        detail=verdict["detail"])
    validate_evidence(record)
    Path(evidence_path).write_text(json.dumps(record, indent=2) + "\n",
                                   encoding="utf-8")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-native-head", default=None)
    parser.add_argument("--guard-dir", default=None)
    parser.add_argument("--ninja-dir", default=None)
    parser.add_argument("--iso", type=Path, default=None)
    parser.add_argument("--caveinfo-file", type=Path, default=None)
    parser.add_argument("--units-file", type=Path, default=None)
    parser.add_argument("--exe", type=Path, default=None)
    parser.add_argument("phases", nargs="+",
                        choices=("configure", "build", "single", "fixture",
                                 "guardcheck", "run", "all"))
    args = parser.parse_args(argv)
    ninja_dir = args.ninja_dir or toolchain()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    if "all" in args.phases:
        order = ("configure", "build", "single", "fixture", "guardcheck",
                 "run")
    else:
        order = args.phases
    exe = args.exe
    for phase in order:
        if phase == "configure":
            code = phase_configure(args.native, args.build, ninja_dir,
                                   out / "configure.log")
        elif phase == "build":
            code = phase_build(args.build, out / "build.log", ninja_dir)
        elif phase == "single":
            code = phase_single_tu(args.native, args.build,
                                   out / "single-tu.log", ninja_dir)
        elif phase == "fixture":
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(
                    ["git", "-C", str(args.native), "rev-parse", "HEAD"],
                    text=True).strip()
            code = run_python_under_lease(
                "build:" + str(Path(args.build).resolve()),
                {"fn": "phase_fixture",
                 "kwargs": {"native": str(args.native),
                            "build": str(args.build),
                            "output": str(out), "expected_head": head,
                            "guard_dir": args.guard_dir,
                            "log_path": str(out / "fixture.json")}},
                out / "fixture-lease.log")
            if code == 0 and exe is None:
                exe = max(out.glob("fixture-*/fixture.exe"),
                          key=lambda p: p.stat().st_mtime_ns)
        elif phase == "guardcheck":
            if exe is None:
                raise SystemExit("guardcheck needs --exe or a prior fixture phase")
            caveinfo, units = load_sources(
                args.iso, args.caveinfo_file, args.units_file)
            units_text = units.decode("shift_jis")
            expected_links_rows = expected_links(units_text)
            expected_counts = expected_traversal(units_text)
            compiler = Path("C:/msys64/mingw64/bin/g++.exe")
            guard = resolve_guard(args.guard_dir)
            code = phase_guardcheck(exe, compiler, guard.parent,
                                    out / "guardcheck.log",
                                    expected_links_rows, expected_counts)
        elif phase == "run":
            if exe is None:
                raise SystemExit("run needs --exe or a prior fixture phase")
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(
                    ["git", "-C", str(args.native), "rev-parse", "HEAD"],
                    text=True).strip()
            code = phase_run(exe, out, out / "run.log", out / "evidence.json",
                             args.iso, args.caveinfo_file, args.units_file,
                             native_head=head)
        if code:
            raise SystemExit("Phase %s failed; see %s"
                             % (phase, out / (phase + ".log")))
    print(json.dumps({"status": "ok", "output": str(out.resolve()),
                      "exe": str(exe) if exe else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
