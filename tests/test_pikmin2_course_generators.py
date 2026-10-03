import unittest
from experimental.pikmin2_course_generators import course_generators
from experimental.pikmin2_generator_calendar import course_schedule


def member(count=2, tail=''):
    label = ' '.join(['0'] * 32)
    actors = ['{ {v0.3} 5 3 ' + label + ' 10 20 30 1 2 3 {teki} {0005} '
              '1 0 2 80.15625 2 70 0 841 3 5 1 8 .7 {0000} ' + tail + ' {{_eof}} }'
              for _ in range(count)]
    return ('{v0.1} 1 2 3 45 ' + str(count) + ' ' + ' '.join(actors)).encode('cp932')


class CourseGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.schedule = course_schedule('1 { name tutorial end 1 a.txt 5 29 29 1 b.txt 30 39 39 }', 'tutorial')
        self.raw = {'defaultgen.txt': member(), 'initgen.txt': member(1),
                    'nonloop/a.txt': member(3, '200 30'), 'loop/b.txt': member(4)}

    def load(self, day=5, **kwargs):
        return course_generators(self.schedule, self.raw, day, course_visited=kwargs.pop('course_visited', True), **kwargs)

    def test_complete_records_and_original_semantics(self):
        batches = self.load(course_visited=False)
        self.assertEqual([b['member'] for b in batches], ['defaultgen.txt', 'initgen.txt', 'nonloop/a.txt'])
        self.assertEqual([len(b['records']) for b in batches], [2, 1, 3])
        record = batches[-1]['records'][2]
        self.assertEqual(record['source_key'], 'tutorial/nonloop/a.txt#2')
        self.assertEqual(record['actor']['effective_position'], [11, 22, 33])
        self.assertEqual(record['actor']['respawn_days'], 3)
        self.assertEqual(record['enemy']['count'], 2)
        self.assertEqual(record['enemy']['direction_degrees'], 80.15625)
        self.assertEqual(record['enemy']['generator_tail'], ['200', '30'])
        self.assertEqual(record['enemy']['treasure_code'], 841)

    def test_identities_do_not_change_with_day_or_catalog_order(self):
        before = self.load()[0]['records']
        self.raw = dict(reversed(list(self.raw.items())))
        after = self.load(30)[0]['records']
        self.assertEqual(before, after)
        self.assertEqual(len({r['generator_uid'] for b in self.load(30) for r in b['records']}), 6)

    def test_saved_flags_control_selection_without_mutation(self):
        flags = {0}
        self.assertEqual([b['member'] for b in self.load(nonloop_loaded=flags)], ['defaultgen.txt'])
        self.assertEqual(flags, {0})
        self.assertEqual(self.load(30)[-1]['load']['expiry_day'], 39)
        self.assertEqual([b['member'] for b in self.load(31, loop_loaded={0})], ['defaultgen.txt'])

    def test_raw_bytes_are_authoritative_and_outputs_are_independent(self):
        before = dict(self.raw)
        first = self.load()
        first[0]['records'][0]['enemy']['generator_tail'].append('changed')
        self.assertEqual(self.raw, before)
        self.assertEqual(self.load()[0]['records'][0]['enemy']['generator_tail'], [])
        self.assertEqual(len(first[0]['source_sha256']), 64)

    def test_missing_or_malformed_source_refuses_whole_plan(self):
        del self.raw['loop/b.txt']
        with self.assertRaises(ValueError): self.load()
        self.raw['loop/b.txt'] = member().replace(b'{0005}', b'{0004}')
        with self.assertRaises(ValueError): self.load()

    def test_unsafe_member_is_never_a_source_identity(self):
        for name in ('../outside.txt', '/outside.txt', 'a\\b.txt', 'a//b.txt', 'C:bad.txt'):
            with self.subTest(name=name):
                self.raw[name] = member()
                with self.assertRaises(ValueError): self.load()
                del self.raw[name]


if __name__ == '__main__': unittest.main()
