import unittest

from experimental.pikmin2_specular_slice2 import evidence, specular_criterion, LIT_CONTROL, VERTEX_COLOR_FLAG


def _render(**overrides):
    values = dict(visible_channels=695092, specular_channels=260635, replay_equal=1)
    values.update(overrides)
    body = ' '.join('{}={}'.format(k, v) for k, v in sorted(values.items()))
    return '\n'.join([
        'P2_QUEEN_SPECULAR_READY diffuse=UV1 specular=normal_btk source_lighting=host third_stage=omitted',
        'FROG_SPECULAR_READY materials=1 source_control=0x93',
        'FROG_SPECULAR_RENDER ' + body,
        'PASS FROG_SPECULAR_RENDER',
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
    def test_valid_marker_passes(self):
        result = evidence(_render())
        self.assertEqual(result['specular_channels'], 260635)
        self.assertEqual(result['replay_equal'], 1)

    def test_stripped_render_marker_flips(self):
        with self.assertRaises(ValueError):
            evidence('')
        with self.assertRaises(ValueError):
            evidence('P2_FROG_READY species=Frog generator=1 health=100\n')

    def test_stripped_pass_line_flips(self):
        no_pass = _render().replace('PASS FROG_SPECULAR_RENDER', '')
        with self.assertRaises(ValueError):
            evidence(no_pass)

    def test_zero_specular_contribution_flips(self):
        with self.assertRaises(ValueError):
            evidence(_render(specular_channels=0))

    def test_literal_replay_or_no_visible_pixels_flip(self):
        with self.assertRaises(ValueError):
            evidence(_render(visible_channels=0))
        with self.assertRaises(ValueError):
            evidence(_render(replay_equal=0))

    def test_missing_fields_flip(self):
        log = ('FROG_SPECULAR_RENDER specular_channels=5\n'
               'PASS FROG_SPECULAR_RENDER\n')
        with self.assertRaises(ValueError):
            evidence(log)


if __name__ == '__main__':
    unittest.main()
