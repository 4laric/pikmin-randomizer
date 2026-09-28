"""Fail-closed tests for the retail cave generation path discovery adapter."""
import os
import subprocess
import sys
import tempfile

import pytest

ADAPTER = os.path.join(
    os.path.dirname(__file__), "..", "experimental",
    "pikmin2_retail_cave_generation_path_discovery.py")
ADAPTER = os.path.normpath(ADAPTER)
PY = sys.executable


def run_tree(root):
    return subprocess.run(
        [PY, ADAPTER, root], capture_output=True, text=True, timeout=120)


def make_tree(files):
    tmp = tempfile.mkdtemp(prefix="retail-cave-path-")
    for rel, text in files.items():
        full = os.path.join(tmp, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
    return tmp


def test_verified_absence_on_tree_without_retail_symbols():
    root = make_tree({
        "pc_port/pc_p2_cave_generate.h": (
            "// sidecar-driven randomizer generation\n"
            "void pc_p2_cave_generate_run();\n"),
        "pc_port/pc_randomizer.cpp": "int generatorId = 0;\n",
        "tools/p2_cave_guarded_boot_fixture.cpp": "int main() { return 0; }\n",
    })
    proc = run_tree(root)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "P2_RETAIL_CAVE_PATH_ABSENT retail-gen" in out
    assert "P2_RETAIL_CAVE_PATH_ABSENT cave-save" in out
    assert "P2_RETAIL_CAVE_PATH_VERDICT absence-verified" in out
    assert "P2_RETAIL_CAVE_PATH_FOUND" not in out
    assert "P2_RETAIL_CAVE_FOOTHOLD pc_port/pc_p2_cave_generate.h" in out


def test_randomizer_sidecar_markers_are_not_retail_paths():
    root = make_tree({
        "pc_port/pc_p2_cave.cpp": (
            "P2_CAVE_GENERATE_1\nP2_CAVE_READY\n"
            "Saves at floor boundaries\n"),
    })
    proc = run_tree(root)
    assert proc.returncode == 0, proc.stderr
    assert "P2_RETAIL_CAVE_PATH_VERDICT absence-verified" in proc.stdout
    assert "P2_RETAIL_CAVE_PATH_FOUND" not in proc.stdout


def test_found_paths_when_retail_symbols_present():
    root = make_tree({
        "pc_port/pc_p2_cave.cpp": "struct CaveInfo { int floors; };\n",
        "pc_port/ogSave.cpp": "void writeSave() {}\n",
    })
    proc = run_tree(root)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "P2_RETAIL_CAVE_PATH_FOUND retail-gen pc_port/pc_p2_cave.cpp CaveInfo" in out
    assert "P2_RETAIL_CAVE_PATH_FOUND cave-save pc_port/ogSave.cpp writeSave" in out
    assert "P2_RETAIL_CAVE_PATH_VERDICT paths-found" in out


def test_refused_missing_root():
    proc = run_tree(os.path.join(tempfile.gettempdir(), "no-such-retail-tree-xyz"))
    assert proc.returncode == 2
    assert "P2_RETAIL_CAVE_PATH_REFUSED reason=missing-root" in proc.stdout


def test_refused_no_search_dirs():
    root = make_tree({"docs/note.txt": "nothing to scan\n"})
    proc = run_tree(root)
    assert proc.returncode == 2
    assert "P2_RETAIL_CAVE_PATH_REFUSED reason=no-search-dirs" in proc.stdout


def test_refused_usage_without_arg():
    proc = subprocess.run(
        [PY, ADAPTER], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2
    assert "P2_RETAIL_CAVE_PATH_REFUSED reason=usage" in proc.stdout


def test_non_source_files_are_ignored():
    root = make_tree({
        "pc_port/CaveInfo.txt": "CaveInfo FloorInfo RandomMapCreator\n",
        "pc_port/real.cpp": "int x = 0;\n",
    })
    proc = run_tree(root)
    assert proc.returncode == 0, proc.stderr
    assert "P2_RETAIL_CAVE_PATH_VERDICT absence-verified" in proc.stdout
