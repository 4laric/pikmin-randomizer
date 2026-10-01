"""Retail cave generation + cave-save engine path discovery (issue #771).

Read-only scanner over a native source tree (pc_port + tools). Reports
whether RETAIL engine cave-generation / cave-save symbols exist, or
verifies their absence and lists the nearest randomizer-side footholds.

Markers (stdout, one per line):
  P2_RETAIL_CAVE_PATH_FOUND <set> <relpath> <symbol>
  P2_RETAIL_CAVE_PATH_ABSENT <set>
  P2_RETAIL_CAVE_FOOTHOLD <relpath>
  P2_RETAIL_CAVE_PATH_REFUSED reason=<code>
  P2_RETAIL_CAVE_PATH_VERDICT <absence-verified|paths-found>

Exit 0 when the tree was scanned (even on absence); exit 2 on refusal.
Never writes to the scanned tree. Stdlib only.
"""
import os
import re
import sys

SEARCH_DIRS = ("pc_port", "tools")
SOURCE_EXTS = (".cpp", ".h", ".hpp", ".c", ".inc")

RETAIL_GEN_SYMBOLS = (
    "CaveInfo",
    "FloorInfo",
    "RandomMapCreator",
    "TileMap",
    "Cave::",
    "Oeoe::",
    "ogCave",
)

SAVE_SYMBOLS = (
    "ogSave",
    "SaveData",
    "writeSave",
    "saveFile",
    "SaveMgr",
    "saveMgr",
    "CaveSave",
    "saveCave",
)

FOOTHOLD_FILES = (
    "pc_p2_cave_generate.h",
    "pc_p2_cave_generate.cpp",
    "pc_p2_cave.cpp",
    "pc_p2_cave.h",
    "pc_p2_cave_anchor.h",
    "pc_p2_cave_nav_diagnostics.h",
    "pc_randomizer.cpp",
    "pc_randomizer.h",
    "pc_randomizer_probe.cpp",
    "p2_cave_guarded_boot_fixture.cpp",
    "preview_p2_cave.inc",
    "test_p2_cave_anchor.cpp",
)


def _compile(symbols):
    return [(s, re.compile(re.escape(s))) for s in symbols]


GEN_RES = _compile(RETAIL_GEN_SYMBOLS)
SAVE_RES = _compile(SAVE_SYMBOLS)


def scan_tree(native_root):
    """Return (markers, refused_reason). markers is a list of strings."""
    markers = []
    if not isinstance(native_root, str) or not native_root:
        return markers, "bad-root"
    if not os.path.exists(native_root):
        return markers, "missing-root"
    if not os.path.isdir(native_root):
        return markers, "not-a-dir"
    found_gen = []
    found_save = []
    footholds = []
    searched = 0
    for sub in SEARCH_DIRS:
        d = os.path.join(native_root, sub)
        if not os.path.isdir(d):
            continue
        for dirpath, _dirnames, filenames in os.walk(d):
            for fn in sorted(filenames):
                if not fn.endswith(SOURCE_EXTS):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, native_root).replace(os.sep, "/")
                if fn in FOOTHOLD_FILES and rel not in footholds:
                    footholds.append(rel)
                try:
                    with open(full, "r", encoding="utf-8", errors="strict") as fh:
                        text = fh.read()
                except (OSError, UnicodeError):
                    return markers, "unreadable-input"
                searched += 1
                for sym, rx in GEN_RES:
                    if rx.search(text):
                        found_gen.append((rel, sym))
                        markers.append(
                            "P2_RETAIL_CAVE_PATH_FOUND retail-gen %s %s" % (rel, sym))
                        break
                for sym, rx in SAVE_RES:
                    if rx.search(text):
                        found_save.append((rel, sym))
                        markers.append(
                            "P2_RETAIL_CAVE_PATH_FOUND cave-save %s %s" % (rel, sym))
                        break
    if searched == 0:
        return markers, "no-search-dirs"
    if not found_gen:
        markers.append("P2_RETAIL_CAVE_PATH_ABSENT retail-gen")
    if not found_save:
        markers.append("P2_RETAIL_CAVE_PATH_ABSENT cave-save")
    for rel in footholds:
        markers.append("P2_RETAIL_CAVE_FOOTHOLD %s" % rel)
    verdict = "paths-found" if (found_gen or found_save) else "absence-verified"
    markers.append("P2_RETAIL_CAVE_PATH_VERDICT %s" % verdict)
    return markers, None


def main(argv):
    if len(argv) != 2:
        print("P2_RETAIL_CAVE_PATH_REFUSED reason=usage")
        return 2
    markers, refused = scan_tree(argv[1])
    for m in markers:
        print(m)
    if refused is not None:
        print("P2_RETAIL_CAVE_PATH_REFUSED reason=%s" % refused)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
