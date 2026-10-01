import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from workflow.throughput_controller import publish_dashboard


class DashboardPublicationTests(unittest.TestCase):
    def test_transient_reader_lock_retries_atomic_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'throughput.html';temp=target.with_suffix('.tmp')
            target.write_text('old');temp.write_text('new')
            original=Path.replace;calls=[]
            def replace(path,destination):
                calls.append(1)
                if len(calls)<3:raise PermissionError('reader')
                return original(path,destination)
            with patch.object(Path,'replace',replace):
                self.assertTrue(publish_dashboard(temp,target,10,pause=lambda _:None))
            self.assertEqual(target.read_text(),'new')
            self.assertEqual(len(calls),3)

    def test_persistent_lock_preserves_previous_html_and_records_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'throughput.html';temp=target.with_suffix('.tmp')
            target.write_text('old');temp.write_text('new')
            original=Path.replace
            def replace(path,destination):
                if path==temp:raise PermissionError('reader')
                return original(path,destination)
            with patch.object(Path,'replace',replace):
                self.assertFalse(publish_dashboard(temp,target,10,pause=lambda _:None))
            self.assertEqual(target.read_text(),'old')
            self.assertEqual(json.loads((target.parent/'dashboard-publish-error.json').read_text())['status'],'retry_next_tick')
