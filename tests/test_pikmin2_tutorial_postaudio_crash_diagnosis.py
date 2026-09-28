"""Focused fail-closed tests for the post-audio crash diagnosis (#750).

The adapter loads by path (no package init owned). Positive tests pin the
real 23-line crash signature; negative tests prove misclassified inputs
(loader failure, healthy boot, empty log, wrong exit) are rejected, and that
wrong causes do not validate. No runtime, no ADMIT.
"""
import copy
import importlib.util
import unittest
from pathlib import Path


def _load_adapter():
    path = (Path(__file__).resolve().parents[1] / "experimental" /
            "pikmin2_tutorial_postaudio_crash_diagnosis.py")
    spec = importlib.util.spec_from_file_location("postaudio_diag", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ADAPTER = _load_adapter()

CRASH_TAIL = "\n".join(
    ["[PC Port] Target refresh rate: 60.00 Hz",
     "[jaudio-bank] BX ready: 18/22 WSYS, 19/22 IBNK; 882 waves",
     "[jaudio] NextOS DSP, SDL2 S16 stereo 32000 Hz"])


def _crash_log(extra=()):
    lines = (["boot %d" % i for i in range(20)] + [CRASH_TAIL]
             if False else ["line %02d" % i for i in range(21)])
    lines.append("[jaudio-bank] BX ready: 18/22 WSYS, 19/22 IBNK; 882 waves")
    lines.append("[jaudio] NextOS DSP, SDL2 S16 stereo 32000 Hz")
    lines.extend(extra)
    return "\n".join(lines) + "\n"


class CrashSignatureTests(unittest.TestCase):
    def test_real_signature_classifies(self):
        facts = ADAPTER.log_facts(_crash_log(), 3221225477)
        self.assertEqual(facts["lines"], 23)
        self.assertTrue(facts["ends_after_dsp"])
        self.assertTrue(facts["has_bank_ready"])
        self.assertEqual(facts["dvd_attempts"], 0)
        self.assertFalse(facts["has_fps"])
        self.assertFalse(facts["has_fixture_markers"])
        verdict = ADAPTER.classify_crash(facts)
        self.assertTrue(verdict["matches_issue_750"])
        self.assertEqual(verdict["signature"],
                         "post-audio-pre-file-io-access-violation")

    def test_loader_failure_distinguished(self):
        facts = ADAPTER.log_facts("", 3221225781) if False else None
        with self.assertRaises(ADAPTER.DiagnosisError):
            ADAPTER.log_facts("", 3221225781)
        verdict = ADAPTER.classify_crash({
            "lines": 0, "ends_after_dsp": False, "has_bank_ready": False,
            "dvd_attempts": 0, "has_fps": False, "has_fixture_markers": False,
            "exit_code": 3221225781})
        self.assertFalse(verdict["matches_issue_750"])
        self.assertEqual(verdict["signature"], "loader-stage-dll-missing")

    def test_healthy_boot_rejected(self):
        facts = ADAPTER.log_facts(_crash_log(["[PC Port] FPS: 60"]), 0)
        with self.assertRaises(ADAPTER.DiagnosisError):
            ADAPTER.classify_crash(facts)

    def test_dvd_activity_rejected(self):
        text = _crash_log(['[PC Port] DVDOpen("x") -> OK, size = 1'])
        with self.assertRaises(ADAPTER.DiagnosisError):
            ADAPTER.classify_crash(ADAPTER.log_facts(text, 3221225477))

    def test_fixture_markers_rejected(self):
        text = _crash_log(["P2_TUTORIAL_P1_WAIT frames=600"])
        with self.assertRaises(ADAPTER.DiagnosisError):
            ADAPTER.classify_crash(ADAPTER.log_facts(text, 3221225477))

    def test_empty_log_rejected(self):
        with self.assertRaises(ADAPTER.DiagnosisError):
            ADAPTER.log_facts("", 3221225477)
        with self.assertRaises(ADAPTER.DiagnosisError):
            ADAPTER.classify_crash({})

    def test_packet_names_pins_and_downstream(self):
        packet = ADAPTER.packet(
            ADAPTER.log_facts(_crash_log(), 3221225477),
            ADAPTER.classify_crash(
                ADAPTER.log_facts(_crash_log(), 3221225477)))
        self.assertEqual(packet["issue"], 750)
        self.assertEqual(packet["downstream"]["issue"], 148)
        self.assertEqual(packet["pins"]["native"],
                         "13b4262c78611b6a0279aa65ea5785b614ecd6cf")
        self.assertFalse(packet["admit"])
        self.assertRegex(packet["packet_sha256"], r"[0-9a-f]{64}")

    def test_packet_rejects_non_matching_verdict(self):
        facts = {"lines": 0, "ends_after_dsp": False, "has_bank_ready": False,
                 "dvd_attempts": 0, "has_fps": False,
                 "has_fixture_markers": False, "exit_code": 3221225781}
        with self.assertRaises(ADAPTER.DiagnosisError):
            ADAPTER.packet(facts, ADAPTER.classify_crash(facts))

    def test_suspects_ranked_with_files(self):
        suspects = ADAPTER.suspects()
        self.assertEqual([s["rank"] for s in suspects], [1, 2, 3, 4])
        for suspect in suspects:
            self.assertTrue(suspect["files"])
            self.assertTrue(suspect["reason"])

    def test_cli_writes_packet(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "headed-run.log"
            src.write_text(_crash_log(), encoding="utf-8")
            out = Path(directory) / "packet.json"
            self.assertEqual(
                ADAPTER.main(["--log", str(src), "--exit-code", "3221225477",
                              "--output", str(out)]), 0)
            import json
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(packet["verdict"]["matches_issue_750"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
