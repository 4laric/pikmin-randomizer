#!/usr/bin/env python3
"""GL counting audit for netplay polish (issue #880 item 5, review m6).

Scans pc_port/gl for GL calls and verifies every one runs through a counting
macro/shim into pc_netplay_present_note_real(), so the authoritative-pass
tripwire sees all real GL work.

Usage:
    py -3.12 tools/netplay/gl_audit.py [--root <worktree>]

Exit 0 when UNCOUNTED total is 0, else 1. The full output is the audit log;
save it next to the handoff evidence.
"""

import argparse
import pathlib
import re
import sys

CALL_RE = re.compile(r"\b(gl[A-Za-z][A-Za-z0-9_]*)\s*\(")
DEFINE_RE = re.compile(r"^\s*#\s*define\s+(gl[A-Za-z0-9_]+)")
LOADER_RE = re.compile(r'SDL_GL_GetProcAddress\s*\(\s*"gl')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".",
                    help="worktree root holding pc_port/gl (default: cwd)")
    args = ap.parse_args()
    gldir = pathlib.Path(args.root) / "pc_port" / "gl"
    # Bundled Khronos/GLU headers are declarations, not call sites.
    VENDOR_HEADERS = {"gl.h", "glext.h", "glu.h"}
    files = sorted(p for p in gldir.glob("*.cpp")) \
        + sorted(p for p in gldir.glob("*.inc")) \
        + sorted(p for p in gldir.glob("*.h") if p.name not in VENDOR_HEADERS)
    if not files:
        print(f"gl_audit: no sources under {gldir}")
        return 1

    # Names routed through a counting macro: object-like or function-like
    # #defines in pc_gfx.cpp / pc_texpack.cpp whose expansion calls the
    # counting choke point, plus the cached_uniform* wrappers (they count
    # inline) and the glUniform*_ptr aliases that redirect to them.
    counted: set[str] = set()
    wrappers: set[str] = set()
    for path in files:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = DEFINE_RE.match(line)
            if m:
                counted.add(m.group(1))
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"static\s+\S[\w\s\*]*\b(cached_uniform\w+)\s*\(", text):
            wrappers.add(m.group(1))
    counted |= wrappers
    # glUniform*_ptr aliases redirect to cached_uniform* (pc_gfx.cpp).
    for path in files:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*#\s*define\s+(glUniform\w+_ptr)\s+cached_uniform", line)
            if m:
                counted.add(m.group(1))

    uncounted: list[tuple[str, int, str]] = []
    call_total = 0
    for path in files:
        for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # macro definitions / loader assignments, not calls
            if LOADER_RE.search(line):
                continue  # SDL_GL_GetProcAddress("gl...") loader strings
            code = line.split("//", 1)[0]  # drop trailing comments
            # Drop string literals (loader names, format strings).
            code = re.sub(r'"[^"]*"', '""', code)
            for m in CALL_RE.finditer(code):
                name = m.group(1)
                call_total += 1
                if name not in counted:
                    uncounted.append((path.name, lineno, name))

    print(f"gl_audit: {len(files)} files, {call_total} gl call sites, "
          f"{len(counted)} counted names")
    if uncounted:
        print("UNCOUNTED:")
        for fname, lineno, name in uncounted:
            print(f"  {fname}:{lineno}: {name}")
    print(f"UNCOUNTED total: {len(uncounted)}")
    return 0 if not uncounted else 1


if __name__ == "__main__":
    sys.exit(main())
