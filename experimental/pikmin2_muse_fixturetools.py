"""Additive preflight/diagnostic adapter for private fixture builds.

Lane muse-fixturetools (l67, child #507). Investigates repeated private
fixture/build failures across Muse l52-l61 logs without touching the shared
runner, the fixture builder, or any other lane's worktree.

What it checks, in builder order (fail-closed, first failure wins):

1. Ninja discovery: an existing ``ninja`` executable must be resolvable from
   the CMake cache ``CMAKE_MAKE_PROGRAM``, ``PATH``, or the Python ``ninja``
   package. A missing Ninja reproduces the l52/l53/l55/l60/l61 first-attempt
   ``CMAKE was unable to find a build program corresponding to "Ninja"``
   failure; the remediation names the exact ``-DCMAKE_MAKE_PROGRAM=`` flag
   the common leased runner now passes.
2. Generator/toolchain agreement: the configured ``CMAKE_GENERATOR`` must be
   ``Ninja``, ``CMAKE_HOME_DIRECTORY`` must be the claimed source directory,
   and the cached compilers plus make program must exist on disk.
3. Path validity: source carries ``CMakeLists.txt`` and
   ``pc_port/pc_main.cpp``; the build directory carries ``CMakeCache.txt``;
   the fixture exists with a ``.cpp`` suffix; the private output directory
   is outside both source and production build.
4. Provenance freshness: native ``HEAD`` must equal the explicitly expected
   commit and ``ninja -n -d explain pikmin_pc`` must report no work to do.
5. Command portability: ``ninja -t commands`` lines selected by the builder
   (``' -c '``/``' -o '``) must not carry raw ``@<file>.rsp`` response-file
   references, which the maintained builder rejects with
   ``Empty command or unsupported response file`` (l60-fixture-01, l61
   fixture-build). The diagnosis names the exact offending line and points
   at the worktree builder carrying the #437 expansion fixes.

This module never configures, builds, or launches anything except the two
read-only probes (``git rev-parse`` and ``ninja -n``). ::

    py -3.12 -m experimental.pikmin2_muse_fixturetools preflight \
        --source <native> --build <build> --output <new-dir> \
        --fixture <fixture.cpp> --expected-native-head <40-hex>
    py -3.12 -m experimental.pikmin2_muse_fixturetools diagnose \
        --commands <native-commands.txt>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOL = "muse-fixturetools-preflight-v1"
FRESH_TEXT = "ninja: no work to do."
EXPECTED_GENERATOR = "Ninja"
FULL_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")

CMD_WRAPPER_RE = re.compile(
    r'(?:"[^"]*[/\\]cmd\.exe"|\S*[/\\]cmd\.exe|cmd\.exe) /C "cd \. && (.*) && cd \."',
    re.IGNORECASE | re.DOTALL,
)

# Matches a raw Ninja response-file reference: @"...rsp" or @....rsp.
RESPONSE_RE = re.compile(r'@"([^"]+\.rsp)"|@([^\s"@]+\.rsp)', re.IGNORECASE)


def _fail(check, detail, remediation):
    return {"check": check, "ok": False, "detail": detail,
            "remediation": remediation}


def _pass(check, detail):
    return {"check": check, "ok": True, "detail": detail, "remediation": None}


def find_ninja(search_path=None, hint=None):
    """Locate a ninja executable. Returns (Path|None, notes)."""
    notes = []
    candidates = []
    if hint:
        candidates.append(Path(hint))
        notes.append("cache CMAKE_MAKE_PROGRAM=" + str(hint))
    found = shutil.which("ninja", path=search_path)
    if found:
        candidates.append(Path(found))
        notes.append("PATH ninja=" + found)
    try:
        import ninja  # type: ignore

        packaged = Path(ninja.BIN_DIR) / "ninja.exe"
        candidates.append(packaged)
        notes.append("python-ninja=" + str(packaged))
        packaged_exe = Path(ninja.BIN_DIR) / "ninja"
        candidates.append(packaged_exe)
    except Exception as error:  # pragma: no cover - environment dependent
        notes.append("python-ninja unavailable: " + str(error))
    for candidate in candidates:
        if candidate.is_file():
            return candidate, notes
        notes.append("missing candidate: " + str(candidate))
    return None, notes


def read_cmake_cache(build):
    """Parse CMakeCache.txt KEY[:TYPE]=VALUE lines (skips # and //)."""
    cache_file = Path(build) / "CMakeCache.txt"
    if not cache_file.is_file():
        return None, "no CMakeCache.txt in " + str(build)
    values = {}
    for line in cache_file.read_text(encoding="utf-8",
                                     errors="replace").splitlines():
        if not line or line.startswith(("#", "//")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.split(":")[0]] = value
    return values, None


def split_windows_args(command):
    """Split Windows argv grammar without destroying backslashes.

    Minimal re-implementation of the argv grammar the fixture builder
    enforces: returns None for empty input or any response-file argument
    (``@file``), since the maintained builder rejects exactly those.
    """
    args, at = [], 0
    size = len(command)
    while at < size:
        while at < size and command[at] in " \t":
            at += 1
        if at == size:
            break
        value, quoted = [], False
        while at < size and (quoted or command[at] not in " \t"):
            if command[at] == "\\":
                end = at
                while end < size and command[end] == "\\":
                    end += 1
                number = end - at
                if end < size and command[end] == '"':
                    value.extend("\\" * (number // 2))
                    at = end
                    if number % 2:
                        value.append('"')
                        at += 1
                        continue
                else:
                    value.extend("\\" * number)
                    at = end
                    continue
            if command[at] == '"':
                if quoted and at + 1 < size and command[at + 1] == '"':
                    value.append('"')
                    at += 2
                    continue
                quoted = not quoted
            else:
                value.append(command[at])
            at += 1
        if quoted:
            return None
        args.append("".join(value))
    if not args or any(arg.startswith("@") for arg in args):
        return None
    return args


def unwrap_command(line):
    """Strip the inert CMake ``cmd /C "cd . && ... && cd ."`` wrapper."""
    match = CMD_WRAPPER_RE.fullmatch(line.strip())
    if match:
        return match.group(1)
    return line


def diagnose_commands(text):
    """Classify builder-selected command lines for portability.

    Returns a dict with ``selected`` (lines containing `` -c ``/`` -o ``),
    ``response_lines`` (selected lines carrying a raw ``@...rsp``
    reference), ``unparsable`` (selected lines the maintained argv grammar
    rejects), and ``ok`` (True only when both lists are empty).
    """
    selected, response_lines, unparsable = [], [], []
    for line in text.splitlines():
        if " -c " not in line and " -o " not in line:
            continue
        selected.append(line)
        command = unwrap_command(line)
        match = RESPONSE_RE.search(command)
        if match:
            response_lines.append(
                {"reference": match.group(0),
                 "line_head": line[:220]})
        if split_windows_args(command) is None and match is None:
            unparsable.append({"line_head": line[:220]})
    return {"selected": len(selected), "response_lines": response_lines,
            "unparsable": unparsable,
            "ok": not response_lines and not unparsable}


def _run(args, cwd, timeout=120):
    try:
        completed = subprocess.run(
            args, cwd=str(cwd), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        return None, "cannot run " + " ".join(args) + ": " + str(error)
    return completed, None


def preflight(source, build, output, fixture, expected_head,
              search_path=None):
    """Run every check; return a JSON-serialisable report dict."""
    checks = []
    source, build, output = Path(source), Path(build), Path(output)
    fixture = Path(fixture)

    # 3a. Source identity files.
    missing = [str(source / name) for name in
               ("CMakeLists.txt", "pc_port/pc_main.cpp")
               if not (source / name).is_file()]
    if missing:
        checks.append(_fail(
            "source-paths", "missing source inputs: " + ", ".join(missing),
            "point --source at the configured native worktree "
            "(must carry CMakeLists.txt and pc_port/pc_main.cpp)"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    checks.append(_pass("source-paths", "source carries CMakeLists.txt "
                                       "and pc_port/pc_main.cpp"))

    # 3b. Build cache presence.
    cache, error = read_cmake_cache(build)
    if cache is None:
        checks.append(_fail(
            "build-paths", error,
            "configure the private build directory first with the leased "
            "runner --configure, then rerun preflight"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    checks.append(_pass("build-paths", "CMakeCache.txt present"))

    # 3c. Fixture + output placement.
    if not fixture.is_file() or fixture.suffix != ".cpp":
        checks.append(_fail(
            "fixture-paths",
            "expected an existing C++ fixture source, got " + str(fixture),
            "point --fixture at tools/p2_muse_fixturetools_fixture.cpp "
            "inside the private native worktree"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    try:
        resolved_output = output.resolve()
        inside_source = resolved_output.is_relative_to(source.resolve())
        inside_build = resolved_output.is_relative_to(build.resolve())
    except (OSError, ValueError) as error:
        checks.append(_fail("output-paths", "cannot resolve output: "
                                           + str(error),
                            "use an absolute --output path"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    if inside_source or inside_build:
        checks.append(_fail(
            "output-paths",
            "private output must be outside the native source and "
            "production build, got " + str(output),
            "use a fresh directory such as output/muse-wave/l67/<attempt>"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    checks.append(_pass("output-paths", "output outside source and build; "
                                        "fixture is an existing .cpp file"))

    # 2. Generator agreement.
    generator = cache.get("CMAKE_GENERATOR")
    if generator != EXPECTED_GENERATOR:
        checks.append(_fail(
            "generator",
            "CMAKE_GENERATOR=%r, expected %r" % (generator,
                                                EXPECTED_GENERATOR),
            "reconfigure with -G Ninja (the leased runner passes it); a "
            "Makefiles-configured build directory cannot be reused"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    checks.append(_pass("generator", "CMAKE_GENERATOR=Ninja"))

    # 2b. Configured source agreement.
    home = cache.get("CMAKE_HOME_DIRECTORY")
    if home is None or Path(home).resolve() != source.resolve():
        checks.append(_fail(
            "configured-source",
            "CMAKE_HOME_DIRECTORY=%r does not match --source %s"
            % (home, source),
            "reconfigure with -S pointing at the private native worktree; "
            "never reuse a build directory configured from another source"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    checks.append(_pass("configured-source",
                        "configured source matches --source"))

    # 1+2c. Toolchain existence (compilers + make program).
    ninja_hint = cache.get("CMAKE_MAKE_PROGRAM")
    missing_tools = [name + "=" + str(cache.get(name)) for name in
                     ("CMAKE_C_COMPILER", "CMAKE_CXX_COMPILER")
                     if not cache.get(name)
                     or not Path(cache[name]).is_file()]
    if missing_tools:
        checks.append(_fail(
            "toolchain",
            "missing cached compilers: " + ", ".join(missing_tools),
            "reconfigure with -DCMAKE_C_COMPILER=gcc "
            "-DCMAKE_CXX_COMPILER=g++ and MinGW on PATH"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    ninja, notes = find_ninja(search_path=search_path, hint=ninja_hint)
    if ninja is None:
        checks.append(_fail(
            "ninja",
            "no ninja executable found (" + "; ".join(notes) + ")",
            "pass -DCMAKE_MAKE_PROGRAM=<python-ninja>/ninja.exe at "
            "configure time; the common leased runner already does this"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    checks.append(_pass("toolchain",
                        "compilers exist; ninja=" + str(ninja)))

    # 4a. Expected HEAD.
    if not FULL_SHA_RE.match(expected_head or ""):
        checks.append(_fail(
            "expected-head",
            "expected-native-head is not a 40-hex commit",
            "pass the full native HEAD the build was configured from"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    completed, error = _run(["git", "-C", str(source), "rev-parse", "HEAD"],
                            source)
    if completed is None or completed.returncode != 0:
        checks.append(_fail("native-head", error or "git rev-parse failed",
                            "run preflight from a host with the native "
                            "worktree available"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    head = completed.stdout.strip()
    if head != expected_head:
        checks.append(_fail(
            "native-head",
            "native HEAD %s differs from expected %s"
            % (head, expected_head),
            "rebuild from the expected commit or update the expectation; "
            "a produced executable alone is not provenance"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    checks.append(_pass("native-head", "HEAD matches expectation"))

    # 4b. Ninja freshness (read-only dry run with explanation).
    completed, error = _run([str(ninja), "-n", "-d", "explain", "pikmin_pc"],
                            build, timeout=300)
    if completed is None or completed.returncode != 0 or \
            completed.stdout.strip() != FRESH_TEXT:
        detail = error or ("ninja reports pending work: "
                           + (completed.stdout.strip()[:300]
                              if completed else "no output"))
        checks.append(_fail(
            "freshness", detail,
            "rebuild the private target via the leased runner until "
            "`ninja -n` reports no work to do; the builder never rebuilds "
            "production itself"))
        return {"tool": TOOL, "status": "rejected", "checks": checks,
                "error": checks[-1]["detail"]}
    checks.append(_pass("freshness", FRESH_TEXT))

    return {"tool": TOOL, "status": "ok", "checks": checks, "error": None,
            "ninja": str(ninja), "native_head": head}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("preflight", help="run every preflight check")
    prepare.add_argument("--source", type=Path, required=True)
    prepare.add_argument("--build", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--fixture", type=Path, required=True)
    prepare.add_argument("--expected-native-head", required=True)

    diagnose = sub.add_parser("diagnose",
                              help="classify ninja -t commands output")
    diagnose.add_argument("--commands", type=Path, required=True,
                          help="native-commands.txt from a fixture attempt")

    args = parser.parse_args(argv)
    if args.command == "preflight":
        report = preflight(args.source, args.build, args.output,
                           args.fixture, args.expected_native_head,
                           search_path=os.environ.get("PATH"))
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "ok" else 1
    text = args.commands.read_text(encoding="utf-8", errors="replace")
    result = diagnose_commands(text)
    print(json.dumps(result, indent=2))
    if result["response_lines"]:
        print("DIAGNOSIS response-file link line(s) require expansion: "
              "the maintained builder rejects raw @...rsp arguments with "
              "'Empty command or unsupported response file'; use "
              "<lane-root>/scripts/build_pikmin2_fixture.py (carries the "
              "#437 expansion fixes).", file=sys.stderr)
        return 2
    if result["unparsable"]:
        print("DIAGNOSIS unparsable builder-selected command line(s).",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
