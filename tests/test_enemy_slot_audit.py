import struct
import unittest
from scripts.audit_enemy_slots import records, schedules, schedule_for, Reader


def fixture():
    term = b'\xff' * 4
    header = b'1.0v' + struct.pack('>4fi', 0, 0, 0, 0, 1)
    gen = b'    0.0v' + struct.pack('>ii', 0, 5) + bytes(32) + struct.pack('>6f', -1.8, 0, 3.8, -.5, 0, .5)
    obj = b'iket' + (10).to_bytes(4, 'little') + bytes((4, 0, 0)) + b'enon' + struct.pack('>5i5f', 0, 0, 0, 0, 0, 1, 1, 0, 0, 0) + term
    area = b'tnip0.0v' + struct.pack('>3f', 0, 0, 0) + term
    kind = b'eno10.0v' + b'b00\x04' + struct.pack('>i', 5) + term
    return header + gen + obj + area + kind


class EnemySlotAuditTests(unittest.TestCase):
    def test_record_identity_and_native_cache_rounding(self):
        row, = records(fixture(), 1, 'init.gen')
        self.assertEqual(row['id'], '1/init.gen@24')
        self.assertEqual(row['cache_position'], [-1, 0, 3])
        self.assertEqual((row['species'], row['count_min'], row['count_max'], row['respawn_days']), (4, 1, 1, 5))
        self.assertEqual(row['exclusions'], [])

    def test_malformed_records_fail(self):
        data = fixture()
        for bad in (data[:-1], data.replace(b'iket\x0a', b'iket\x09'), data[:24] + b'x' * 8 + data[32:]):
            with self.assertRaises(ValueError): records(bad, 1, 'init.gen')
        with self.assertRaises(ValueError): Reader(b'p00\x04\0').parameters()

    def test_schedule_uses_config_and_excludes_comments(self):
        parsed = schedules('new_map visible { file stages/stage1.ini generator {\n// genfile 1-29.gen 1 29 29\ngenfile odd.gen 4 14 20\n}}')
        self.assertNotIn('1-29.gen', parsed['stage1'])
        schedule = schedule_for('odd.gen', parsed['stage1'])
        self.assertEqual((schedule['first_day'], schedule['last_activation_day'], schedule['expires_after_day']), (5, 15, 21))
        self.assertEqual(schedule_for('1-29.gen', parsed['stage1'])['mode'], 'inactive-file')
        self.assertEqual(schedule_for('28.gen', {})['first_day'], 29)
        self.assertEqual(schedule_for('init.gen', {})['mode'], 'first-visit')
