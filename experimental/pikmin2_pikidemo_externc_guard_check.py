"""Fail-closed checker for the pikidemo.h extern-C guard repair (#776).

Verifies that `Jac_NoteDemoSkipped` is declared INSIDE the extern-C guards
(BEGIN_SCOPE_EXTERN_C ... END_SCOPE_EXTERN_C) so C++ callers reference the
unmangled symbol defined in src/jaudio/pikidemo.c. A declaration after
END_SCOPE_EXTERN_C reproduces the proven final-link failure (566/566 TUs
compile; link fails on undefined Jac_NoteDemoSkipped).
"""
from __future__ import annotations

import re
from pathlib import Path

SYMBOL = "Jac_NoteDemoSkipped"
BEGIN_GUARD = "BEGIN_SCOPE_EXTERN_C"
END_GUARD = "END_SCOPE_EXTERN_C"


class GuardError(ValueError):
    """The header fails the extern-C guard check."""


def check_header(header_text):
    """Verify the decl sits inside the extern-C guards exactly once.

    Returns {"guarded": True, "decl_line": n}. Raises GuardError naming the
    exact defect otherwise (unguarded, missing, duplicated, unbalanced).
    """
    if not isinstance(header_text, str) or not header_text.strip():
        raise GuardError("header text is missing or empty")
    lines = header_text.splitlines()
    begin = next((i for i, line in enumerate(lines) if BEGIN_GUARD in line), None)
    end = next((i for i, line in enumerate(lines) if END_GUARD in line), None)
    if begin is None or end is None or end <= begin:
        raise GuardError("extern-C guards unbalanced or missing")
    pattern = re.compile(r"\bvoid\s+" + re.escape(SYMBOL) + r"\s*\(\s*void\s*\)\s*;")
    hits = [i for i in range(begin + 1, end) if pattern.search(lines[i])]
    if not hits:
        outside = [i for i, line in enumerate(lines)
                   if pattern.search(line) and not (begin < i < end)]
        if outside:
            raise GuardError(
                f"{SYMBOL} declared outside extern-C guards (line {outside[0] + 1}); "
                "C++ callers mangle the ref while pikidemo.c defines it unmangled")
        raise GuardError(f"{SYMBOL} declaration missing")
    if len(hits) > 1:
        raise GuardError(f"{SYMBOL} declared {len(hits)} times (no stub duplication allowed)")
    return {"guarded": True, "decl_line": hits[0] + 1}


def check_definition(source_text):
    """Verify the unmangled C definition exists in pikidemo.c (read-only)."""
    if not isinstance(source_text, str) or not source_text.strip():
        raise GuardError("source text is missing or empty")
    pattern = re.compile(r"\bvoid\s+" + re.escape(SYMBOL) + r"\s*\(\s*void\s*\)\s*\{")
    hits = [i for i, line in enumerate(source_text.splitlines())
            if pattern.search(line)]
    if not hits:
        raise GuardError(f"{SYMBOL} definition missing from pikidemo.c")
    return {"defined": True, "def_line": hits[0] + 1}


def check_pair(header_text, source_text):
    """Verify the guarded decl + C definition pair agrees."""
    header = check_header(header_text)
    source = check_definition(source_text)
    return {"guarded": header["guarded"], "decl_line": header["decl_line"],
            "defined": source["defined"], "def_line": source["def_line"]}


def check_files(header_path, source_path):
    """Read both files and verify the pair; paths recorded by the caller."""
    header_text = Path(header_path).read_text(encoding="utf-8", errors="replace")
    source_text = Path(source_path).read_bytes().decode("utf-8", errors="replace")
    return check_pair(header_text, source_text)
