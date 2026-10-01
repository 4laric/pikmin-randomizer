#!/usr/bin/env python3
"""Private leased build/run helper for the challenge persistence fixture (#713).

Drives the maintained generic fixture builder
(scripts/build_pikmin2_fixture.py) for
native/tools/p2_challenge_persistence_fixture.cpp, then runs the guarded
marker observation and validates the 7/7 probe markers. No maintained,
CMakeLists, preview, consumer (#561), or call-site (#710) edits.

Usage (from the canonical root):
  py -3.12 scripts/build_p2_challenge_persistence.py --source <native> --build <build>
      --output <out> --expected-native-head <40hex> [--check-only] [--run <rundir>]
      [--run-only]

Steps: builder --check-only (or full build), ninja -n dry run, exe SHA-256,
fixture provenance `built`, guarded run asserting PASS
P2_CHALLENGE_PERSISTENCE_RUN with the exact 7 probe markers and no
CAPTAIN_DOWN / injection markers. Heavy jobs require a canonical registry
build lease held beforehand; this script never acquires one itself.

Response-file note: the maintained builder parses only inline argv and rejects
`@responsefile` tokens, but the pikmin_pc link is `@CMakeFiles\\pikmin_pc.rsp`
(Ninja materializes it only while linking, so no file exists on a fresh tree).
This helper expands that token into the exact argv Ninja would pass
(`rspfile_content = $in $LINK_PATH $LINK_LIBRARIES`, reconstructed from
build.ninja) and then delegates to the maintained pipeline unchanged: same
freshness checks, same input/toolchain snapshots, same provenance schema. The
expansion is recorded as `pikmin_pc.expanded.rsp` beside the provenance. No
production rebuild.

Compiler note: the private build's CMakeCache stores a bare compiler name
(CMAKE_CXX_COMPILER=g++), which the maintained path resolver maps under the
build dir where no such file exists. Bare program names therefore fall back
to a PATH lookup, snapshotting the real binary Ninja invokes. Absolute and
slash-bearing paths resolve exactly as before.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

FIXTURE = os.path.join("tools", "p2_challenge_persistence_fixture.cpp")
STAGE = "ch_MAT_route_rover"
PASS_MARKER = "PASS P2_CHALLENGE_PERSISTENCE_RUN"
MARKER_STEMS = ("SAVE_KEY", "LOAD_KEY", "CLEAR", "HIGHSCORE", "UNLOCK",
                "RECEIPT_DEDUP", "REENTRY")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


_RSP = {"root": None, "out": None, "wrote": False}


def _ninja_unescape(token):
    out, i = [], 0
    while i < len(token):
        if token[i] == "$" and i + 1 < len(token) and token[i + 1] in "$: ":
            out.append(token[i + 1])
            i += 2
            continue
        out.append(token[i])
        i += 1
    return "".join(out)


def _reconstruct_rsp_argv(build_dir, rsp_name):
    """Rebuild the argv Ninja would place in a link response file.

    Matches the edge whose `RSP_FILE` binding equals rsp_name and expands the
    rule's `rspfile_content = $in $LINK_PATH $LINK_LIBRARIES`: explicit edge
    objects, then implicit libs (both `$in`, in edge order), then the edge's
    LINK_PATH and LINK_LIBRARIES bindings. All tokens Ninja-unescaped.
    """
    want = rsp_name.replace("\\", "/")
    text = (build_dir / "build.ninja").read_text(encoding="utf-8", errors="replace")
    edge_inputs, edge_vars = None, {}
    header, variables = None, {}
    for line in text.splitlines():
        if line.startswith("build "):
            header, variables = line, {}
            continue
        if header is not None and (line.startswith(" ") or line.startswith("\t")):
            if "=" in line:
                key, value = line.strip().split("=", 1)
                variables[key.strip()] = value.strip()
            continue
        if header is not None:
            if variables.get("RSP_FILE", "").replace("\\", "/") == want:
                edge_inputs, edge_vars = header, dict(variables)
                break
            header, variables = None, {}
    if header is not None and variables.get("RSP_FILE", "").replace("\\", "/") == want:
        edge_inputs, edge_vars = header, dict(variables)
    if edge_inputs is None:
        raise ValueError("no link edge binds RSP_FILE " + rsp_name)
    parts = edge_inputs.split()
    if not parts or parts[0] != "build":
        raise ValueError("malformed link edge for " + rsp_name)
    try:
        outputs_end = next(i for i, t in enumerate(parts) if t.endswith(":"))
    except StopIteration:
        raise ValueError("malformed link edge for " + rsp_name)
    explicit, implicit, seen_bar = [], [], False
    for token in parts[outputs_end + 2:]:
        if token == "|":
            seen_bar = True
            continue
        if token == "||":
            break
        (implicit if seen_bar else explicit).append(_ninja_unescape(token))
    argv = explicit + implicit
    for key in ("LINK_PATH", "LINK_LIBRARIES"):
        argv.extend(_ninja_unescape(t) for t in edge_vars.get(key, "").split())
    if not any(t.endswith((".obj", ".o")) for t in argv):
        raise ValueError("reconstructed response file has no objects")
    return argv


def _expand_rsp_token(token):
    from pathlib import Path
    root = Path(_RSP["root"])
    candidate = root / token[1:].replace("\\", "/")
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8", errors="replace").split()
    argv = _reconstruct_rsp_argv(root, token[1:])
    if _RSP["out"] is not None and not _RSP["wrote"]:
        Path(_RSP["out"]).mkdir(parents=True, exist_ok=True)
        (Path(_RSP["out"]) / "pikmin_pc.expanded.rsp").write_text(
            "\n".join(argv) + "\n", encoding="utf-8")
        _RSP["wrote"] = True
    return argv


def check_run_markers(text):
    """PASS + exact 7/7 probe markers present, no captain-down, no injection."""
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    missing = []
    for stem in MARKER_STEMS:
        line = "P2_CHALLENGE_%s stage=%s" % (stem, STAGE)
        if line not in text:
            missing.append(stem)
    if missing:
        return False, "missing probe markers: %s" % ",".join(missing)
    injected = [t for t in INJECTED_TOKENS if t in text]
    if injected:
        return False, "injection markers present: %s" % ",".join(injected)
    return True, "run PASS with exact 7/7 probe markers"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="native worktree")
    parser.add_argument("--build", required=True, help="private build dir (leased)")
    parser.add_argument("--output", required=True, help="private output dir")
    parser.add_argument("--expected-native-head", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--run", metavar="RUNDIR")
    parser.add_argument("--run-only", action="store_true",
                        help="skip the build; validate against the existing built "
                             "provenance in --output and run it (same head required)")
    args = parser.parse_args(argv)

    fixture = os.path.join(os.path.abspath(args.source), FIXTURE)
    from pathlib import Path
    import shutil
    build_dir = Path(os.path.abspath(args.build)).resolve()
    output_dir = Path(os.path.abspath(args.output)).resolve()
    fixture_path = Path(fixture).resolve()
    sys.path.insert(0, os.path.abspath(os.path.join("scripts")))
    import build_pikmin2_fixture as maintained
    real_compiler_args = maintained.compiler_args
    real_absolute = maintained.absolute

    def absolute_with_path_lookup(value, root):
        path = real_absolute(value, root)
        flat = value.replace("\\", "/")
        if not path.is_file() and "/" not in flat and ":" not in flat:
            found = shutil.which(value)
            if found:
                return Path(found).resolve()
        return path

    maintained.absolute = absolute_with_path_lookup
    _RSP["root"] = str(build_dir)
    _RSP["out"] = str(output_dir)
    _RSP["wrote"] = False

    def compiler_args_with_rsp(command):
        def splice(match):
            expanded = _expand_rsp_token("@" + match.group(1))
            return match.group(0)[:1] + " ".join(expanded)
        return real_compiler_args(re.sub(r"(?:^|\s)@(\S+)", splice, command))

    maintained.compiler_args = compiler_args_with_rsp
    build_reused = False
    try:
        if args.run_only:
            if args.check_only:
                print("--run-only cannot be combined with --check-only")
                return 2
            proven = output_dir / "provenance.json"
            if not proven.is_file():
                print("no built provenance to reuse in " + str(output_dir))
                return 2
            prior = json.loads(proven.read_text(encoding="utf-8"))
            if prior.get("status") != "built":
                print("existing provenance is not built: " + str(prior.get("status")))
                return 2
            if prior.get("expected_native_head") != args.expected_native_head:
                print("existing provenance head mismatch")
                return 2
            if prior.get("observed_source", {}).get("head") != args.expected_native_head:
                print("existing provenance source mismatch")
                return 2
            build_reused = True
            record = {"fixture": FIXTURE, "rundir": "", "guard_sha256": GUARD_SHA256,
                      "build_reused": True, "provenance": str(proven)}
            print("reusing built fixture at expected head " + args.expected_native_head)
        else:
            record = maintained.build_fixture(
                build_dir, Path(os.path.abspath(args.source)).resolve(),
                fixture_path, output_dir, args.expected_native_head,
                check_only=args.check_only)
    except (maintained.BuildRejected, OSError) as error:
        print("builder step failed: " + str(error))
        return 1
    finally:
        maintained.compiler_args = real_compiler_args
        maintained.absolute = real_absolute
    if not build_reused:
        print("builder step complete: " + record["status"])
        if args.check_only or record["status"] != "built":
            return 0 if record["status"] in ("built", "checked_not_built") else 1
    if args.run is None:
        print("build/check step complete; no run requested")
        return 0
    rundir = os.path.abspath(args.run)
    record["fixture"] = FIXTURE
    record["rundir"] = rundir
    record["guard_sha256"] = GUARD_SHA256
    exe_candidates = []
    for base in (args.output, args.build):
        for name in ("fixture.exe", "p2_challenge_persistence.exe"):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                exe_candidates.append(path)
    if not exe_candidates:
        print("fixture exe missing: build first")
        return 2
    exe = exe_candidates[0]
    record["exe"] = exe
    record["exe_sha256"] = sha256_file(exe)
    env = dict(os.environ)
    env["SDL_AUDIODRIVER"] = "dummy"
    env["PIKMIN_P2_ROOM_WINDOW"] = "960x540"
    proc = subprocess.Popen([exe], cwd=rundir, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            errors="replace")
    try:
        out, _ = proc.communicate(timeout=600)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("run timed out")
        return 2
    ok, detail = check_run_markers(out)
    record["run"] = {"exit": proc.returncode, "detail": detail, "pass": ok}
    with open(os.path.join(args.output, "persistence-run.log"), "w",
              encoding="utf-8", errors="replace") as f:
        f.write(out)
    record["run_log"] = os.path.join(os.path.abspath(args.output), "persistence-run.log")
    record["run_log_sha256"] = sha256_file(record["run_log"])
    print(detail)
    with open(os.path.join(args.output, "persistence-run.json"), "w",
              encoding="utf-8") as f:
        json.dump(record, f, indent=1)
    return 0 if (proc.returncode == 0 and ok) else 1


if __name__ == "__main__":
    sys.exit(main())
