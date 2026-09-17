#!/usr/bin/env python3
"""Private leased build/run helper for the challenge persistence ENGINE MEMBERSHIP fixture (#725).

Builds the private pikmin_pc target (Ninja, C:/msys64/mingw64/bin on PATH),
then compiles native/tools/p2_challenge_persistence_membership_fixture.cpp and
links it in place of pc_port/pc_main.cpp through a rewritten Ninja response
file (the pikmin_pc link line is too long for a Windows command line, so it is
invoked as @fixture.rsp). Finally it runs the guarded fixture and asserts the
exact 7/7 probe markers.

The fixture does NOT compile the persistence module in: it only includes the
header and calls the recorders, so a successful link proves
pc_port/pc_p2_challenge_persistence.cpp is a real member of pikmin_pc (the
CMake change) and that the pc_bbft.cpp callsite emits the 7 markers.

Heavy jobs require a canonical registry build lease held beforehand; this
script never acquires one itself. No maintained/consumer (#561)/#710 edits.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

FIXTURE = "tools/p2_challenge_persistence_membership_fixture.cpp"
STAGE = "ch_MAT_route_rover"
PASS_MARKER = "PASS P2_CHALLENGE_PERSISTENCE_MEMBERSHIP_RUN"
MARKER_STEMS = ("SAVE_KEY", "LOAD_KEY", "CLEAR", "HIGHSCORE", "UNLOCK",
                "RECEIPT_DEDUP", "REENTRY")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
MAIN_REL = "CMakeFiles/pikmin_pc.dir/pc_port/pc_main.cpp.obj"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_run_markers(text):
    """PASS + exact 7/7 probe markers present, no captain-down."""
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    missing = [s for s in MARKER_STEMS
               if ("P2_CHALLENGE_%s stage=%s" % (s, STAGE)) not in text]
    if missing:
        return False, "missing probe markers: %s" % ",".join(missing)
    return True, "run PASS with exact 7/7 probe markers"


def run(args, env, cwd=None, timeout=3600):
    done = subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)
    return done.returncode, done.stdout


def parse_cache(build):
    cache = {}
    for line in (build / "CMakeCache.txt").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(("#", "//")) and "=" in line:
            key, value = line.split("=", 1)
            cache[key.split(":")[0]] = value
    return cache


def response_content(build, rsp_rel):
    rsp_path = build / rsp_rel
    if rsp_path.is_file():
        return rsp_path.read_text(encoding="utf-8", errors="replace")
    lines = (build / "build.ninja").read_text(encoding="utf-8", errors="replace").splitlines()
    anchor = next(i for i, l in enumerate(lines) if l.strip() == "RSP_FILE = " + rsp_rel)
    header = next(lines[i] for i in range(anchor, -1, -1) if lines[i].startswith("build "))
    objects = [t for t in header.split() if t.endswith(".obj")]
    begin = anchor
    while begin > 0 and lines[begin - 1].strip():
        begin -= 1
    end = anchor
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    libs = ""
    for l in lines[begin:end + 1]:
        if l.strip().startswith("LINK_LIBRARIES = "):
            libs = l.strip().split("=", 1)[1].strip()
    return "\n".join(objects + ([libs] if libs else [])) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-native-head", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--run", metavar="RUNDIR")
    parser.add_argument("--scripts-root", default="scripts")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args(argv)

    build_dir = Path(os.path.abspath(args.build)).resolve()
    source_dir = Path(os.path.abspath(args.source)).resolve()
    output_dir = Path(os.path.abspath(args.output)).resolve()
    fixture = (source_dir / FIXTURE).resolve()
    env = dict(os.environ)
    env["PATH"] = r"C:\msys64\mingw64\bin" + os.pathsep + env.get("PATH", "")

    head = run(["git", "-C", str(source_dir), "rev-parse", "HEAD"], env)[1].strip()
    if head != args.expected_native_head:
        print("native head mismatch: " + head)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    record = {"schema": 1, "status": "checking", "source": str(source_dir),
              "build": str(build_dir), "fixture": str(fixture),
              "expected_native_head": args.expected_native_head,
              "observed_source": head, "commands": [], "guard_sha256": GUARD_SHA256}

    if not args.skip_build:
        code, log = run(["cmake", "--build", str(build_dir), "--target", "pikmin_pc", "-j", "6"], env)
        (output_dir / "build-pikmin-pc.log").write_text(log, encoding="utf-8", errors="replace")
        if code:
            print("pikmin_pc build failed")
            return 1
        print("pikmin_pc build ok")

    sys.path.insert(0, os.path.abspath(args.scripts_root))
    import build_pikmin2_fixture as bf
    cache = parse_cache(build_dir)
    ninja = bf.absolute(cache["CMAKE_MAKE_PROGRAM"], build_dir)
    code, fresh = run([str(ninja), "-C", str(build_dir), "-n", "pikmin_pc"], env)
    (output_dir / "ninja-dry-run.log").write_text(fresh, encoding="utf-8", errors="replace")
    if "ninja: no work to do." not in fresh:
        print("pikmin_pc not fresh")
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
                      if " -o " in l and " -c " not in l and ".rsp" in l), None)
    if link_line is None:
        print("response-file link line not found")
        return 1
    wrapper = re.fullmatch(
        r'(?:"[^"]*[/\\]cmd\.exe"|\S*[/\\]cmd\.exe|cmd\.exe) /C "cd \. && (.*) && cd \."',
        link_line, re.IGNORECASE)
    core = wrapper.group(1) if wrapper else link_line
    tokens = core.split()
    rsp_token = next((t for t in tokens if t.startswith("@")), None)
    content = response_content(build_dir, rsp_token[1:])
    if MAIN_REL not in content:
        print("pc_main object missing from response file")
        return 1
    fixture_obj = output_dir / "fixture.obj"
    (output_dir / "fixture.rsp").write_text(
        content.replace(MAIN_REL, fixture_obj.as_posix()), encoding="utf-8")
    compile_cmd = bf.fixture_compile(compile_args, fixture, output_dir, source_dir)
    record["commands"].append(compile_cmd)
    code, clog = run(compile_cmd, env)
    (output_dir / "compile.log").write_text(clog, encoding="utf-8", errors="replace")
    if code:
        print("fixture compile failed")
        return 1
    link = [("@%s" % (output_dir / "fixture.rsp")) if t == rsp_token else t for t in tokens]
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
    run_env = dict(env)
    run_env["SDL_AUDIODRIVER"] = "dummy"
    run_env["PIKMIN_P2_ROOM_WINDOW"] = "960x540"
    proc = subprocess.Popen([str(exe)], cwd=str(rundir), env=run_env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors="replace")
    try:
        out, _ = proc.communicate(timeout=600)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("run timed out")
        return 2
    ok, detail = check_run_markers(out)
    log_path = output_dir / "membership-run.log"
    log_path.write_text(out, encoding="utf-8", errors="replace")
    record["run"] = {"exit": proc.returncode, "detail": detail, "pass": ok}
    record["run_log"] = str(log_path)
    record["run_log_sha256"] = sha256_file(log_path)
    (output_dir / "membership-run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(detail)
    return 0 if (proc.returncode == 0 and ok) else 1


if __name__ == "__main__":
    sys.exit(main())
