"""Focused contract tests for the PanModoki source-38 transport gate (#220).

Synthetic native logs only: the positive sequence mirrors the real marker
order, and every negative asserts that a partial/injected/duplicate run is
refused rather than silently accepted. No native build or runtime here.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experimental.pikmin2_panmodoki_transport import (
    GENERATOR_SOURCE_38, TransportContractError, parse, validate,
)

G = GENERATOR_SOURCE_38


def positive_lines():
    return [
        'P2_BREADBUG_ACTOR_READY generator=%d native_type=8 xyz=-150,30,1850 behavior=P1_Collec_proxy' % G,
        'P2_BREADBUG_CONTEST_BAIT x=-150.0 y=5.0 z=1910.0',
        'P2_BREADBUG_CONTEST_PHASE phase=natural_tug_setup tick=1',
        'P2_BREADBUG_CONTEST_BEGIN generator=%d identity=onion:p2:38:0 max=2' % G,
        'P2_BREADBUG_CONTEST generator=%d native_power=2 carriers=1' % G,
        'P2_BREADBUG_CONTEST_UPDATE generator=%d carriers=1 outcome=held' % G,
        'P2_BREADBUG_CONTEST_UPDATE generator=%d carriers=2 outcome=stolen' % G,
        'P2_BREADBUG_CONTEST_STOLEN generator=%d carriers=2 released=1' % G,
        'P2_BREADBUG_CONTEST_GRANT generator=%d identity=onion:p2:38:0 granted=1' % G,
        'P2_BREADBUG_CONTEST_PHASE phase=revisit_duplicate tick=420',
        'P2_BREADBUG_CONTEST_UPDATE generator=%d carriers=2 outcome=stolen' % G,
        'P2_BREADBUG_CONTEST_STOLEN generator=%d carriers=2 released=1' % G,
        'P2_BREADBUG_CONTEST_GRANT generator=%d identity=onion:p2:38:0 granted=0 duplicate=1' % G,
        'PASS P2_BREADBUG_CONTEST contest tug stolen_grant owner_died revisit_exactly_once',
    ]


class PanModokiTransportTests(unittest.TestCase):
    def test_positive_sequence_passes(self):
        report = validate(parse('\n'.join(positive_lines())))
        self.assertEqual(report['transport_reward'], 'PASS')
        self.assertEqual(report['identity'], 'onion:p2:38:0')
        self.assertLess(report['natural_carry_line'], report['grant_line'])
        self.assertLess(report['grant_line'], report['duplicate_line'])

    def test_parser_ignores_unrelated_engine_output(self):
        text = '\n'.join(['[PC Port] FPS: 60', 'P2_BREADBUG_CONTEST generator=%d native_power=2 carriers=1' % G])
        events = parse(text)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['kind'], 'carry')
        self.assertEqual(events[0]['carriers'], 1)

    def test_missing_bind_refused(self):
        lines = [l for l in positive_lines() if 'ACTOR_READY' not in l]
        with self.assertRaisesRegex(TransportContractError, 'ACTOR_READY bind'):
            validate(parse('\n'.join(lines)))

    def test_unknown_behavior_refused(self):
        lines = positive_lines()
        lines[0] = lines[0].replace('P1_Collec_proxy', 'impostor')
        with self.assertRaisesRegex(TransportContractError, 'Unexpected source-38 behavior'):
            validate(parse('\n'.join(lines)))

    def test_proxy_only_carry_refused(self):
        lines = [l for l in positive_lines() if 'native_power' not in l]
        lines.insert(4, 'P2_BREADBUG_CONTEST_PROBE generator=%d carriers=2 injected=1' % G)
        with self.assertRaisesRegex(TransportContractError, 'No natural carry latch'):
            validate(parse('\n'.join(lines)))

    def test_injected_receipt_without_steal_refused(self):
        lines = [l for l in positive_lines() if 'STOLEN' not in l and 'outcome=stolen' not in l]
        with self.assertRaisesRegex(TransportContractError, 'No stolen tug'):
            validate(parse('\n'.join(lines)))

    def test_grant_without_preceding_stolen_refused(self):
        lines = positive_lines()
        lines.insert(5, 'P2_BREADBUG_CONTEST_GRANT generator=%d identity=onion:p2:38:0 granted=1' % G)
        with self.assertRaisesRegex(TransportContractError, 'without a preceding STOLEN'):
            validate(parse('\n'.join(lines)))

    def test_wrong_receipt_identity_refused(self):
        lines = [l.replace('onion:p2:38:0', 'onion:p2:40:0') for l in positive_lines()]
        with self.assertRaisesRegex(TransportContractError, 'is not source 38'):
            validate(parse('\n'.join(lines)))

    def test_duplicate_delivery_refused(self):
        lines = positive_lines()
        lines.append('P2_BREADBUG_CONTEST_GRANT generator=%d identity=onion:p2:38:0 granted=1' % G)
        with self.assertRaises(TransportContractError):
            validate(parse('\n'.join(lines)))

    def test_missing_duplicate_negative_refused(self):
        lines = [l for l in positive_lines() if 'duplicate=1' not in l]
        with self.assertRaisesRegex(TransportContractError, 'exactly-once negative'):
            validate(parse('\n'.join(lines)))

    def test_missing_drag_refused(self):
        lines = [l for l in positive_lines() if 'outcome=held' not in l]
        with self.assertRaisesRegex(TransportContractError, 'sustained drag'):
            validate(parse('\n'.join(lines)))

    def test_other_generator_ignored(self):
        text = '\n'.join(positive_lines()) + '\nP2_BREADBUG_CONTEST generator=999999 native_power=9 carriers=9'
        report = validate(parse(text))
        self.assertEqual(report['generator'], G)
        self.assertEqual(report['injected_probes'], 0)


if __name__ == '__main__':
    unittest.main()
