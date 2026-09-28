import os
import unittest

from tests import test_pikmin2_controller as fixtures
from workflow.activity_health import snapshot


class ActivityHealthTests(unittest.TestCase):
    def test_cleanup_and_heartbeat_do_not_reset_activity_age(self):
        fixture = fixtures.ControllerTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        launch = fixture.plan()
        fixture.controller.dispatch(launch)
        directory = fixture.controller.launch_directory(launch['id'])
        events = directory/'events.jsonl'
        events.write_text('')
        os.utime(events, (1000, 1000))
        (directory/'stderr.log').write_text(
            'timestamp=1970-01-01T00:16:40Z level=INFO run=a message=stream\n'
            'timestamp=1970-01-01T00:33:19Z level=INFO run=a message=cleanup prune=7.days\n')
        fixture.now = 2000
        fixture.reg.heartbeat('consumer', 2)
        activity = snapshot(fixture.controller)['consumer']
        self.assertEqual(activity['status'], 'stalled / inspect')
        self.assertEqual(activity['activity_age_seconds'], 1000)
        self.assertEqual(activity['process'], 'alive')

    def test_only_schema_insertion_preserves_pinned_config(self):
        import hashlib
        import tempfile
        from pathlib import Path
        from workflow.managed_config import pinned_config_matches
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'config.json'
            original = b'{\r\n "permission": {"task":"deny"}\r\n}'
            expected = hashlib.sha256(original).hexdigest()
            schema = b'{\n  "$schema": "https://opencode.ai/config.json",'
            path.write_bytes(schema + original[1:])
            self.assertTrue(pinned_config_matches(path, expected))
            path.write_bytes((schema + original[1:]).replace(b'deny', b'allow'))
            self.assertFalse(pinned_config_matches(path, expected))

    def test_integrator_standby_report_is_not_a_stuck_handoff(self):
        from workflow.analytics import throughput_metrics
        state = dict(lanes={'owner': dict(state='review_ready', handoff_at=1),
                            'review': dict(state='review_ready', handoff_at=90)},
                     throughput={'workstreams': {'content': {'owner_lane': 'owner'}}})
        metrics = throughput_metrics(state, 100)
        self.assertEqual(metrics['oldest_handoff']['lane'], 'review')
        self.assertEqual(metrics['parked_integration_reports'], ['owner'])

    def test_repository_permission_boundary_rejects_siblings_and_traversal(self):
        from pathlib import Path
        from workflow.managed_config import permission_path_allowed
        root = Path.cwd().resolve()
        rules = [root.as_posix() + '/**']
        self.assertTrue(permission_path_allowed(root, rules))
        self.assertTrue(permission_path_allowed(root/'output'/'private-worktree', rules))
        self.assertFalse(permission_path_allowed(root.parent/(root.name + '-other'), rules))
        self.assertFalse(permission_path_allowed(root/'..'/'external', rules))
