"""Private build + fixture provenance for the damagumo stage-table row (#742).

Configures and builds the untouched private native tree (proves tree health;
records exe SHA-256 + ninja no-work), then compiles the standalone row +
fixture translation units directly with g++ (no engine link, no shared build
 edits) and runs the resolution matrix. All artifacts stay under the private
output directory. Heavy steps run under the caller-held registry lease.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, cwd, env=None):
    completed = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True,
                               encoding="utf-8", errors="replace")
    return completed.returncode, completed.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-native-head", required=True)
    parser.add_argument("--guard-dir", type=Path, default=None)
    parser.add_argument("--skip-native-build", action="store_true")
    args = parser.parse_args()
    native = args.native.resolve()
    build = args.build.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    record = {"native": str(native), "build": str(build),
              "expected_native_head": args.expected_native_head}

    if not args.skip_native_build:
        import os
        env = dict(os.environ,
                   PATH="C:/msys64/mingw64/bin;" + os.environ.get("PATH", ""))
        configure = ["cmake", "-S", str(native), "-B", str(build), "-G", "Ninja",
                     "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
                     "-DCMAKE_BUILD_TYPE=Release", "-DPIKMIN_NATIVE_JAUDIO=ON",
                     "-DPIKMIN_NATIVE_OPTIMIZE=OFF"]
        if args.guard_dir is not None:
            configure.append("-DP2_CHALLENGE_GUARD_INCLUDE_DIR=" + str(args.guard_dir))
        code, text = run(configure, native, env)
        (output / "configure.log").write_text(text, encoding="utf-8")
        if code:
            raise SystemExit("configure failed; see configure.log")
        code, text = run(["cmake", "--build", str(build), "--target", "pikmin_pc",
                          "-j", "6"], native, env)
        (output / "build.log").write_text(text, encoding="utf-8")
        if code:
            raise SystemExit("build failed; see build.log")
        code, text = run(["cmake", "--build", str(build), "--target", "pikmin_pc",
                          "--", "-n"], native, env)
        (output / "dryrun.log").write_text(text, encoding="utf-8")
        record["ninja_no_work"] = "ninja: no work to do." in text
        if code or not record["ninja_no_work"]:
            raise SystemExit("dry run failed; see dryrun.log")
        exe = build / "bin/nectar.exe"
        record["nectar_sha256"] = sha256(exe)

    import os as _os
    env = dict(_os.environ)
    env["PATH"] = "C:/msys64/mingw64/bin;" + env.get("PATH", "")
    compile_cmd = [
        "C:/msys64/mingw64/bin/g++.exe", "-std=c++17", "-Wall", "-Wextra",
        "-Werror", "-I" + str(native / "pc_port"),
        str(native / "pc_port/pc_p2_challenge_damagumo_stage.cpp"),
        str(native / "tools/p2_damagumo_stage_table_fixture.cpp"),
        "-o", str(output / "p2_damagumo_stage_table_fixture.exe")]
    code, text = run(compile_cmd, native, env)
    (output / "fixture-compile.log").write_text(text, encoding="utf-8")
    if code:
        raise SystemExit("fixture compile failed; see fixture-compile.log")
    fixture = output / "p2_damagumo_stage_table_fixture.exe"
    record["fixture_sha256"] = sha256(fixture)
    cases = [
        (["--cave-id", "ch_MUKI_damagumo", "--expect-resolved", "1"], 0,
         "P2_DAMAGUMO_STAGE_RESOLVED"),
        (["--cave-id", "ch_NARI_01kusachi", "--expect-resolved", "0"], 0,
         "P2_DAMAGUMO_STAGE_REFUSED"),
        (["--cave-id", "ch_MUKI_damagumo", "--captain-down"], 86,
         "P2_FIXTURE_CAPTAIN_DOWN"),
    ]
    logs = []
    for argv, want_code, want_marker in cases:
        code, text = run([str(fixture)] + argv, output, env)
        name = "run-" + argv[1].replace("_", "-") + ("-down" if "--captain-down" in argv else "") + ".log"
        (output / name).write_text(text, encoding="utf-8")
        logs.append({"argv": argv, "exit": code, "log": name,
                     "log_sha256": sha256(output / name)})
        if code != want_code or want_marker not in text:
            raise SystemExit("fixture case failed: %r (exit %d)" % (argv, code))
    record["runs"] = logs
    record["status"] = "built"
    (output / "provenance.json").write_text(json.dumps(record, indent=1) + "\n",
                                            encoding="utf-8")
    print(json.dumps({"status": "built",
                      "fixture_sha256": record["fixture_sha256"],
                      "runs": len(logs)}))


if __name__ == "__main__":
    main()
