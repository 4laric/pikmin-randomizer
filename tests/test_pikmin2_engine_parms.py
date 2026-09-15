import struct
import unittest

from experimental.pikmin2_engine_parms import (parse_ai_constants,
                                               parse_anim_mgr,
                                               parse_otakara_config,
                                               parse_parm_text,
                                               parse_teki_tokens,
                                               bmg_find_strings)


def parm_source():
    return (
        '# Creature::Property\n{\n'
        '\t{s000} 4 0.500000 \t# friction(not used)\n'
        '\t{_eof} \n}\n'
        '# EnemyParmsBase\n{\n'
        '\t{fp00} 4 1500.000000 \t# life\n'
        '\t{fp24} 4 10.000000 \t# attack damage\n'
        '\t{ip01} 4 3 \t# flick hit A\n'
        '\t{_eof} \n}\n'
        '# EnemyParmsBase\n{\n'
        '\t{fp01} 4 70.000000 \t# flight height\n'
        '\t{ip02} 4 15 \t# induction limit\n'
        '\t{_eof} \n}\n')


def anim_source():
    return (
        '#\n#\tAnimMgr\n#\n'
        '\t2 \t# number of animations\n'
        '# hit_start.bca\n{\n\tD:\\designer\\hit_start.bca \n\thit_start.bca \n\t10 2\n\t-1 \n}\n'
        '# hit_loop.bca\n{\n\tD:\\designer\\hit_loop.bca \n\thit_loop.bca \n\t0 0 \n\t7 1 \n\t-1 \n}\n')


def config_source():
    return (
        '2\t# size of configs\n'
        '{\n\tname\t\telec\n\tarchive\t\telec.szs\n\tbmd\t\telements_elec.bmd\n'
        '\tradius\t\t35\n\tp_radius\t\t25\n\theight\t\t50\n\tinertiascaling\t\t350\n'
        '\tfriction\t\t0.1\n\tmin\t\t30\n\tmax\t\t40\n\tmoney\t\t1000\n\tunique\t\tyes\n'
        '\tcode\t0\n\tdictionary\t197\n\tend\n}\n'
        '{\n\tname\t\tother\n}\n')


def cave_source():
    return (
        '# TekiInfo\n{\n\t2 \t# num\n\tBigTreasure 10 \t# weight\n\t1 \t# type\n'
        '\tBigTreasure_key 5 \t# weight\n\t1 \t# type\n}\n'
        '# TekiInfo\n{\n\t1 \t# num\n\tChappy 20 \t# weight\n\t0 \t# type\n}\n')


class ParmTextTests(unittest.TestCase):
    def test_sections_and_values(self):
        sections = parse_parm_text(parm_source())
        self.assertEqual([name for name, _ in sections],
                         ['Creature::Property', 'EnemyParmsBase', 'EnemyParmsBase'])
        general = sections[1][1]
        proper = sections[2][1]
        self.assertEqual(general['fp00'], ('1500.000000', 'life'))
        self.assertEqual(general['ip01'], ('3', 'flick hit A'))
        self.assertEqual(proper['fp01'], ('70.000000', 'flight height'))
        self.assertEqual(proper['ip02'], ('15', 'induction limit'))

    def test_malformed_input_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_parm_text(parm_source().replace('\t{fp00}', '\tfp00'))
        with self.assertRaises(ValueError):
            parse_parm_text(parm_source().replace('{fp00} 4', '{fp00} 9'))
        with self.assertRaises(ValueError):
            parse_parm_text(parm_source().replace(
                '\t{fp24} 4 10.000000 \t# attack damage',
                '\t{fp00} 4 99.000000 \t# conflicting duplicate'))
        with self.assertRaises(ValueError):
            parse_parm_text('\t{fp00} 4 1.0 \t# orphan\n')
        with self.assertRaises(ValueError):
            parse_parm_text('# nothing here\n')


class AnimMgrTests(unittest.TestCase):
    def test_clips_and_events(self):
        result = parse_anim_mgr(anim_source())
        self.assertEqual(result['count'], 2)
        start, loop = result['clips']
        self.assertEqual(start['file'], 'hit_start.bca')
        self.assertEqual(start['events'], [(10, 2)])
        self.assertEqual(loop['file'], 'hit_loop.bca')
        self.assertEqual(loop['events'], [(0, 0), (7, 1)])

    def test_malformed_input_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_anim_mgr(anim_source().replace('\t2 \t# number', '\t3 \t# number'))
        with self.assertRaises(ValueError):
            parse_anim_mgr(anim_source().replace('\t-1 \n}\n# hit_loop', '}\n# hit_loop'))
        with self.assertRaises(ValueError):
            parse_anim_mgr(anim_source().replace('\t0 0 \n\t7 1', '\t7 1 \n\t0 0'))
        with self.assertRaises(ValueError):
            parse_anim_mgr(anim_source().replace('\t10 2', '\t10 2\n\t11 two'))


class OtakaraConfigTests(unittest.TestCase):
    def test_wanted_pellets_only(self):
        found = parse_otakara_config(config_source(), ('elec',))
        self.assertEqual(list(found), ['elec'])
        elec = found['elec']
        self.assertEqual((elec['min'], elec['max']), ('30', '40'))
        self.assertEqual(elec['dictionary'], '197')

    def test_malformed_input_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_otakara_config(config_source(), ('elec', 'missing'))
        with self.assertRaises(ValueError):
            parse_otakara_config(config_source().replace('\tend\n', '\n'), ('elec',))
        with self.assertRaises(ValueError):
            parse_otakara_config(config_source().replace('\tmin\t\t30\n', ''), ('elec',))


class AiConstantsTests(unittest.TestCase):
    def test_values(self):
        result = parse_ai_constants('gravity\t\t\t560.0\ndebt\t\t\t10000\nend\n')
        self.assertEqual(result['gravity'], 560.0)
        self.assertEqual(result['debt'], 10000.0)

    def test_malformed_input_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_ai_constants('dopecount\t10\nend\n')
        with self.assertRaises(ValueError):
            parse_ai_constants('gravity\t\tnan\nend\n')


class TekiTokenTests(unittest.TestCase):
    def test_plain_and_cargo_tokens(self):
        tokens = parse_teki_tokens(cave_source(), 'BigTreasure')
        self.assertEqual(len(tokens), 2)
        plain, cargo = tokens
        self.assertIsNone(plain['carried'])
        self.assertEqual((plain['token'], plain['weight'], plain['type']),
                         ('BigTreasure', 10, 1))
        self.assertEqual(cargo['carried'], 'key')

    def test_malformed_input_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_teki_tokens(cave_source().replace('\t2 \t# num', '\t3 \t# num'),
                              'BigTreasure')


def tiny_bmg(strings):
    payload = b'\x00' + b''.join(text.encode('ascii') + b'\x00' for text in strings)
    dat1 = b'DAT1' + struct.pack('>I', 8 + len(payload)) + payload
    return b'MESGbgmg' + b'\x01\x0b' + b'\x00' * 22 + dat1


class BmgTests(unittest.TestCase):
    def test_strings_found_as_whole_records(self):
        data = tiny_bmg(['King of Bugs', 'King', 'Comedy\nBomb'])
        found = bmg_find_strings(data, ['King of Bugs', 'Comedy\nBomb'])
        self.assertEqual(found['King of Bugs'], [1])
        self.assertEqual(len(found['Comedy\nBomb']), 1)
        # 'King' alone is a prefix of a longer record and its own record.
        self.assertEqual(len(bmg_find_strings(data, ['King'])['King']), 1)

    def test_missing_string_fails_closed(self):
        with self.assertRaises(ValueError):
            bmg_find_strings(tiny_bmg(['a']), ['absent'])
        with self.assertRaises(ValueError):
            bmg_find_strings(b'not-a-bmg', ['a'])


if __name__ == '__main__':
    unittest.main()
