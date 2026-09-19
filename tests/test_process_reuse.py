import socket
import subprocess
import unittest
from unittest.mock import patch

from workflow import processes


class ProtectedPidReuseTests(unittest.TestCase):
    identity = dict(host=socket.gethostname(), pid=123, started='134341570682844101')

    def check(self, stdout, expected, returncode=0):
        result = subprocess.CompletedProcess([], returncode, stdout, '')
        with patch.object(processes, 'identify', side_effect=PermissionError), \
             patch.object(processes.os, 'name', 'nt'), \
             patch.object(processes.subprocess, 'run', return_value=result):
            self.assertEqual(processes.probe(self.identity), expected)

    def test_replacement_creation_time_proves_old_owner_dead(self):
        self.check('134341581227183800\n', 'dead')

    def test_same_time_remains_unknown_including_precision_loss(self):
        self.check('134341570682844100\n', 'unknown')

    def test_failed_or_missing_observation_remains_unknown(self):
        for value in ('', 'garbage', '0', '-1'):
            self.check(value, 'unknown')
        self.check('134341581227183800', 'unknown', 1)

    def test_timeout_remains_unknown(self):
        with patch.object(processes, 'identify', side_effect=PermissionError), \
             patch.object(processes.os, 'name', 'nt'), \
             patch.object(processes.subprocess, 'run', side_effect=subprocess.TimeoutExpired('powershell', 5)):
            self.assertEqual(processes.probe(self.identity), 'unknown')

    def test_other_host_is_not_inspected(self):
        with patch.object(processes.subprocess, 'run') as run:
            self.assertEqual(processes.probe(dict(self.identity, host='another-host')), 'unknown')
            run.assert_not_called()
