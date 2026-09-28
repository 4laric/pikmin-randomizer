#!/usr/bin/env python3
"""Private leased build/run helper for the 03toy stage-table fixture (#752).

Builds the private pikmin_pc target (Ninja, C:/msys64/mingw64/bin on PATH),
then compiles native/tools/p2_toy_stage_table_fixture.cpp (which compiles in
pc_port/pc_p2_challenge_toy_stage.cpp as its single definition site) and links
it against the pikmin_pc object graph with pc_main replaced, through a
rewritten Ninja response file. Finally it runs the guarded fixture (self-test,
negative test, unknown refusal, window + resolution run) and asserts the exact
markers.

Heavy jobs require a canonical registry build lease held beforehand; this
script never acquires one itself. No maintained/consumer (#746)/#710 edits.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

FIXTURE = "tools/p2_toy_stage_table_fixture.cpp"
STAGE = "ch_NARI_03toy"
PASS_MARKER = "PASS P2_TOY_STAGE_TABLE_RUN markers=3"
MARKERS = (
    "P2_TOY_STAGE_TABLE stage=ch_NARI_03toy ui_index=5 floors=2",
    "P2_TOY_STAGE_RESOLVED stage=ch_NARI_03toy ui_index=5 floors=2 roster_total=100",
)
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
MAIN_REL = "CMakeFiles/pikmin_pc.dir/pc_port/pc_main.cpp.obj"


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
    missing = [m for m in MARKERS if m not in text]
    if missing:
        return False, "missing markers: %s" % "; ".join(missing)
    if "P2_TOY_STAGE_REFUSED" in text:
        return False, "refusal present"
    return True, "run PASS with exact markers"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-native-head", required=True)
    parser.add_argument("--run", metavar="RUNDIR")
    parser.add_argument("--scripts-root", default="scripts")
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
    import re
    wrapper = re.fullmatch(
        r'(?:"[^"]*[/\\]cmd\.exe"|\S*[/\\]cmd\.exe|cmd\.exe) /C "cd \. && (.*) && cd \."',
        link_line, re.IGNORECASE)
    core = wrapper.group(1) if wrapper else link_line
    tokens = core.split()
    rsp_token = next((t for t in tokens if t.startswith("@")), None)
    rsp_path = build_dir / rsp_token[1:]
    if rsp_path.is_file():
        content = rsp_path.read_text(encoding="utf-8", errors="replace")
    else:
        lines = (build_dir / "build.ninja").read_text(encoding="utf-8", errors="replace").splitlines()
        anchor = next(i for i, l in enumerate(lines) if l.strip() == "RSP_FILE = " + rsp_token[1:])
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
        content = "\n".join(objects + ([libs] if libs else [])) + "\n"
    if MAIN_REL not in content:
        print("pc_main object missing from response file")
        return 1
    fixture_obj = output_dir / "fixture.obj"
    (output_dir / "fixture.rsp").write_text(
        content.replace(MAIN_REL, fixture_obj.as_posix()), encoding="utf-8")
    compile_cmd = bf.fixture_compile(compile_args, fixture, output_dir, source_dir)
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
    code, llog = run(link, env, cwd=str(build_dir))
    (output_dir / "link.log").write_text(llog, encoding="utf-8", errors="replace")
    if code:
        print("fixture link failed")
        return 1
    exe = output_dir / "fixture.exe"
    record = {"schema": 1, "status": "built", "source": str(source_dir), "build": str(build_dir),
              "fixture": str(fixture), "expected_native_head": args.expected_native_head,
              "observed_source": head, "guard_sha256": GUARD_SHA256,
              "artifacts": {"fixture.exe": {"path": str(exe), "sha256": sha256_file(exe),
                                            "size": exe.stat().st_size}},
              "toolchain": {"compiler": str(compiler), "ninja": str(ninja)}}
    (output_dir / "provenance.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("fixture built sha256 " + record["artifacts"]["fixture.exe"]["sha256"])
    if args.run is None:
        return 0
    rundir = Path(os.path.abspath(args.run)).resolve()
    rundir.mkdir(parents=True, exist_ok=True)
    run_env = dict(env)
    run_env["SDL_AUDIODRIVER"] = "dummy"
    run_env["PIKMIN_P2_ROOM_WINDOW"] = "960x540"
    modes = {"guard-self": ["--guard-self-test"], "guard-negative": ["--guard-negative-test"],
             "unknown": ["--unknown-test"], "run": []}
    results = {}
    for name, extra in modes.items():
        proc = subprocess.Popen([str(exe)] + extra, cwd=str(rundir), env=run_env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace")
        try:
            out, _ = proc.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            print(name, "timed out")
            return 2
        (output_dir / ("mode-%s.log" % name)).write_text(out, encoding="utf-8", errors="replace")
        results[name] = {"exit": proc.returncode, "log": "mode-%s.log" % name}
        print(name, "exit", proc.returncode)
    ok, detail = check_run_markers((output_dir / "mode-run.log").read_text(encoding="utf-8", errors="replace"))
    self_ok = "SELFTEST_PASS" in (output_dir / "mode-guard-self.log").read_text(encoding="utf-8", errors="replace")
    neg_ok = ("P2_FIXTURE_CAPTAIN_DOWN" in (output_dir / "mode-guard-negative.log").read_text(encoding="utf-8", errors="replace"))
    unk_ok = ("UNKNOWN_REFUSED" in (output_dir / "mode-unknown.log").read_text(encoding="utf-8", errors="replace"))
    record["modes"] = results
    record["run"] = {"detail": detail, "pass": ok and self_ok and neg_ok and unk_ok}
    record["run_log"] = str(output_dir / "mode-run.log")
    record["run_log_sha256"] = sha256_file(output_dir / "mode-run.log")
    (output_dir / "toy-stage-run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(detail)
    return 0 if (ok and self_ok and neg_ok and unk_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
