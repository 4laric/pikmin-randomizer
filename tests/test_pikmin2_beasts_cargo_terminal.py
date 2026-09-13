import json
from pathlib import Path
import tempfile
import unittest
from experimental.pikmin2_beasts_cargo_terminal import enable,validate,POLICY,EMPTY
from experimental.pikmin2_beasts_floor3_failure_runtime import validate as legacy_validate

TOKEN='e'*64
PARTY=dict(health=1.,squad=[dict(species='red',maturity=0) for _ in range(20)])


def evidence(reason):
    lines=[f'P2_BEASTS_CARGO_TERMINAL_READY floor=3 token={TOKEN} cargo=1 pokos=0 diagnostic=1',
        'P2_CAVE_READY floor=3 survivors=20 health=1',f'P2_BEASTS_ENTRY_READY floor=3 token={TOKEN} descent=disabled',
        'P2_CARGO_FAILURE_OBSERVED generator=63000 value=150 weight=12 slots=20 pre_receipt=1',
        f'P2_FLOOR3_FAILURE_ARMED token={TOKEN} reason={reason} active_descent_rejected=1','P2_BEASTS_PARTY health=1 count=20']
    lines += [f'P2_BEASTS_SURVIVOR index={i} species=red maturity=0' for i in range(20)]
    lines += ['P2_BEASTS_PARTY_END',f'P2_FLOOR3_FAILURE_INJECTED reason={reason} repairs_unchanged=1 pokos=0',
        f'P2_BEASTS_FAILURE floor=3 destination=0 reason={reason} survivors=0 health=0']
    return '\n'.join(lines)+'\n',f'P2_BEASTS_FAILURE_1\n{TOKEN}\n3 0 0 0\n{reason}\n'.encode()


class CargoTerminalTests(unittest.TestCase):
    def test_reasons_and_legacy_rejection(self):
        for reason in ('extinction','knockout'):
            log,transfer=evidence(reason)
            self.assertTrue(validate(log,transfer,TOKEN,reason,PARTY)['diagnostic_only'])
            with self.assertRaises(ValueError):legacy_validate(log,transfer,TOKEN,reason,PARTY)

    def test_changed_identity_receipt_and_party_rejected(self):
        log,transfer=evidence('extinction')
        for old,new in [('floor=3','floor=4'),('generator=63000','generator=63001'),('cargo=1','cargo=2'),
            ('health=1 count=20','health=0.5 count=20'),('species=red','species=purple'),('pokos=0','pokos=150'),
            ('active_descent_rejected=1','active_descent_rejected=0')]:
            with self.subTest(old=old),self.assertRaises(ValueError):validate(log.replace(old,new),transfer,TOKEN,'extinction',PARTY)
        for suffix in ('P2_POD_RECEIPT id=x\n','P2_ROOM_CARGO_FREE_READY cargo=0\n','P2_CAVE_TRANSFER\n'):
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):validate(log+suffix,transfer,TOKEN,'extinction',PARTY)
        with self.assertRaises(ValueError):validate(log,transfer.replace(b'3 0 0 0',b'3 4 0 0'),TOKEN,'extinction',PARTY)

    def test_opt_in_only_fresh_pre_receipt_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);report=dict(policy='P2_BEASTS_FLOOR3_HAUL_SURVEY_1',floor=3,replay=False,boundary_token=TOKEN,input_sha256={},limitations=[])
            (p/'survey.json').write_text(json.dumps(report));enable(p,'knockout',empty_ledger=True)
            self.assertEqual((p/'p2-economy.txt').read_bytes(),EMPTY)
            self.assertEqual((p/'p2-beasts-cargo-terminal.txt').read_text(),f'P2_BEASTS_CARGO_TERMINAL_1\n{TOKEN}\n')
            actual=json.loads((p/'survey.json').read_bytes());self.assertEqual(actual['policy'],POLICY)
            self.assertIn('p2-economy.txt',actual['input_sha256'])
            with self.assertRaises(ValueError):enable(p,'extinction')
        for field,value in [('replay',True),('floor',4),('policy','P2_BEASTS_FLOOR3_ENTRY_SURVEY_1')]:
            with tempfile.TemporaryDirectory() as temp:
                p=Path(temp);bad=dict(report);bad[field]=value;(p/'survey.json').write_text(json.dumps(bad))
                with self.subTest(field=field),self.assertRaises(ValueError):enable(p,'extinction')
