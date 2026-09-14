import contextlib
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experimental import pikmin2_generated_session_acceptance as gs
from experimental import pikmin2_qa_matrix as qa

COHORT = (79, 15)


@contextlib.contextmanager
def reviewed_cohort():
    """Inject a reviewed cohort for the *test* only; the product path is unchanged.

    Tests use this to exercise the success branch while the live lane 02
    admission set is empty. A run made under this patch is never classified as
    natural evidence.
    """
    from experimental import pikmin2_seed_bridge as bridge
    original = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: list(COHORT)
    try:
        yield
    finally:
        bridge.admitted_ids = original


def placement_document():
    """The same minimal lane 04 document the wiring probe uses."""
    def slot(uid, label):
        return {"uid": uid, "label": label, "stage": 1, "terrain": "ground", "radius": 300.0,
                "evidence": {"xyz": True, "terrain": True, "route": True}}
    return {
        "schema": "p2-placement-v1",
        "slots": [slot(401, "sokkuri-slot"), slot(402, "armor-slot")],
        "profiles": [
            {"identity": "Sokkuri", "terrains": ["ground"], "accepted_gates": ["xyz"]},
            {"identity": "Armor", "terrains": ["ground"], "accepted_gates": ["xyz"]},
        ],
    }


def make_exe(tmp, data=b"pinned-binary"):
    path = Path(tmp) / "nectar.exe"
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def pin_for(tmp, root="a" * 40, native="f" * 40):
    exe, sha = make_exe(tmp)
    return gs.Pin(root_commit=root, native_commit=native,
                  executable=str(exe), executable_sha256=sha)


class PinTests(unittest.TestCase):
    def test_verify_success_returns_resolved_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            pin = pin_for(tmp)
            verified = pin.verify()
            self.assertEqual(verified["root_commit"], "a" * 40)
            self.assertEqual(verified["native_commit"], "f" * 40)
            self.assertEqual(verified["executable_sha256"], pin.executable_sha256)

    def test_verify_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            pin = pin_for(tmp)
            wrong = gs.Pin(root_commit=pin.root_commit, native_commit=pin.native_commit,
                           executable=pin.executable, executable_sha256="0" * 64)
            with self.assertRaises(gs.PinMismatch):
                wrong.verify()

    def test_verify_rejects_missing_commit_and_missing_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe, sha = make_exe(tmp)
            with self.assertRaises(gs.PinMismatch):
                gs.Pin(root_commit="", native_commit="f" * 40, executable=str(exe),
                       executable_sha256=sha).verify()
            with self.assertRaises(gs.PinMismatch):
                gs.Pin(root_commit="a" * 40, native_commit="f" * 40,
                       executable=str(Path(tmp) / "nope.exe"), executable_sha256=sha).verify()

    def test_round_trip_dict(self):
        pin = gs.Pin(root_commit="a", native_commit="b", executable="c",
                     executable_sha256="d", assets="e")
        self.assertEqual(gs.Pin.from_dict(pin.as_dict()), pin)


class GenerationTests(unittest.TestCase):
    def test_real_admission_set_blocks_generation(self):
        # The live lane 02 admission set is empty; the harness must not inject one.
        with self.assertRaises(gs.AcceptanceBlocked) as caught:
            gs.generate_pinned_session("p2-native", placement_document())
        self.assertEqual(caught.exception.stage, "generate")
        self.assertIn("lane 02", caught.exception.dependency)

    def test_missing_placement_document_blocks(self):
        with self.assertRaises(gs.AcceptanceBlocked) as caught:
            gs.generate_pinned_session("p2-native", None)
        self.assertIn("lane 04", caught.exception.dependency)

    def test_generation_succeeds_with_a_reviewed_cohort(self):
        # Tests may inject a reviewed cohort to exercise the success path; the
        # product code is unchanged and the run is never classified as natural.
        with reviewed_cohort():
            manifest = gs.generate_pinned_session("p2-native", placement_document())
        bindings = manifest["p2_layout"]["bindings"]
        self.assertEqual(sorted(b["source_id"] for b in bindings), [15, 79])
        self.assertIn("p2-enemy-bridge-v1", manifest["capabilities"])


class PrepareTests(unittest.TestCase):
    def _manifest(self):
        return gs.generate_pinned_session("p2-native", placement_document())

    def _content(self, tmp, identities=(79, 15)):
        source = Path(tmp) / "source"
        source.mkdir(parents=True, exist_ok=True)
        entries = []
        for index in range(2):
            data = f"blob-{index}".encode()
            name = f"asset{index}.bin"
            (source / name).write_bytes(data)
            entries.append(dict(id=f"asset{index}", kind="model", source=f"source/{name}",
                                destination=f"tree/{name}",
                                sha256=hashlib.sha256(data).hexdigest()))
        from experimental.pikmin2_staging import build_manifest
        return build_manifest(1, entries, notes="synthetic", identities=list(identities))

    def test_prepare_builds_real_bootstrap_and_checks_content(self):
        with tempfile.TemporaryDirectory() as tmp, reviewed_cohort():
            pin = pin_for(tmp)
            prepared = gs.prepare_session(pin, self._manifest(), Path(tmp) / "sess",
                                          content_manifest=self._content(tmp),
                                          content_base=Path(tmp))
            bootstrap = Path(prepared["bootstrap"]).read_text(encoding="ascii")
            self.assertIn("ENEMY_P2", bootstrap)
            self.assertEqual(prepared["identities"], [79, 15])
            self.assertTrue(prepared["content"]["ok"])
            self.assertIn("randomizer", prepared["launch"])
            self.assertTrue(Path(prepared["manifest"]).is_file())

    def test_prepare_rejects_content_missing_a_bound_identity(self):
        with tempfile.TemporaryDirectory() as tmp, reviewed_cohort():
            pin = pin_for(tmp)
            with self.assertRaises(gs.AcceptanceBlocked) as caught:
                gs.prepare_session(pin, self._manifest(), Path(tmp) / "sess",
                                   content_manifest=self._content(tmp, identities=(79,)))
            self.assertEqual(caught.exception.stage, "install")

    def test_prepare_refuses_wrong_pin_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp, reviewed_cohort():
            pin = gs.Pin(root_commit="a" * 40, native_commit="f" * 40,
                         executable=str(Path(tmp) / "nope.exe"), executable_sha256="0" * 64)
            with self.assertRaises(gs.PinMismatch):
                gs.prepare_session(pin, self._manifest(), Path(tmp) / "sess")


class ObserveTests(unittest.TestCase):
    def test_all_markers_present_pass(self):
        observations = gs.observe_log(
            "PIKMIN_CONTENT_STAGED ...\nP2_ENEMY_READY source_id=79\n",
            {"install": [gs.INSTALL_WITNESS], "natural_fight": ["P2_ENEMY_READY"]})
        self.assertEqual(observations["install"]["status"], qa.PASS)
        self.assertEqual(observations["natural_fight"]["status"], qa.PASS)

    def test_missing_marker_fails_with_names(self):
        observations = gs.observe_log("nothing here", {"natural_fight": ["P2_ENEMY_READY"]})
        self.assertEqual(observations["natural_fight"]["status"], qa.FAIL)
        self.assertIn("P2_ENEMY_READY", observations["natural_fight"]["missing"])

    def test_stage_without_declared_markers_is_blocked(self):
        observations = gs.observe_log("anything", {"install": [gs.INSTALL_WITNESS]})
        self.assertEqual(observations["reward"]["status"], qa.BLOCKED)
        self.assertIn("no declared witness", observations["reward"]["reason"])

    def test_generate_stage_is_not_log_derived(self):
        observations = gs.observe_log("anything", {})
        self.assertNotIn("generate", observations)


class RecordTests(unittest.TestCase):
    def test_natural_requires_a_verified_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = gs.Pin(root_commit="a" * 40, native_commit="f" * 40,
                         executable=str(Path(tmp) / "nope.exe"), executable_sha256="0" * 64)
            with self.assertRaises(gs.PinMismatch):
                gs.build_records(bad, {"natural_fight": {"status": qa.PASS, "reason": "x"}},
                                 kind=qa.KIND_NATURAL, evidence_paths=["e.json"])

    def test_build_records_emits_valid_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            pin = pin_for(tmp)
            stage_results = {
                "generate": {"status": qa.PASS, "reason": "real product generation"},
                "install": {"status": qa.PASS, "reason": "staged"},
                "natural_fight": {"status": qa.FAIL, "reason": "missing marker"},
            }
            records = gs.build_records(pin, stage_results, kind=qa.KIND_FIXTURE,
                                       scenario="baseline_cohort",
                                       evidence_paths=[Path(tmp) / "prepared.json"])
            self.assertEqual([r["status"] for r in records],
                             [qa.PASS, qa.PASS, qa.FAIL])
            for record in records:
                self.assertEqual(qa.validate_record(record), [])

    def test_fixture_evidence_cannot_satisfy_a_natural_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            pin = pin_for(tmp)
            records = gs.build_records(
                pin, {"natural_fight": {"status": qa.PASS, "reason": "x"}},
                kind=qa.KIND_FIXTURE, scenario="baseline_cohort", evidence_paths=["e.json"])
            cell = qa.evaluate_cell(records, "natural_fight", "baseline_cohort")
            self.assertEqual(cell["status"], qa.BLOCKED)

    def test_rejects_unknown_kind_and_empty_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            pin = pin_for(tmp)
            with self.assertRaises(gs.AcceptanceError):
                gs.build_records(pin, {}, kind="magic", evidence_paths=["e.json"])
            with self.assertRaises(gs.AcceptanceError):
                gs.build_records(pin, {}, kind=qa.KIND_FIXTURE, evidence_paths=[])


class PlanTests(unittest.TestCase):
    def test_plan_reports_blocked_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            pin = pin_for(tmp)
            report = gs.plan_report(pin, "p2-native", placement_document())
            self.assertEqual(report["status"], qa.BLOCKED)
            self.assertIn("lane 02", report["blocked_by"])

    def test_plan_reports_bad_pin(self):
        report = gs.plan_report(gs.Pin(root_commit="a", native_commit="b"), "s", {})
        self.assertEqual(report["status"], qa.BLOCKED)
        self.assertIn("pin", report["blocked_by"])


class CliTests(unittest.TestCase):
    def test_verify_pin_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            pin = pin_for(tmp)
            self.assertEqual(gs.main(["verify-pin", "--root-commit", pin.root_commit,
                                      "--native-commit", pin.native_commit,
                                      "--executable", pin.executable,
                                      "--executable-sha256", pin.executable_sha256]), 0)
            self.assertEqual(gs.main(["verify-pin", "--root-commit", pin.root_commit,
                                      "--native-commit", pin.native_commit,
                                      "--executable", pin.executable,
                                      "--executable-sha256", "0" * 64]), 1)

    def test_observe_cli_writes_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "native.log"
            log.write_text("PIKMIN_CONTENT_STAGED ok\n", encoding="utf-8")
            markers = Path(tmp) / "markers.json"
            markers.write_text(json.dumps({"install": [gs.INSTALL_WITNESS]}), encoding="utf-8")
            out = Path(tmp) / "obs.json"
            self.assertEqual(gs.main(["observe", "--log", str(log), "--markers", str(markers),
                                      "--output", str(out)]), 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["install"]["status"], qa.PASS)


if __name__ == "__main__":
    unittest.main()
