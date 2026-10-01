"""Lane 11 (#131): the cave checkpoint carries White/Bulbmin at schema 2/3.

Exercises the campaign's own serializer/deserializer (the cave/campaign
supervisor) against the native wire contract in
`native pc_port/pc_p2_species_schema.h`: schema 1 = Blue/Red/Yellow/Purple,
schema 2 adds White, schema 3 adds Bulbmin.
"""
import unittest

from experimental.pikmin2_campaign import (
    SPECIES, SPECIES_SCHEMA, entry_schema, entry_text, initial, transition,
    transfer_schema)

TOKEN = 'a' * 32


def transfer(token, floor, health, squad):
    schema = max([1] + [SPECIES_SCHEMA[s] for s, _ in squad])
    text = f'P2_CAVE_TRANSFER_{schema}\n{token}\n{floor} {health:.9g} {len(squad)}\n'
    return text + ''.join(f'{SPECIES.index(s)} {m}\n' for s, m in squad)


class CaveCheckpointSchemaTests(unittest.TestCase):
    def test_species_table_matches_native(self):
        self.assertEqual(SPECIES_SCHEMA['purple'], 1)
        self.assertEqual(SPECIES_SCHEMA['white'], 2)
        self.assertEqual(SPECIES_SCHEMA['bulbmin'], 3)

    def test_entry_schema_bumps_with_the_squad(self):
        base = [('red', 0), ('purple', 2)]
        self.assertEqual(entry_schema([dict(species=s, maturity=m) for s, m in base]), 1)
        with_white = base + [('white', 1)]
        self.assertEqual(entry_schema([dict(species=s, maturity=m) for s, m in with_white]), 2)
        with_bulbmin = with_white + [('bulbmin', 0)]
        self.assertEqual(entry_schema([dict(species=s, maturity=m) for s, m in with_bulbmin]), 3)

    def test_entry_text_emits_schema_3_for_bulbmin(self):
        state = initial('0' * 64)
        state['squad'] = [dict(species=s, maturity=m) for s, m in
                          [('red', 0), ('white', 2), ('bulbmin', 1)]]
        text = entry_text(state, TOKEN)
        self.assertTrue(text.startswith('P2_CAVE_ENTRY_3\n'))
        self.assertIn('4 2\n', text)   # White = 4
        self.assertIn('5 1\n', text)   # Bulbmin = 5

    def test_transfer_round_trip_preserves_bulbmin(self):
        state = initial('0' * 64)
        state['squad'] = [dict(species=s, maturity=m) for s, m in
                          [('red', 0), ('white', 2), ('bulbmin', 1)]]
        squad = [('red', 0), ('white', 2), ('bulbmin', 1)]
        next_state = transition(state, TOKEN, transfer(TOKEN, 1, 0.625, squad), {}, {})
        self.assertEqual([p['species'] for p in next_state['squad']],
                         ['red', 'white', 'bulbmin'])
        self.assertEqual(next_state['floor'], 2)
        self.assertEqual(next_state['status'], 'active')

    def test_v2_transfer_cannot_carry_bulbmin(self):
        state = initial('0' * 64)
        text = f'P2_CAVE_TRANSFER_2\n{TOKEN}\n1 0.5 1\n5 0\n'
        with self.assertRaisesRegex(ValueError, 'schema too old'):
            transition(state, TOKEN, text, {}, {})

    def test_unknown_transfer_schema_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported cave transfer schema'):
            transfer_schema('P2_CAVE_TRANSFER_4')
        with self.assertRaisesRegex(ValueError, 'Stale or incomplete'):
            transfer_schema('P2_CAVE_ENTRY_1')


if __name__ == '__main__':
    unittest.main()
