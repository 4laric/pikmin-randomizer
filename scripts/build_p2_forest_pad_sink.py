#!/usr/bin/env python3
"""Private leased build/run helper for the forest PAD sink fixture (#794).

Builds the private pikmin_pc target (Ninja, C:/msys64/mingw64/bin on PATH),
then compiles native/tools/p2_forest_pad_sink_fixture.cpp and links it in
place of pc_port/pc_main.cpp against the pikmin_pc object graph (inline link
line; no response-file rewrite needed here). Finally it runs the guarded
fixture (self-test, negative test, inject/observe run) and asserts keyDown
observes the injected A/START presses with no bleed.

The fixture does NOT compile any engine TU in: it only includes Controller.h
and Dolphin/pad.h and calls the test-only sink, so a successful link proves
the sink is a real member of the pikmin_pc controllerMgr object. Production
code never calls the sink.

Heavy jobs require a canonical registry build lease held beforehand; this
script never acquires one itself. No maintained/consumer (#660)/#741 edits.
Runtime PATH must include the MinGW bin dir or the fixture crashes at load
(STATUS_DLL_NOT_FOUND); the runner sets it.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

FIXTURE = "tools/p2_forest_pad_sink_fixture.cpp"
PASS_MARKER = "PASS P2_FOREST_PAD_SINK_RUN markers=3"
OBSERVED = ("P2_FOREST_PAD_SINK_BASELINE_CLEAR",
            "P2_FOREST_PAD_SINK_OBSERVED button=A",
            "P2_FOREST_PAD_SINK_OBSERVED button=START")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
MAIN_REL = "CMakeFiles/pikmin_pc.dir/pc_port/pc_main.cpp.obj"
MINGW_BIN = r"C:\msys64\mingw64\bin"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args, env, cwd=None, timeout=3600):
    done = subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)
    return done.returncode, done.stdout


def check_run_markers(text):
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    missing = [m for m in OBSERVED if m not in text]
    if missing:
        return False, "missing markers: %s" % "; ".join(missing)
    return True, "run PASS with sink observations"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-native-head", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--run", metavar="RUNDIR")
    parser.add_argument("--scripts-root", default="scripts")
    args = parser.parse_args(argv)

    build_dir = Path(os.path.abspath(args.build)).resolve()
    source_dir = Path(os.path.abspath(args.source)).resolve()
    output_dir = Path(os.path.abspath(args.output)).resolve()
    fixture = (source_dir / FIXTURE).resolve()
    env = dict(os.environ)
    env["PATH"] = MINGW_BIN + os.pathsep + env.get("PATH", "")

    head = run(["git", "-C", str(source_dir), "rev-parse", "HEAD"], env)[1].strip()
    if head != args.expected_native_head:
        print("native head mismatch: " + head)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    record = {"schema": 1, "status": "checking", "source": str(source_dir),
              "build": str(build_dir), "fixture": str(fixture),
              "expected_native_head": args.expected_native_head,
              "observed_source": head, "commands": [], "guard_sha256": GUARD_SHA256}

    sys.path.insert(0, os.path.abspath(args.scripts_root))
    import build_pikmin2_fixture as bf
    cache = {}
    for line in (build_dir / "CMakeCache.txt").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(("#", "//")) and "=" in line:
            key, value = line.split("=", 1)
            cache[key.split(":")[0]] = value
    ninja = bf.absolute(cache["CMAKE_MAKE_PROGRAM"], build_dir)
    code, fresh = run([str(ninja), "-C", str(build_dir), "-n", "pikmin_pc"], env)
    (output_dir / "ninja-dry-run.log").write_text(fresh, encoding="utf-8", errors="replace")
    if "ninja: no work to do." not in fresh and not args.check_only:
        print("pikmin_pc not fresh; build it first")
        return 1
    code, text = run([str(ninja), "-C", str(build_dir), "-t", "commands", "pikmin_pc"], env)
    (output_dir / "native-commands.txt").write_text(text, encoding="utf-8", errors="replace")
    main_cpp = (source_dir / "pc_port/pc_main.cpp").resolve()
    compile_args = None
    for line in text.splitlines():
        if " -c " not in line and " -o " not in line:
            continue
        try:
            parsed = bf.compiler_args(line)
        except bf.BuildRejected:
            continue
        if "-c" in parsed and bf.absolute(parsed[bf.option_index(parsed, "-c")], build_dir) == main_cpp:
            compile_args = parsed
            break
    if compile_args is None:
        print("pc_main compile line not found")
        return 1
    compiler = Path(compile_args[0]).resolve()
    env["PATH"] = str(compiler.parent) + os.pathsep + env.get("PATH", "")
    link_line = next((l for l in text.splitlines()
                      if " -o " in l and " -c " not in l and "nectar.exe" in l), None)
    if link_line is None:
        print("pikmin_pc link line not found")
        return 1
    wrapper = re.fullmatch(
        r'(?:"[^"]*[/\\]cmd\.exe"|\S*[/\\]cmd\.exe|cmd\.exe) /C "cd \. && (.*) && cd \."',
        link_line, re.IGNORECASE)
    tokens = ((wrapper.group(1) if wrapper else link_line).split())
    if MAIN_REL not in tokens:
        print("pc_main object missing from link line")
        return 1
    fixture_obj = output_dir / "fixture.obj"
    tokens = [str(fixture_obj) if t == MAIN_REL else t for t in tokens]
    compile_cmd = bf.fixture_compile(compile_args, fixture, output_dir, source_dir)
    record["commands"].append(compile_cmd)
    code, clog = run(compile_cmd, env)
    (output_dir / "compile.log").write_text(clog, encoding="utf-8", errors="replace")
    if code:
        print("fixture compile failed")
        return 1
    link = list(tokens)
    link[bf.option_index(link, "-o")] = str(output_dir / "fixture.exe")
    if "-Wl,--out-implib," in " ".join(link):
        link = [("-Wl,--out-implib," + str(output_dir / "fixture.dll.a"))
                if t.startswith("-Wl,--out-implib,") else t for t in link]
    record["commands"].append(link)
    code, llog = run(link, env, cwd=str(build_dir))
    (output_dir / "link.log").write_text(llog, encoding="utf-8", errors="replace")
    if code:
        print("fixture link failed")
        return 1
    exe = output_dir / "fixture.exe"
    record["status"] = "built"
    record["artifacts"] = {"fixture.exe": {"path": str(exe), "sha256": sha256_file(exe),
                                           "size": exe.stat().st_size}}
    record["toolchain"] = {"compiler": str(compiler), "ninja": str(ninja)}
    (output_dir / "provenance.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("fixture built sha256 " + record["artifacts"]["fixture.exe"]["sha256"])
    if args.check_only or args.run is None:
        return 0
    rundir = Path(os.path.abspath(args.run)).resolve()
    rundir.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, extra in (("guard-self", ["--guard-self-test"]),
                        ("guard-negative", ["--guard-negative-test"]),
                        ("run", [])):
        proc = subprocess.Popen([str(exe)] + extra, cwd=str(rundir), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace")
        try:
            out, _ = proc.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            print(name, "timed out")
            return 2
        (output_dir / ("mode-%s.log" % name)).write_text(out, encoding="utf-8", errors="replace")
        results[name] = proc.returncode
        print(name, "exit", proc.returncode)
    ok, detail = check_run_markers((output_dir / "mode-run.log").read_text(encoding="utf-8", errors="replace"))
    self_ok = "SELFTEST_PASS" in (output_dir / "mode-guard-self.log").read_text(encoding="utf-8", errors="replace")
    neg_ok = CAPTAIN_DOWN in (output_dir / "mode-guard-negative.log").read_text(encoding="utf-8", errors="replace")
    record["modes"] = results
    record["run"] = {"detail": detail, "pass": ok and self_ok and neg_ok}
    record["run_log"] = str(output_dir / "mode-run.log")
    record["run_log_sha256"] = sha256_file(output_dir / "mode-run.log")
    (output_dir / "forest-pad-sink-run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(detail)
    return 0 if (ok and self_ok and neg_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
