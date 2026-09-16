"""Focused tests for the provenance adoption checker (#615)."""
import json
import unittest
from pathlib import Path

from experimental.pikmin2_provenance_adoption_check import (
    AdoptionError,
    certify,
    check_record,
    load_provenance,
    map_to_handoff_evidence,
    run_recorder,
)

OUT = Path(r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\provider-runtime-fixtures\prepared\provenance-adoption-output")
ARMOR_PROVENANCE = OUT / "armor15-provenance.json"
L62_PROVENANCE = OUT / "l62-provenance.json"
RECORDER_ROOT = Path(r"C:\Users\alari\pikmin-randomizer\output\p2-main-review")


def good_record():
    return {
        "schema": 1, "kind": "production-run-provenance",
        "native": {"observed_head": "a" * 40, "dirty": ""},
        "build": {"executable": {"path": "C:/x/fixture.exe",
                                 "sha256": "b" * 64, "size": 10}},
        "arena": {"directory": "C:/x/arena",
                  "files": {"arena.json": {"sha256": "c" * 64, "size": 5}}},
        "log": {"path": "C:/x/native.log", "sha256": "d" * 64,
                "size": 7, "lines": 3},
    }


class AdoptionCheckTests(unittest.TestCase):
    def test_good_record_loads_and_checks(self):
        record = good_record()
        findings = check_record(record, expected_head="a" * 40, dirty="",
                                exe_sha256="b" * 64, log_sha256="d" * 64)
        self.assertTrue(findings["complete"])
        mapping = map_to_handoff_evidence(record)
        self.assertEqual(mapping["exe"], ("C:/x/fixture.exe", "b" * 64))
        self.assertEqual(mapping["nativelog"], ("C:/x/native.log", "d" * 64))
        self.assertIn("arena:arena.json", mapping)

    def test_malformed_records_fail_closed(self):
        base = good_record()
        mutations = [
            dict(base, schema=2),
            dict(base, kind="other"),
            dict(base, native={"observed_head": "xyz", "dirty": ""}),
            dict(base, native={"observed_head": "a" * 40, "dirty": "M file"}),
            dict(base, build={"executable": {"path": "x", "sha256": "zzz", "size": 1}}),
            dict(base, log={"path": "x", "sha256": "d" * 64, "size": 1}),
            dict(base, arena={"directory": "x"}),
        ]
        for i, mutated in enumerate(mutations):
            with self.subTest(case=i), self.assertRaises(AdoptionError):
                check_shape(mutated)

    def test_mismatch_fails_closed(self):
        record = good_record()
        with self.assertRaises(AdoptionError):
            check_record(record, expected_head="f" * 40)
        with self.assertRaises(AdoptionError):
            check_record(record, exe_sha256="e" * 64)
        with self.assertRaises(AdoptionError):
            check_record(record, log_sha256="e" * 64)
        with self.assertRaises(AdoptionError):
            check_record(record, arena_dir="C:/other")

    def test_recorder_missing_script_fails_closed(self):
        with self.assertRaises(AdoptionError):
            run_recorder("C:/nonexistent-root", "n", "h", "b", "e", "a", "l", "o")

    def test_live_armor15_record(self):
        if not ARMOR_PROVENANCE.is_file():
            self.skipTest("live armor15 provenance not staged")
        record = load_provenance(ARMOR_PROVENANCE)
        findings = check_record(
            record, expected_head="0a32249ab40bbf424403437b7b6dec4ed0529323",
            exe_sha256="ae666fb4a9ec98027e278678ae29cd77f5fb21a5e3bc856bcf51c36515e974b5",
            log_sha256="8ccbb58b99e145577fae057e8452ccfd576763c8065fd8af80a00c52bb7cd1e8")
        self.assertTrue(findings["complete"])

    def test_live_l62_record(self):
        if not L62_PROVENANCE.is_file():
            self.skipTest("live l62 provenance not staged")
        record = load_provenance(L62_PROVENANCE)
        findings = check_record(
            record, expected_head="b024c88c8b5eaf7edbfe563948040f948b9d1af8",
            exe_sha256="7e4518583c77bfbdad5692a5146530011f6fba3efcd7c901518ec8d7081b0582",
            log_sha256="52d1ad8c05194a9fad841b8e976ee44070cd47170b049cbaab4c5df6d388e96c")
        self.assertTrue(findings["complete"])


def check_shape(record):
    """Shape gate used by the malformed-input tests (mirrors load checks)."""
    from experimental import pikmin2_provenance_adoption_check as checker
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as stream:
        json.dump(record, stream)
        path = stream.name
    try:
        return checker.load_provenance(path)
    finally:
        Path(path).unlink()


if __name__ == "__main__":
    unittest.main()
