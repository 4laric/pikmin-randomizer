"""Synthetic regional-audit boundary tests; no disc assets or dialogue fixtures."""
import copy
from collections import Counter
import struct
import unittest

from experimental.pikmin2_regional_audit import (
    PELLET_LIST, attach_names, bmg_index, catalog_delta, cave_file_classes,
    campaign_cave_names, digest, kfes_references, message_name, reconcile_entries,
    stage_cave_links, verify_ledger,
)


def bmg(rows, encoding=3):
    data = bytearray(b'\0')
    info = bytearray(struct.pack('>HHHH', len(rows), 8, 0, 0))
    mid = bytearray(struct.pack('>HBBI', len(rows), 0x10, 1, 0))
    for key, value in rows:
        info.extend(struct.pack('>II', len(data), 0))
        data.extend(value + b'\0')
        mid.extend(struct.pack('>I', key))
    blocks = b''.join(tag + struct.pack('>I', 8 + len(body)) + body
                      for tag, body in ((b'INF1', info), (b'DAT1', data), (b'MID1', mid)))
    return b'MESGbmg1' + struct.pack('>II', 32 + len(blocks), 3) + bytes([encoding]) + bytes(15) + blocks


def ledger_fixture():
    config = dict(name='example', dictionary='7', money='40', min='2', max='4',
                  archive='example.szs', bmd='example.bmd', unique='yes')
    entry = dict(treasure_id='example', pellet_kind='otakara', config_index=0,
                 dictionary=7, value=40, weight=2, slots=4, archive='example.szs',
                 model='example.bmd', unique='yes', classification='campaign',
                 campaign_scopes=['campaign_surface'], mode_scopes=[],
                 placements=[dict(treasure_id='example', scope='campaign_surface', engine_loaded=True),
                             dict(treasure_id='example', scope='campaign_surface', engine_loaded=False)])
    return dict(entries=[entry]), dict(otakara={'example': config}, item={})


class MessageTests(unittest.TestCase):
    def test_ids_are_not_entry_positions_and_variants_are_distinct(self):
        messages = bmg_index(bmg([(101 << 8, b'Fixture'), ((101 << 8) | 1, b'Appraisal')]))
        self.assertEqual(message_name(messages, 101)['text'], 'Fixture')
        self.assertEqual(message_name(messages, 101, 1)['text'], 'Appraisal')
        self.assertEqual(message_name(messages, 0)['status'], 'missing')

    def test_empty_control_codes_and_unknown_single_byte_font_are_unresolved(self):
        for value, encoding, status in [(b'', 3, 'empty'), (b'\x1a\x06\0x', 3, 'control_codes_unresolved'),
                                        (b'\xe9', 1, 'font_encoding_unresolved')]:
            with self.subTest(status=status):
                result = message_name(bmg_index(bmg([(101 << 8, value)], encoding)), 101)
                self.assertEqual(result['status'], status)

    def test_shift_jis_is_decoded_strictly(self):
        text = '\u30c6\u30b9\u30c8'
        self.assertEqual(message_name(bmg_index(bmg([(101 << 8, text.encode('shift_jis'))])), 101)['text'], text)

    def test_malformed_tables_fail_closed(self):
        valid = bmg([(101 << 8, b'Fixture')])
        fixtures = [valid[:-1], bmg([(101 << 8, b'A'), (101 << 8, b'B')]), bmg([], 2)]
        bad = bytearray(valid)
        struct.pack_into('>I', bad, 48, 0xFFFFFF)
        fixtures.append(bytes(bad))
        bad = bytearray(valid)
        bad[bad.index(b'MID1') + 11] = 2
        fixtures.append(bytes(bad))
        for data in fixtures:
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                bmg_index(data)

    def test_items_follow_full_treasure_list_not_dictionary_number(self):
        rows = [dict(pellet_kind='otakara', config_index=0, dictionary=99),
                dict(pellet_kind='item', config_index=0, dictionary=1)]
        messages = bmg_index(bmg([(101 << 8, b'Treasure'), (103 << 8, b'Equipment')]))
        attach_names(rows, {'otakara': {'one': {}, 'two': {}}}, {'eng': messages})
        self.assertEqual([r['display_offset'] for r in rows], [0, 2])
        self.assertEqual(rows[1]['onboard_names']['eng']['text'], 'Equipment')


class ContractTests(unittest.TestCase):
    def test_regional_join_preserves_id_when_dictionary_numbers_move(self):
        left = {'a': {'dictionary': '1'}, 'b': {'dictionary': '2'}}
        right = {'b': {'dictionary': '1'}, 'a': {'dictionary': '2'}, 'extra': {}}
        result = catalog_delta(left, right)
        self.assertEqual([r['source_id'] for r in result['changed']], ['a', 'b'])
        self.assertEqual(result['compared_only'], ['extra'])
        self.assertTrue(result['order_changed'])

    def test_unloaded_records_are_separate_and_input_is_unchanged(self):
        ledger, catalogs = ledger_fixture()
        before = copy.deepcopy(ledger)
        row = reconcile_entries(ledger, catalogs)[0]
        self.assertEqual(len(row['active_source_definitions']), 1)
        self.assertEqual(row['unloaded_generator_definitions'][0]['ledger_placement_index'], 1)
        self.assertEqual(ledger, before)

    def test_catalog_drift_duplicates_and_missing_entries_are_rejected(self):
        for mutation in ('dictionary', 'index', 'duplicate', 'missing', 'loaded_flag'):
            ledger, catalogs = ledger_fixture()
            if mutation == 'dictionary': ledger['entries'][0]['dictionary'] = 1
            if mutation == 'index': ledger['entries'][0]['config_index'] = 1
            if mutation == 'duplicate': ledger['entries'] *= 2
            if mutation == 'missing': ledger['entries'] = []
            if mutation == 'loaded_flag': ledger['entries'][0]['placements'][0]['engine_loaded'] = 'false'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                reconcile_entries(ledger, catalogs)

    def test_provenance_rejects_stale_disc_inventory_and_unreconciled_ledger(self):
        sources = {PELLET_LIST: b'catalog fixture', 'user/Abe/stages.txt': b'stage fixture'}
        ledger = dict(schema=1, disc='GPVE01 revision 0', inventory_sha256=digest(b'inventory'),
                      source_sha256={p: digest(v) for p, v in sources.items()}, reconciliation={'reconciled': True})
        verify_ledger(ledger, b'inventory', sources.__getitem__)
        with self.assertRaises(ValueError): verify_ledger(ledger, b'changed', sources.__getitem__)
        sources[PELLET_LIST] = b'changed'
        with self.assertRaises(ValueError): verify_ledger(ledger, b'inventory', sources.__getitem__)
        ledger['source_sha256'][PELLET_LIST] = digest(b'changed')
        ledger['reconciliation']['reconciled'] = False
        with self.assertRaises(ValueError): verify_ledger(ledger, b'inventory', sources.__getitem__)

    def test_unreferenced_is_not_automatically_unused_or_demo(self):
        prefix = 'user/Mukki/mapunits/caveinfo/'
        paths = {prefix + name + '.txt': (0, 0) for name in ('retail', 'test', 'kfes_example')}
        inventory = dict(story_caves=[{'source': prefix + 'retail.txt'}],
                         challenge={'stages': []}, battle={'stages': []})
        rows = cave_file_classes(paths, inventory)
        self.assertEqual(dict(Counter(r['classification'] for r in rows)),
                         {'unreferenced_status_unresolved': 2, 'retail_referenced': 1})
        self.assertEqual(rows[0]['filename_hint'], 'kfes')
        del paths[prefix + 'retail.txt']
        with self.assertRaises(ValueError): cave_file_classes(paths, inventory)

    def test_kfes_classification_requires_table_reference_not_filename(self):
        row = ['4', 'alternate.txt'] + ['0'] * 24 + ['1', '0', '0', '20.0']
        references = kfes_references('1 { ' + ' '.join(row) + ' }')
        prefix = 'user/Mukki/mapunits/caveinfo/'
        files = {prefix + 'alternate.txt': (0, 0), prefix + 'kfes_unproven.txt': (0, 0)}
        inventory = dict(story_caves=[], challenge={'stages': []}, battle={'stages': []})
        rows = cave_file_classes(files, inventory, references)
        self.assertEqual(rows[0]['classification'], 'kfes_only_reference')
        self.assertEqual(rows[1]['classification'], 'unreferenced_status_unresolved')
        with self.assertRaises(ValueError): kfes_references('2 { ' + ' '.join(row) + ' }')


class CaveNameTests(unittest.TestCase):
    STAGES = ('1 { name tutorial start 0 0 0 end '
              '1 window.txt 0 9 1 0 '
              '2 {t_01} 3 tutorial_1.txt {test} 0 caveinfo.txt 7 }')

    def inventory(self):
        return dict(surfaces=[{'id': 'tutorial'}],
                    story_caves=[{'id': 'tutorial_1', 'source': 'user/Mukki/mapunits/caveinfo/tutorial_1.txt'}],
                    challenge={'stages': []}, battle={'stages': []})

    def test_join_uses_stage_tag_not_inventory_order_or_filename_guess(self):
        messages = {'eng': bmg_index(bmg([(8395 << 8, b'Cave fixture')]))}
        links = stage_cave_links(self.STAGES)
        rows = campaign_cave_names(list(reversed(links)), self.inventory(), messages)
        self.assertEqual(rows[0]['source_id'], 'tutorial_1')
        self.assertEqual(rows[0]['cave_tag'], 't_01')
        self.assertEqual(rows[0]['message_number'], 8395)
        self.assertEqual(rows[0]['onboard_names']['eng']['text'], 'Cave fixture')
        self.assertEqual(rows[0]['cave_table_index'], 0)

    def test_malformed_stage_framing_rejected(self):
        bad = [self.STAGES.replace('1 {', '2 {', 1), self.STAGES.replace('2 {t_01}', '3 {t_01}'),
               self.STAGES.replace('{test}', '{t_01}'), self.STAGES.replace('end', 'missing'),
               self.STAGES.replace('tutorial_1.txt', '../tutorial_1.txt'), self.STAGES.replace('7 }', '7 extra }')]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                stage_cave_links(text)

    def test_missing_ambiguous_and_unmapped_campaign_links_fail(self):
        links = stage_cave_links(self.STAGES)
        cases = [[], links + [links[0]], [dict(links[0], cave_tag='c_00')]]
        for candidate in cases:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                campaign_cave_names(candidate, self.inventory(), {})

    def test_missing_localized_message_is_not_replaced_with_english(self):
        rows = campaign_cave_names(stage_cave_links(self.STAGES), self.inventory(), {'jpn': {}})
        self.assertEqual(rows[0]['onboard_names']['jpn']['status'], 'missing')
        self.assertIsNone(rows[0]['onboard_names']['jpn']['text'])

    def test_registration_outside_retail_does_not_become_campaign(self):
        links = stage_cave_links(self.STAGES)
        files = {r['source_path']: (0, 0) for r in links}
        rows = cave_file_classes(files, self.inventory(), stage_links=links)
        registered = next(r for r in rows if r['source_path'].endswith('/caveinfo.txt'))
        self.assertEqual(registered['classification'], 'stage_registered_outside_retail_inventory')
        self.assertEqual(registered['retail_scopes'], [])
        self.assertEqual(registered['stage_table_references'][0]['cave_tag'], 'test')

    def test_nonretail_extensionless_references_stay_literal(self):
        links = stage_cave_links('1 {name test_map end 0 0 2 {info} 0 haru {king} 0 haru 0}')
        self.assertEqual([r['filename'] for r in links], ['haru', 'haru'])
        self.assertEqual([r['cave_tag'] for r in links], ['info', 'king'])
        self.assertEqual(links[0]['source_path'], 'user/Mukki/mapunits/caveinfo/haru')

    def test_cave_presentation_payload_nul_is_not_string_terminator(self):
        raw = b'\x1a\x07\xff\x00\x01\x00\x73\x1a\x05\x03\x00\x04\x1a\x07\x03\x00\x05\x00\x69Cave fixture'
        table = bmg_index(bmg([(8395 << 8, raw)]))
        result = message_name(table, 8395, cave_presentation=True)
        self.assertEqual(result['text'], 'Cave fixture')
        self.assertEqual(result['status'], 'resolved_with_presentation_controls')
        self.assertEqual(result['presentation_controls'],
                         [{'tag': 0xFF0001, 'payload_hex': '0073'}, {'tag': 0x030004, 'payload_hex': ''},
                          {'tag': 0x030005, 'payload_hex': '0069'}])
        self.assertEqual(message_name(table, 8395)['status'], 'control_codes_unresolved')

    def test_unknown_cave_control_remains_unresolved_and_bad_length_fails(self):
        table = bmg_index(bmg([(8395 << 8, b'\x1a\x05\xfe\x00\x01Cave fixture')]))
        self.assertEqual(message_name(table, 8395, cave_presentation=True)['status'], 'control_codes_unresolved')
        for raw in (b'\x1a\x04\xff\x00\x01', b'\x1a\xff\xff\x00\x01'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                message_name(bmg_index(bmg([(8395 << 8, raw)])), 8395, cave_presentation=True)


if __name__ == '__main__':
    unittest.main()
