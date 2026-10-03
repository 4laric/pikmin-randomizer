import hashlib
import struct
import contextlib
import io
from unittest.mock import patch
import unittest
from tests import test_white_campaign_bank as white_tests
from randomizer.white_treasure_campaign import append_cargo, bank_files, receiver_row, sidecars
from randomizer.white_campaign import bind_campaign_mode, stage_campaign
from randomizer.purple_campaign import split_records


def goal(uid=178195544, color=1, active=True):
    row = bytearray(108)
    row[:8] = b'    0.0v' if active else b'txen0.0v'
    struct.pack_into('<I', row, 8, uid)
    row[72:80] = b'meti1.0v'
    struct.pack_into('>I', row, 80, 4)
    row[84:88] = b'goal'
    row[88:92] = b'p00\x04'
    struct.pack_into('>I', row, 92, color)
    row[96:104] = b'tnip0.0v'
    return bytes(row)


def framed(rows):
    return b'1.0v' + struct.pack('>4fI', 10, 20, 30, 45, len(rows)) + b''.join(rows)


class WhiteTreasureCampaign(unittest.TestCase):
    source_tree = white_tests.WhiteCampaignBank.source_tree
    # Framed engine-free records test source byte contracts, not model fidelity or gameplay.
    def setUp(self):
        white_tests.WhiteCampaignBank.setUp(self)
        self.treasure = self.root / 'treasure'; self.treasure.mkdir()
        (self.treasure / 'p2-pod.txt').write_bytes(b'P2_POD_1\ndia_a_red 180 15 25\nKochappy 2\n')
        (self.treasure / 'treasure.mod').write_bytes(b'bounded-test-model')
        (self.treasure / 'pod.mod').write_bytes(b'bounded-test-pod')
        self.enabled = dict(self.manifest, p2_white_treasure_campaign=True, profile='foh-day2', starting_color='red')
        self.pellet = bytearray(84); self.pellet[:8] = b'    0.0v'
        struct.pack_into('<I', self.pellet, 8, 321)
        self.pellet[72:80] = b'tlep0.0v'; self.pellet[80:84] = b'50rp'

    def treasure_source(self, root):
        original = self.source_tree(root)
        boss = split_records(original)[0]
        data = framed([goal(), goal(color=0), boss])
        (root / 'dataDir/stages/stage1/default.gen').write_bytes(data)
        (root / 'dataDir/stages/chal0/default.gen').write_bytes(framed([boss, bytes(self.pellet)]))
        return data

    def test_original_receiver_same_uid_other_color_unchanged(self):
        data = framed([goal(), goal(color=0)])
        result, cargo, receiver = append_cargo(data, self.pellet, 1)
        self.assertEqual(result[:20], data[:20])
        self.assertEqual(result[24:len(data)], data[24:])
        self.assertEqual(receiver, 178195544); self.assertEqual(cargo, 0x57545201)
        row = split_records(result)[-1]
        self.assertEqual(struct.unpack_from('>6f', row, 48), (-215, 20, 280, 0, 0, 0))
        self.assertEqual(row[72:], bytes(self.pellet)[72:])

    def test_missing_duplicate_zero_and_dormant_red_receiver_refused(self):
        for rows in ([goal(color=0)], [goal(), goal()], [goal(uid=0)], [goal(active=False)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError): receiver_row(rows)

    def test_broken_receiver_framing_refused(self):
        for start, value in ((80, b'\0\0\0\x05'), (96, b'bad!bad!')):
            row = bytearray(goal()); row[start:start+len(value)] = value
            with self.assertRaises(ValueError): receiver_row([row])

    def test_reserved_identity_bad_stage_and_nonfinite_origin_refuse(self):
        data = framed([goal(), bytes(self.pellet)])
        collision = bytearray(self.pellet); struct.pack_into('<I', collision, 8, 0x57545201)
        with self.assertRaises(ValueError): append_cargo(framed([goal(), collision]), self.pellet, 1)
        for stage in (-1, 5, True):
            with self.assertRaises(ValueError): append_cargo(data, self.pellet, stage)
        data = bytearray(data); struct.pack_into('>f', data, 4, float('nan'))
        with self.assertRaises(ValueError): append_cargo(data, self.pellet, 1)

    def test_exact_descriptor_and_nonempty_models_required(self):
        profile = self.treasure / 'p2-pod.txt'; original = profile.read_bytes()
        for bad in (b'P2_POD_1\ndia_a_red 1 1 1\nKochappy 2\n', b'\xff'):
            profile.write_bytes(bad)
            with self.assertRaises(ValueError): bank_files(self.treasure)
        profile.write_bytes(original); (self.treasure / 'pod.mod').write_bytes(b'')
        with self.assertRaises(ValueError): bank_files(self.treasure)

    def test_bound_config_hashes_exact_original_inputs(self):
        files = bank_files(self.treasure)
        fields = sidecars(files, 1, 12, 13)['p2-white-treasure-campaign.txt'].decode().split()
        self.assertEqual(fields[:4], ['P2_WHITE_TREASURE_CAMPAIGN_1', '1', '12', '13'])
        self.assertEqual(fields[4:], [hashlib.sha256(files[n]).hexdigest() for n in ('p2-pod.txt','treasure.mod','pod.mod')])

    def test_full_overlay_preserves_original_purple_enemy_and_receiver(self):
        assets = self.root / 'retail'; original = self.treasure_source(assets)
        run = self.root / 'run'; run.mkdir(); prior = run / 'assets'; self.treasure_source(prior)
        models = prior / 'dataDir/courses/pikmin2room'; models.mkdir(parents=True)
        for name in ('purple_wait_00.mod', 'enemy.mod'): (models / name).write_bytes(b'prior-' + name.encode())
        (run / 'p2-purple-campaign.txt').write_bytes(b'prior-purple-config')
        receipt = stage_campaign(run, assets, self.bank, self.enabled, self.treasure)
        staged = (run / 'assets/dataDir/stages/stage1/default.gen').read_bytes()
        self.assertEqual(staged[:20], original[:20]); self.assertEqual(staged[24:len(original)], original[24:])
        self.assertEqual(len(split_records(staged)), 7)
        self.assertEqual((assets / 'dataDir/stages/stage1/default.gen').read_bytes(), original)
        for name in ('purple_wait_00.mod', 'enemy.mod'):
            self.assertEqual((run / 'assets/dataDir/courses/pikmin2room' / name).read_bytes(), b'prior-' + name.encode())
        self.assertEqual((run / 'p2-purple-campaign.txt').read_bytes(), b'prior-purple-config')
        self.assertEqual((run / 'assets/dataDir/courses/pikmin2room/treasure.mod').read_bytes(), b'bounded-test-model')
        config = (run / 'p2-white-treasure-campaign.txt').read_text().split()
        self.assertEqual(config[:4], ['P2_WHITE_TREASURE_CAMPAIGN_1','1',str(0x57545201),'178195544'])
        facts = receipt['treasure']; self.assertEqual((facts['value'],facts['minimum'],facts['maximum']), (180,15,25))
        self.assertFalse(facts['physical_delivery_accepted']); self.assertFalse(facts['native_SAVE_resume_accepted'])

    def test_scheduled_cargo_collision_leaves_existing_overlay_unchanged(self):
        assets = self.root / 'retail'; self.treasure_source(assets)
        run = self.root / 'run'; run.mkdir(); prior = run / 'assets'; original = self.treasure_source(prior)
        row = bytearray(self.pellet); struct.pack_into('<I', row, 8, 0x57545201)
        (prior / 'dataDir/stages/stage1/1.gen').write_bytes(framed([row]))
        with self.assertRaises(ValueError): stage_campaign(run, assets, self.bank, self.enabled, self.treasure)
        self.assertEqual((prior / 'dataDir/stages/stage1/default.gen').read_bytes(), original)
        self.assertFalse((run / 'white-base-assets').exists())
        self.assertFalse((run / 'p2-white-treasure-campaign.txt').exists())

    def test_session_treasure_hash_change_or_disabled_reconnect_refuses(self):
        session = self.root / 'session'
        bind_campaign_mode(session, self.enabled, self.bank, self.treasure)
        marker = (session / 'white-campaign.json').read_bytes()
        bind_campaign_mode(session, self.enabled, self.bank, self.treasure)
        self.assertEqual((session / 'white-campaign.json').read_bytes(), marker)
        with self.assertRaises(ValueError): bind_campaign_mode(session, self.manifest, self.bank)
        (self.treasure / 'pod.mod').write_bytes(b'changed')
        with self.assertRaises(ValueError): bind_campaign_mode(session, self.enabled, self.bank, self.treasure)

    def test_mismatch_or_blue_start_refuses_without_session_mutation(self):
        for manifest, bank in ((self.enabled,None), (self.manifest,self.treasure), (dict(self.enabled,starting_color='blue'),self.treasure)):
            with self.assertRaises(ValueError): bind_campaign_mode(self.root / 's', manifest, self.bank, bank)
            self.assertFalse((self.root / 's').exists())

    def test_genuine_bootstrap_has_all_explicit_suffix_flags(self):
        from randomizer.seed import generate
        from randomizer.session import Session
        from randomizer.runner import NativeRun
        manifest = generate('treasure-bank68', p2_enemies=True, p2_purple_campaign=True,
                            p2_white_campaign=True,p2_white_treasure_campaign=True,p2_species=[2])
        session = Session(manifest, self.root / 's'); session.save()
        bind_campaign_mode(session.directory, manifest, self.bank, self.treasure)
        native = NativeRun(session)
        self.assertTrue(native.bootstrap.read_text().endswith('PURPLE 1\nWHITE 1\nWHITE_TREASURE 1\nEND\n'))

    def test_cli_dependency_and_blue_start_refuse(self):
        from randomizer.__main__ import main
        for flags in (['--p2-white-treasure-campaign'], ['--p2-enemies','--p2-purple-campaign','--p2-white-campaign','--p2-white-treasure-campaign','--starting-color','blue']):
            with patch('sys.argv', ['randomizer','generate','--seed','treasure68',*flags]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught: main()
                self.assertEqual(caught.exception.code, 2)
