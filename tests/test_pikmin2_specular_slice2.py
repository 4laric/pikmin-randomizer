import unittest
from pathlib import Path

from experimental.pikmin2_specular_slice2 import evidence, specular_criterion, LIT_CONTROL, VERTEX_COLOR_FLAG

DATA = Path(__file__).with_name('data') / 'frog_specular_render.log'

RENDER = ('FROG_SPECULAR_RENDER viewport_w=1138 viewport_h=711 control=0x93 '
          'specular_dir_calls=2 specular_channel_draws=3 replay_equal=1')


def _log(window='FROG_SPECULAR_WINDOW w=960 h=540 flags=SHOWN centered=1',
         render=RENDER):
    return '\n'.join([
        window,
        'FROG_SPECULAR_READY materials=1 control=0x93',
        'FROG_SPECULAR_SQUAD pikmin=20 navi=1',
        render,
        'PASS FROG_SPECULAR_RENDER',
        '',
    ])


class SpecularCriterionTests(unittest.TestCase):
    def test_audited_lit_controls_carry_specular(self):
        self.assertTrue(specular_criterion(LIT_CONTROL))
        self.assertTrue(specular_criterion(LIT_CONTROL | VERTEX_COLOR_FLAG))

    def test_converter_defaults_do_not_select_specular(self):
        self.assertFalse(specular_criterion(0))
        self.assertFalse(specular_criterion(VERTEX_COLOR_FLAG))

    def test_bad_input_rejected(self):
        for control in (-1, '0x93', None):
            with self.assertRaises(ValueError):
                specular_criterion(control)


class RenderMarkerTests(unittest.TestCase):
    def test_valid_marker(self):
        result = evidence(_log())
        self.assertEqual(result['control'], 0x93)
        self.assertEqual(result['specular_dir_calls'], 2)
        self.assertEqual(result['replay_equal'], 1)

    def test_real_committed_marker_log_parses(self):
        result = evidence(DATA.read_text(encoding='utf-8'))
        self.assertEqual(result['control'], 0x93)

    def test_stripped_render_marker_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(render=''))
        with self.assertRaises(ValueError):
            evidence(_log(window=''))

    def test_missing_real_flag_token_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(window='FROG_SPECULAR_WINDOW w=960 h=540 visible=1 centered=1'))
        with self.assertRaises(ValueError):
            evidence(_log(window='FROG_SPECULAR_WINDOW w=960 h=540 centered=1'))

    def test_ordinary_path_not_reached_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(render=RENDER.replace('specular_dir_calls=2', 'specular_dir_calls=0')))
        with self.assertRaises(ValueError):
            evidence(_log(render=RENDER.replace('specular_channel_draws=3', 'specular_channel_draws=0')))

    def test_literal_without_replay_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log(render=RENDER.replace('replay_equal=1', 'replay_equal=0')))

    def test_stripped_pass_line_flips(self):
        with self.assertRaises(ValueError):
            evidence(_log().replace('PASS FROG_SPECULAR_RENDER', ''))


if __name__ == '__main__':
    unittest.main()
