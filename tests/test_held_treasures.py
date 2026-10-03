import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from randomizer.held_treasures import prepare, _uid


def text(value):
    data = value.encode('ascii')
    return struct.pack('<I', len(data)) + data


def original(campaign, code=841):
    uid = _uid('tutorial/initgen.txt#17')
    data = b'P2OC1' + text(campaign) + struct.pack('<I', 1)
    data += text('tutorial') + text('initgen.txt') + struct.pack('<I', 17)
    data += struct.pack('<5I9f6I', 33, uid, 0, 1, 0, *([0.] * 9), code, 0, 0, 0, 0, 0)
    data += text('0005') + struct.pack('<4I', 0, 0, 0, 0xffffffff)
    return data + hashlib.sha256(data).digest()


class HeldTreasures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.model = root / 'watch.mod'; self.model.write_bytes(b'synthetic-watch-model')
        self.pod = root / 'pod.mod'; self.pod.write_bytes(b'synthetic-pod-model')
        self.campaign = hashlib.sha256(b'synthetic-campaign').hexdigest()
        self.source = original(self.campaign)
        self.uid = _uid('tutorial/initgen.txt#17')
        self.receiver = _uid('tutorial/defaultgen.txt#0')
        self.onyons = (f'P2_ORIGINAL_ONYON_1 1\n{self.receiver} tutorial/defaultgen.txt#0 '
                       f'{hashlib.sha256(b"synthetic-generator").hexdigest()} '
                       '0002 0001 0 0 -1 4 1 0 0 0 0 0 0 0 0 0\n').encode('ascii')
        self.request = dict(uid=self.uid, source=33, code=841, id='watch')
        entries = dict(watch=dict(kind='otakara', index=73, dictionary=87,
                                 value=110, minimum=30, maximum=40))
        mock = patch('randomizer.held_treasures.verified_entries', return_value=entries)
        mock.start(); self.addCleanup(mock.stop)

    def prepare(self, requests=None, **changes):
        args = dict(original=self.source, onyons=self.onyons, campaign=self.campaign,
                    requests=requests if requests is not None else [self.request],
                    catalog='synthetic-catalog', models={'watch': self.model}, pod=self.pod)
        args.update(changes)
        return prepare(**args)

    def test_preserves_literal_source_and_binds_both_manifests_models_and_receiver(self):
        result = self.prepare()
        self.assertEqual(result['original'], self.source)
        self.assertEqual(result['onyons'], self.onyons)
        header, row = result['descriptor'].decode().splitlines()
        fields = header.split()
        self.assertEqual(fields[3:6], [self.campaign, hashlib.sha256(self.source).hexdigest(),
                                      hashlib.sha256(self.onyons).hexdigest()])
        self.assertEqual(fields[-3:], [str(self.receiver), 'tutorial', '1'])
        self.assertEqual(row.split()[:4], [str(self.uid), '33', '841', 'watch'])
        self.assertEqual(result['source_digest'], hashlib.sha256(result['descriptor']).hexdigest())
        self.assertEqual((result['facts'][0]['value'], result['facts'][0]['minimum'],
                          result['facts'][0]['maximum']), (110, 30, 40))
        self.assertFalse(result['activated'])
        self.assertFalse(result['facts'][0]['physical_delivery_accepted'])

    def test_unmodified_checksum_does_not_allow_wrong_campaign_or_treasure(self):
        for changes in (dict(campaign='a' * 64), dict(original=original(self.campaign, 842)),
                        dict(original=self.source[:-1] + bytes([self.source[-1] ^ 1]))):
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.prepare(**changes)

    def test_literal_identity_and_duplicate_requests_refuse(self):
        for field, value in [('uid', self.uid + 1), ('source', 34), ('code', 842),
                             ('id', 'unknown'), ('source', True)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.prepare([dict(self.request, **{field: value})])
        with self.assertRaises(ValueError): self.prepare([self.request, self.request])

    def test_typed_ship_identity_and_trailing_source_refuse(self):
        for onyons in (self.onyons.replace(b'4 1', b'0 1'),
                       self.onyons.replace(str(self.receiver).encode(), b'123'),
                       self.onyons + b'EXTRA\n'):
            with self.subTest(onyons=onyons), self.assertRaises(ValueError): self.prepare(onyons=onyons)
        payload = self.source[:-32] + b'EXTRA'
        with self.assertRaises(ValueError):
            self.prepare(original=payload + hashlib.sha256(payload).digest())

    def test_missing_model_refuses_without_mutating_source(self):
        self.model.write_bytes(b'')
        with self.assertRaises(ValueError): self.prepare()
        self.assertEqual(self.source, original(self.campaign))


if __name__ == '__main__': unittest.main()
