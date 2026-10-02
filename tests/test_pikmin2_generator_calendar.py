import unittest

from experimental.pikmin2_generator_calendar import (
    advance_loop_flags, course_schedule, expired, load_plan, validate_members)


class GeneratorCalendarTests(unittest.TestCase):
    def setUp(self):
        # Names deliberately do not encode the intervals: declarations govern.
        self.text = ('1 { name tutorial end 2 early.txt 1 4 9 late.txt 5 29 29 '
                     '3 a.txt 30 39 39 b.txt 40 49 49 c.txt 50 59 59 0 7 }')
        self.schedule = course_schedule(self.text, 'tutorial')
        self.members = ['defaultgen.txt', 'plantsgen.txt', 'initgen.txt', 'day/0.txt']
        self.members += [row['member'] for category in ('nonloop', 'loop')
                         for row in self.schedule[category]]

    def plan(self, day, **kwargs):
        return load_plan(self.schedule, self.members, day,
                         course_visited=kwargs.pop('course_visited', True), **kwargs)

    def limited(self, day, **kwargs):
        return [row for row in self.plan(day, **kwargs) if row['index'] is not None]

    def test_original_declaration_order_and_expiry_preserved(self):
        self.assertEqual(self.schedule['nonloop'][0], dict(index=0, member='nonloop/early.txt',
                         minimum_day=1, maximum_day=4, expiry_day=9))
        self.assertEqual([row['index'] for row in self.schedule['loop']], [0, 1, 2])

    def test_first_visit_and_revisit_load_order(self):
        self.assertEqual([row['member'] for row in self.plan(1, course_visited=False)],
                         ['defaultgen.txt', 'plantsgen.txt', 'initgen.txt', 'nonloop/early.txt'])
        self.assertNotIn('initgen.txt', [row['member'] for row in self.plan(1)])

    def test_nonloop_inclusive_boundaries_and_persisted_flags(self):
        for day, names in ((0, []), (1, ['early']), (4, ['early']), (5, ['late']),
                           (29, ['late']), (30, [])):
            with self.subTest(day=day):
                self.assertEqual([row['member'].split('/')[-1][:-4] for row in self.limited(day)
                                  if row['category'] == 'nonloop'], names)
        self.assertEqual(self.limited(4, nonloop_loaded={0}), [])

    def test_loop_windows_repeat_with_adjusted_expiry(self):
        for day, index, expiry in ((29, None, None), (30, 0, 39), (39, 0, 39),
                                   (40, 1, 49), (49, 1, 49), (50, 2, 59), (59, 2, 59),
                                   (60, 0, 69), (90, 0, 99)):
            with self.subTest(day=day):
                rows = [row for row in self.limited(day) if row['category'] == 'loop']
                self.assertEqual([(row['index'], row['expiry_day']) for row in rows],
                                 [] if index is None else [(index, expiry)])

    def test_load_flags_and_boundary_reset_are_explicit(self):
        loaded = {0}
        self.assertEqual(self.limited(31, loop_loaded=loaded), [])
        self.assertEqual(loaded, {0})
        self.assertEqual(advance_loop_flags(loaded, 59), frozenset({0}))
        self.assertEqual(advance_loop_flags(loaded, 60), frozenset())

    def test_daily_file_and_optional_plants(self):
        self.assertEqual(self.plan(30)[-1]['member'], 'day/0.txt')
        members = [name for name in self.members if name != 'plantsgen.txt']
        rows = load_plan(self.schedule, iter(members), 0, course_visited=True)
        self.assertEqual([row['member'] for row in rows], ['defaultgen.txt', 'day/0.txt'])

    def test_missing_declared_source_does_not_create_plan(self):
        for missing in ('defaultgen.txt', 'nonloop/early.txt', 'loop/a.txt'):
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'Missing declared'):
                validate_members(self.schedule, set(self.members)-{missing})

    def test_unknown_duplicate_or_truncated_course_refused(self):
        for text in ('0', self.text+' { name tutorial end 0 0 }',
                     '1 { name tutorial end 1 early.txt 1 }'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                course_schedule(text, 'tutorial')

    def test_unsafe_duplicate_and_invalid_declarations(self):
        for name in ('../escape', 'a/b', 'a\\b', 'C:bad', '..'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                course_schedule(self.text.replace('early.txt', name), 'tutorial')
        for replacement in ('early.txt 5 4 9', 'early.txt -1 4 9', 'early.txt 1 4 -2'):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                course_schedule(self.text.replace('early.txt 1 4 9', replacement), 'tutorial')
        with self.assertRaises(ValueError):
            course_schedule(self.text.replace('late.txt', 'early.txt'), 'tutorial')

    def test_invalid_save_state_refused(self):
        for day in (-1, 1.5, True, 2**31):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.plan(day)
        for flags in ({-1}, {2}, {True}):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                self.plan(1, nonloop_loaded=flags)
        with self.assertRaises(ValueError):
            self.plan(1, course_visited=1)

    def test_expiry_is_strict_and_minus_one_never_expires(self):
        self.assertFalse(expired(-1, 100))
        self.assertFalse(expired(9, 9))
        self.assertTrue(expired(9, 10))


if __name__ == '__main__':
    unittest.main()
