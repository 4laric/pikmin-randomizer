import unittest
import re

from experimental.pikmin2_frog_draw_specular import evidence

WINDOW = 'FROG_DRAW_WINDOW w=960 h=540 flags=SHOWN centered=1'
READY = 'FROG_DRAW_READY species=Frog generator=201001 registered=1'
RENDER = ('FROG_DRAW_SPECULAR family_specular_draws=7 total_specular_draws=123 '
          'specular_dir_calls=45 replay_equal=1')


def _log(window=WINDOW, ready=READY, render=RENDER):
    return '\n'.join([window, ready, render, 'PASS FROG_DRAW_SPECULAR', ''])


class FrogDrawSpecularValidatorTests(unittest.TestCase):
    def test_valid_marker(self):
        result = evidence(_log())
        self.assertEqual(result['family_specular_draws'], 7)
        self.assertEqual(result['replay_equal'], 1)
        self.assertEqual(result['reported'], (960, 540))

    def test_family_delta_zero_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(render=RENDER.replace('family_specular_draws=7', 'family_specular_draws=0')))

    def test_non_family_delta_does_not_count(self):
        # Renderer-global specular draws present but no family attribution token:
        # a non-family draw must not satisfy the gate.
        non_family = 'FROG_DRAW_SPECULAR total_specular_draws=123 specular_dir_calls=45 replay_equal=1'
        with self.assertRaises(ValueError):
            evidence(_log(render=non_family))

    def test_scene_without_specular_channel_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(render=RENDER.replace('total_specular_draws=123', 'total_specular_draws=0')))

    def test_no_half_vector_setup_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(render=RENDER.replace('specular_dir_calls=45', 'specular_dir_calls=0')))

    def test_hidden_window_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(window='FROG_DRAW_WINDOW w=960 h=540 flags=HIDDEN centered=1'))

    def test_window_size_within_tolerance_passes(self):
        result = evidence(_log(window='FROG_DRAW_WINDOW w=962 h=544 flags=SHOWN centered=1'))
        self.assertEqual(result['reported'], (962, 544))

    def test_window_size_outside_tolerance_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(window='FROG_DRAW_WINDOW w=1280 h=720 flags=SHOWN centered=1'))

    def test_unregistered_frog_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(ready='FROG_DRAW_READY species=Frog generator=201001 registered=0'))

    def test_bad_replay_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(render=RENDER.replace('replay_equal=1', 'replay_equal=0')))

    def test_stripped_markers_flip(self):
        with self.assertRaises(ValueError):
            evidence(_log(window=''))
        with self.assertRaises(ValueError):
            evidence(_log(render=''))
        with self.assertRaises(ValueError):
            evidence(_log().replace('PASS FROG_DRAW_SPECULAR', ''))


if __name__ == '__main__':
    unittest.main()
