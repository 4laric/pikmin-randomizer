"""Engine-free edited-log controls; these never certify native gameplay."""
import unittest
import p2_white_campaign_ingestion_assess as witness


def baseline():
    return '\n'.join([
        f'P2_WHITE_ADULT_CHECKPOINT generation=1 sha256={witness.CARD}',
        'P2_WHITE_ADULT_BASELINE predator=0x10 predator_uid=436207616 native_hp=1100.000',
        'P2_WHITE_ADULT_THROW frame=1 victim=0x20 ordinary_flight=1',
        'P2_WHITE_ADULT_CAPTURE frame=2 victim=0x30 predator=0x10',
        'P2_WHITE_POISON_CONSUMED predator=0x10 victim=0x30 damage=750.000',
        'P2_WHITE_ADULT_CASUALTY frame=3 victim=0x30',
        'P2_WHITE_ADULT_CAPTURE frame=4 victim=0x20 predator=0x10',
        'P2_WHITE_POISON_CONSUMED predator=0x10 victim=0x20 damage=750.000',
        'P2_WHITE_ADULT_CASUALTY frame=5 victim=0x20',
        'P2_WHITE_ADULT_PASS consumed=2 field_white=0 stored_white=13 original_red=5 remaining_total=18 native_dead_state=2 source_uid=436207616 actual_ordinary_inputs=1 predator=0x10 native_health=0.000 corpse=0x40',
    ])


class IngestionControls(unittest.TestCase):
    def assess(self, text, **changes):
        card = dict(sha256=witness.CARD, generation=1)
        args = dict(exit_code=0, elapsed=56, timed_out=False,
                    saved_card=card, current_card=dict(card), source_proof=True)
        args.update(changes)
        return witness.assess(text, **args)

    def test_following_and_thrown_victims(self):
        result = self.assess(baseline())
        self.assertEqual((result['actual_throws'], result['natural_following_captures']), (1, 1))

    def test_zero_and_two_throw_models(self):
        text = baseline()
        throw = 'P2_WHITE_ADULT_THROW frame=1 victim=0x20 ordinary_flight=1'
        self.assertEqual(self.assess(text.replace(throw, ''))['actual_throws'], 0)
        self.assertEqual(self.assess(text.replace(throw, throw+'\n'+throw.replace('0x20', '0x30')))['actual_throws'], 2)

    def test_missing_wrong_duplicate_and_out_of_order_events(self):
        text = baseline()
        throw = 'P2_WHITE_ADULT_THROW frame=1 victim=0x20 ordinary_flight=1'
        malformed = [
            text.replace('damage=750.000', 'damage=75.000', 1),
            text.replace('P2_WHITE_POISON_CONSUMED ', 'HIDDEN_POISON ', 1),
            text.replace('P2_WHITE_ADULT_CAPTURE ', 'HIDDEN_CAPTURE ', 1),
            text.replace('P2_WHITE_ADULT_CASUALTY ', 'HIDDEN_LOSS ', 1),
            text.replace(throw, throw+'\n'+throw),
            text.replace(throw, throw.replace('0x20', '0x99')),
            text.replace(throw, '')+'\n'+throw,
            text.replace('victim=0x30', 'victim=0x20'),
            text.replace('P2_WHITE_ADULT_CAPTURE frame=2 victim=0x30 predator=0x10',
                         'P2_WHITE_ADULT_CAPTURE frame=2 victim=0x30 predator=0x99'),
            text.replace('P2_WHITE_POISON_CONSUMED predator=0x10',
                         'P2_WHITE_POISON_CONSUMED predator=0x99', 1),
            text.replace('native_dead_state=2', 'native_dead_state=1'),
            text.replace('remaining_total=18', 'remaining_total=19'),
            text.replace('native_health=0.000', 'native_health=1.000'),
            text.replace('corpse=0x40', 'corpse=(nil)'),
            text.replace('source_uid=436207616', 'source_uid=2'),
        ]
        for case in malformed:
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.assess(case)

    def test_card_exit_and_bounds(self):
        for change in [dict(elapsed=180), dict(elapsed=float('nan')),
                       dict(timed_out=True), dict(exit_code=1),
                       dict(current_card=dict(sha256='0'*64, generation=1))]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.assess(baseline(), **change)


if __name__ == '__main__':
    unittest.main()
