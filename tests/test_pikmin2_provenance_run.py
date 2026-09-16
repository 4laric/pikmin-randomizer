"""Focused tests for the production-run provenance recorder (#615).

Synthetic git trees, build dirs, arenas and logs under tmp_path; no native
build, no gameplay run. One read-only self-check exercises real prior run
artifacts without modifying them (skipped when absent).
"""
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path


def _load():
    path = (Path(__file__).resolve().parents[1] / "scripts"
            / "pikmin2_provenance_run.py")
    spec = importlib.util.spec_from_file_location("provenance_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()
REAL_LOG = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
                "enemy-sokkuri79-receipt/runs/run1/"
                "b643942fa892401b879fc70ce3f0da4b/capture/native.log")


def git(*args, cwd):
    result = subprocess.run(["git", "-C", str(cwd)] + list(args),
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def make_tree(root, dirty=False):
    root.mkdir(parents=True, exist_ok=True)
    (root / "a.txt").write_text("v1\n")
    git("init", "-q", cwd=root)
    git("config", "user.email", "t@t", cwd=root)
    git("config", "user.name", "t", cwd=root)
    git("add", "a.txt", cwd=root)
    git("commit", "-qm", "one", cwd=root)
    head = git("rev-parse", "HEAD", cwd=root)
    if dirty:
        (root / "a.txt").write_text("v2\n")
    return head


def make_inputs(root, tree):
    build = root / "build"
    build.mkdir()
    exe = build / "run.exe"
    exe.write_bytes(b"\x7fEXE")
    arena = root / "arena"
    arena.mkdir()
    (arena / "arena.json").write_text('{"schema": 1}\n')
    (arena / "receipt.txt").write_text("new=1\n")
    (arena / "assets").mkdir()
    (arena / "assets" / "big.bin").write_bytes(b"x" * 999)
    log = root / "native.log"
    log.write_text("line1\nline2\n")
    return dict(native=tree, build_dir=build, exe=exe, arena=arena, log=log)


class RecordTests(unittest.TestCase):
    def test_happy_path_round_trips_self_check(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = make_tree(root / "native")
            kw = make_inputs(root, root / "native")
            rec = M.record(expected_head=head, **kw)
            self.assertTrue(M.self_check(rec))
            self.assertEqual(rec["native"]["observed_head"], head)
            self.assertEqual(rec["native"]["dirty"], "")
            self.assertEqual(rec["arena"]["arena_json_sha256"],
                             rec["arena"]["files"]["arena.json"]["sha256"])
            self.assertIn("assets", rec["arena"]["subdirs"])
            self.assertNotIn("big.bin", json.dumps(rec["arena"]))
            self.assertEqual(rec["log"]["lines"], 2)

    def test_dirty_tree_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = make_tree(root / "native", dirty=True)
            kw = make_inputs(root, root / "native")
            with self.assertRaisesRegex(ValueError, "dirty"):
                M.record(expected_head=head, **kw)

    def test_wrong_head_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root / "native")
            kw = make_inputs(root, root / "native")
            with self.assertRaisesRegex(ValueError, "!="):
                M.record(expected_head="0" * 40, **kw)

    def test_missing_inputs_fail_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = make_tree(root / "native")
            kw = make_inputs(root, root / "native")
            for key in ("exe", "arena", "log"):
                bad = dict(kw, **{key: root / "nope"})
                with self.assertRaisesRegex(ValueError, "missing"):
                    M.record(expected_head=head, **bad)
            with self.assertRaisesRegex(ValueError, "missing|not a native"):
                M.record(expected_head=head, **dict(kw, native=root / "nope"))

    def test_cli_writes_json(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = make_tree(root / "native")
            kw = make_inputs(root, root / "native")
            out = root / "prov.json"
            code = M.main(["--native", str(kw["native"]), "--expected-head", head,
                           "--build-dir", str(kw["build_dir"]), "--exe", str(kw["exe"]),
                           "--arena", str(kw["arena"]), "--log", str(kw["log"]),
                           "--output", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(M.self_check(json.loads(out.read_text())))


class SelfCheckShapeTests(unittest.TestCase):
    def test_each_required_key_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = make_tree(root / "native")
            rec = M.record(expected_head=head, **make_inputs(root, root / "native"))
        import copy
        for drop in ("schema", "kind", "native", "log"):
            bad = copy.deepcopy(rec)
            bad.pop(drop)
            with self.assertRaises(ValueError):
                M.self_check(bad)
        bad = copy.deepcopy(rec)
        bad["native"]["dirty"] = " M x"
        with self.assertRaises(ValueError):
            M.self_check(bad)
        bad = copy.deepcopy(rec)
        bad["build"]["executable"]["sha256"] = "short"
        with self.assertRaises(ValueError):
            M.self_check(bad)
        with self.assertRaises(ValueError):
            M.self_check("not-a-dict")

    def test_read_only_real_prior_log(self):
        if not REAL_LOG.is_file():
            self.skipTest("prior run artifact absent")
        before = REAL_LOG.stat()
        digest = M.file_record(REAL_LOG, "run log")
        self.assertEqual(len(digest["sha256"]), 64)
        self.assertGreater(digest["lines"], 1000)
        after = REAL_LOG.stat()
        self.assertEqual((before.st_size, before.st_mtime_ns),
                         (after.st_size, after.st_mtime_ns))


if __name__ == "__main__":
    unittest.main()