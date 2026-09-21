import unittest
from unittest.mock import Mock
from workflow.processes import DeadIdentityCache


class DeadIdentityTests(unittest.TestCase):
    def test_conservative_unknown_backoff_expires_and_never_caches_alive(self):
        now=[1]
        inspect=Mock(side_effect=['unknown','alive','dead'])
        probe=DeadIdentityCache(inspect,unknown_seconds=5,clock=lambda:now[0])
        identity=dict(host='host',pid=42,started='100')
        self.assertEqual(probe(identity),'unknown')
        self.assertEqual(probe(identity),'unknown')
        self.assertEqual(inspect.call_count,1)
        now[0]=7
        self.assertEqual(probe(identity),'alive')
        self.assertEqual(probe(identity),'dead')
    def test_dead_identity_cached_but_recycled_pid_is_probed(self):
        inspect = Mock(side_effect=['dead', 'alive'])
        probe = DeadIdentityCache(inspect)
        identity = dict(host='host', pid=42, started='100')
        self.assertEqual(probe(identity), 'dead')
        self.assertEqual(probe(dict(identity)), 'dead')
        self.assertEqual(probe(dict(identity, started='200')), 'alive')
        self.assertEqual(inspect.call_count, 2)

    def test_unknown_and_alive_never_cached(self):
        inspect = Mock(side_effect=['unknown', 'alive', 'dead', 'alive'])
        probe = DeadIdentityCache(inspect)
        identity = dict(host='host', pid=42, started='100')
        self.assertEqual([probe(identity) for _ in range(4)], ['unknown', 'alive', 'dead', 'dead'])
        self.assertEqual(probe(dict(identity, host='other')), 'alive')

    def test_incomplete_identity_never_cached(self):
        inspect = Mock(return_value='dead')
        probe = DeadIdentityCache(inspect)
        probe({'pid': 42})
        probe({'pid': 42})
        self.assertEqual(inspect.call_count, 2)
