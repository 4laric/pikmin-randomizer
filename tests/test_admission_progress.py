import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from workflow.admission_progress import snapshot
from workflow.dashboard import render_dashboard


class AdmissionProgressTests(unittest.TestCase):
    def test_validated_counts_render_above_operational_cards_and_escape_names(self):
        data = dict(admitted=11, total=64, names=['<Monster>'], status='observed')
        with tempfile.TemporaryDirectory() as root, patch('workflow.admission_progress.subprocess.run',
                return_value=subprocess.CompletedProcess([], 0, json.dumps(data), '')):
            result = snapshot(Path(root), {'source': 'maintained'})
        html = render_dashboard({'monster_admission': result})
        self.assertIn('11<span> / 64</span>', html)
        self.assertIn('value="11" max="64"', html)
        self.assertIn('&lt;Monster&gt;', html)
        self.assertLess(html.index('Monster families admitted'), html.index('Integrated slices / hour'))

    def test_failed_contract_is_unavailable_not_zero(self):
        with tempfile.TemporaryDirectory() as root, patch('workflow.admission_progress.subprocess.run',
                return_value=subprocess.CompletedProcess([], 1, '', 'invalid ledger')):
            result = snapshot(Path(root), {'source': 'maintained'})
        self.assertIsNone(result['admitted'])
        html = render_dashboard({'monster_admission': result})
        self.assertIn('Admission records unavailable', html)
        self.assertNotIn('value="0"', html)

    def test_invalid_counts_fail_closed(self):
        for data in [dict(admitted=65,total=64), dict(admitted=-1,total=64), dict(admitted=True,total=64)]:
            with tempfile.TemporaryDirectory() as root, patch('workflow.admission_progress.subprocess.run',
                    return_value=subprocess.CompletedProcess([], 0, json.dumps(data), '')):
                self.assertIsNone(snapshot(Path(root), {'source':'maintained'})['admitted'])
