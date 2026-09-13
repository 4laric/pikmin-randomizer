from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from scripts.test_pikmin2_settings_native import settings_evidence,drift_evidence,run_test


class SettingsRuntimeEvidenceTests(unittest.TestCase):
    def test_real_menu_and_single_closed_confirmation_required(self):
        lines=['P2_SETTINGS_REAL_MENU_OPEN','P2_SETTINGS_F6_SUPPRESSED dialogs=0 transfer=0',
               'P2_SETTINGS_REAL_MENU_CLOSED','P2_SETTINGS_CLOSED_CONFIRM','P2_MANUAL_ENTRANCE_HANDOFF']
        evidence=settings_evidence('\n'.join(lines))
        self.assertTrue(evidence['closed_f6_transferred']);self.assertEqual(evidence['open_f6_dialogs'],0)
        for bad in ('\n'.join(lines[1:]),'\n'.join(reversed(lines)), '\n'.join(lines+['P2_SETTINGS_CLOSED_CONFIRM'])):
            with self.subTest(bad=bad),self.assertRaises(ValueError):settings_evidence(bad)

    def test_drift_preserves_fixed_windows_and_reports_failure_sized_distance(self):
        text='\n'.join(f'P2_DRIFT frame={frame} position={x},80,1160 velocity=0,0,0 ground=80'
                       for frame,x in [(1,-200),(30,-199.5),(60,-199),(90,-198.5)])
        rows=drift_evidence(text,[-200,80,1160])
        self.assertEqual([r['frame'] for r in rows],[1,30,60,90])
        self.assertEqual(rows[-1]['distance_from_snapshot'],1.5)
        # No tolerance is silently increased to turn the90-frame observation into a pass.
        self.assertGreater(rows[-1]['distance_from_snapshot'],1.)
        with self.assertRaises(ValueError):drift_evidence(text.replace('frame=90','frame=89'),[-200,80,1160])
        with self.assertRaises(ValueError):drift_evidence(text.replace('position=-198.5','position=nan'),[-200,80,1160])

    def test_existing_output_refused_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):run_test(SimpleNamespace(output=Path(d)))


if __name__=='__main__':unittest.main()
