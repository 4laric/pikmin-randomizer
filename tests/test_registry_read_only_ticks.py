"""Read-only controller ticks must inspect state without the exclusive writer lock.

Each of these ticks previously opened a full write transaction only to deep-copy a
snapshot, holding the exclusive registry writer for the whole load+copy+save cycle
(seconds on the live registry) while writing nothing.
"""
import unittest
from unittest.mock import patch

from tests import test_pikmin2_controller as controller_fixtures


class ReadOnlyTickTests(unittest.TestCase):
    def setUp(self):
        self.f = controller_fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)

    def forbid_writer_lock(self):
        return patch.object(self.f.reg, 'transaction',
                            side_effect=AssertionError('writer lock taken for a read-only tick'))

    def test_outcome_recovery_reads_without_the_writer_lock(self):
        from workflow.outcome_recovery import tick
        with self.forbid_writer_lock():
            tick(self.f.controller)

    def test_shared_decisions_reads_without_the_writer_lock(self):
        from workflow.shared_decisions import tick
        with self.forbid_writer_lock():
            tick(self.f.controller)

    def test_blocked_followup_reads_without_the_writer_lock(self):
        from workflow.blocked_followup import tick
        config = self.f.controller.config
        config['throughput'] = dict(autofill=dict(enabled=True, planner_lane='consumer'))
        with self.f.reg.transaction() as state:
            state['lanes']['consumer']['state'] = 'running'  # No actionable planner owner.
        with self.forbid_writer_lock():
            tick(self.f.controller)


if __name__ == '__main__':
    unittest.main()
